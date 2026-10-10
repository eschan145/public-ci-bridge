#!/usr/bin/env python3
"""Pi controller for trusted private repositories using encrypted public CI bundles.

Runs from systemd. Never sends source or credential in dispatch payload. A public
release contains only ciphertext. A dedicated repository Actions secret holds
the archive key. Do not run arbitrary, untrusted private-repo code on this system.
"""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
from secure_bundle import encrypt
from validate import validate

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = os.environ.get('CI_PUBLIC_REPO', 'eschan145/public-ci-bridge')
STATE = Path.home() / '.local/state/public-ci-bridge/secure.json'
KEYFILE = Path.home() / '.config/public-ci-bridge/archive.key'
CONTEXT = 'public-ci-bridge/windows-linux'

def gh(*args, data=None):
    return subprocess.check_output(['gh', *args], input=data, text=True).strip()

def api(path):
    return json.loads(gh('api', path))

def post(path, document):
    gh('api', path, '--method', 'POST', '--input', '-', data=json.dumps(document))

def status(repo, sha, result, description, url=''):
    post(f'repos/{repo}/statuses/{sha}', {
        'state': result, 'context': CONTEXT,
        'description': description[:140], 'target_url': url,
    })

def update(state):
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2) + '\n')
    tmp.replace(STATE)

def discover_run(tag):
    runs = api(f'repos/{PUBLIC}/actions/workflows/secure-build.yml/runs?event=repository_dispatch&per_page=50')['workflow_runs']
    for run in runs:
        if run['display_title'] == tag:
            return run
    return None

def collect(project, state):
    item = state[project]
    if item['phase'] == 'complete':
        return
    run = discover_run(item['tag'])
    if not run:
        print(f'{project}: awaiting run discovery')
        return
    item['run_id'] = run['id']
    if run['status'] != 'completed':
        print(f'{project}: {run["status"]}')
        return
    success = run['conclusion'] == 'success'
    status(item['repo'], item['sha'],
           'success' if success else 'failure',
           f'Public Windows/Linux CI: {run["conclusion"]}', run['html_url'])
    item['phase'] = 'complete'
    item['conclusion'] = run['conclusion']
    update(state)
    # The encrypted asset should not be retained after reconciliation.
    try:
        gh('release', 'delete', item['tag'], '--repo', PUBLIC, '--yes', '--cleanup-tag')
    except subprocess.CalledProcessError as e:
        print(f'{project}: release cleanup failed: {e}', file=sys.stderr)
    print(f'{project}: {run["conclusion"]}')

def dispatch(project, sha, repo):
    key = KEYFILE.read_bytes().strip()
    tag = f'ci-{project}-{sha}-{secrets.token_hex(4)}'
    with tempfile.TemporaryDirectory(prefix='ci-bridge-') as tmp:
        root = Path(tmp)
        gh('repo', 'clone', repo, str(root / 'source'), '--', '--quiet')
        subprocess.run(['git', '-C', str(root / 'source'), 'fetch', '--no-tags', 'origin', sha], check=True)
        encrypt(str(root / 'source'), sha, root / 'source.bin', key)
        gh('release', 'create', tag, str(root / 'source.bin'), '--repo', PUBLIC,
           '--title', tag, '--notes', 'Temporary encrypted CI input; no plaintext source.',
           '--prerelease', '--latest=false')
    return tag

def main():
    if not KEYFILE.is_file():
        raise RuntimeError('Archive encryption key not configured')
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for path in sorted((ROOT / 'projects').glob('*.json')):
        project = path.stem
        if project == 'example':
            continue
        config = json.loads(path.read_text())
        repo = config['source_repo']
        sha = api(f'repos/{repo}/commits/main')['sha']
        validate(project, sha)
        current = state.get(project)
        if current and current['phase'] != 'complete':
            collect(project, state)
            current = state.get(project)
        if current and current['sha'] == sha:
            continue
        if current and current['phase'] != 'complete':
            status(repo, current['sha'], 'error', 'Superseded by newer commit')
        status(repo, sha, 'pending', 'Encrypted source CI queued')
        tag = dispatch(project, sha, repo)
        state[project] = {'sha': sha, 'repo': repo, 'tag': tag, 'phase': 'dispatched'}
        update(state)
        post(f'repos/{PUBLIC}/dispatches', {
            'event_type': 'secure-build-v1',
            'client_payload': {'project': project, 'sha': sha, 'tag': tag},
        })
        print(f'{project}: dispatched {tag}')

if __name__ == '__main__':
    main()
