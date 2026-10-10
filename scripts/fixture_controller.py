#!/usr/bin/env python3
"""Pi-hosted CI fixture controller. Only sends explicitly public-safe sample code."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

OWNER = "eschan145"
PRIVATE = f"{OWNER}/ci-bridge-fixture"
PUBLIC = f"{OWNER}/public-ci-bridge"
STATE = Path.home() / ".local/state/public-ci-bridge/fixture.json"
FILES = ["calculator.py", "tests/__init__.py", "tests/test_calculator.py"]
CONTEXT = "public-ci-bridge/fixture-matrix"

def gh(*args, data=None):
    call = ["gh", "api", *args]
    return subprocess.check_output(call, text=True, input=data)

def status(sha, state, description, url=""):
    payload = json.dumps({"state": state, "description": description[:140], "context": CONTEXT, "target_url": url})
    gh(f"repos/{PRIVATE}/statuses/{sha}", "--method", "POST", "--input", "-", data=payload)

def main():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    saved = json.loads(STATE.read_text()) if STATE.exists() else {}
    # Results are linked to the originating private commit, not the worker's own SHA.
    if saved.get("run"):
        runs = json.loads(gh(f"repos/{PUBLIC}/actions/runs/{saved['run']}"))
        if runs["status"] == "completed":
            conclusion = runs.get("conclusion")
            status(saved["sha"], "success" if conclusion == "success" else "failure",
                   f"Public Windows/Linux CI: {conclusion}", runs["html_url"])
            print(f"Completed: {saved['sha'][:8]} -> {conclusion}")
            saved = {}
        else:
            print(f"Still running {saved['run']}: {runs['status']}")
    sha = json.loads(gh(f"repos/{PRIVATE}/commits/main"))["sha"]
    if saved and saved.get("sha") == sha:
        STATE.write_text(json.dumps(saved))
        return
    if saved:
        status(saved["sha"], "error", "Superseded by newer commit")
    if not saved and STATE.exists():
        completed = json.loads(STATE.read_text()).get("completed")
        if completed == sha:
            return
    # Download explicitly allowlisted fixture files only, never arbitrary private source.
    payload_buffer = io.BytesIO()
    with zipfile.ZipFile(payload_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            raw = subprocess.check_output(["gh", "api", "-H", "Accept: application/vnd.github.raw",
                                           f"repos/{PRIVATE}/contents/{name}?ref={sha}"])
            z.writestr(name, raw)
    archive = payload_buffer.getvalue()
    assert len(archive) < 20000, "Fixture too large"
    encoded = base64.b64encode(archive).decode("ascii")
    body = {"event_type": "fixture-smoke-v1",
            "client_payload": {"fixture_zip_b64": encoded,
                               "fixture_zip_sha256": hashlib.sha256(archive).hexdigest(),
                               "private_sha": sha}}
    status(sha, "pending", "Public Windows/Linux CI dispatched")
    before = time.time()
    gh(f"repos/{PUBLIC}/dispatches", "--method", "POST", "--input", "-", data=json.dumps(body))
    # Wait briefly until the created run is listed, or retry discovery at next invocation.
    run_id = None
    for attempt in range(12):
        runs = json.loads(gh(f"repos/{PUBLIC}/actions/workflows/fixture-smoke.yml/runs?event=repository_dispatch&per_page=10"))["workflow_runs"]
        candidates = [r for r in runs if r["created_at"] >= time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(before - 5))]
        if candidates:
            run_id = max(candidates, key=lambda r: r["id"])["id"]
            break
        time.sleep(2)
    if not run_id:
        raise RuntimeError("Dispatch accepted but run not discoverable; retry reconciliation needed")
    STATE.write_text(json.dumps({"sha": sha, "run": run_id}))
    print(f"Dispatched {sha[:8]} -> {run_id}")

if __name__ == "__main__":
    main()
