#!/usr/bin/env python3
"""Encrypt and safely extract complete Git trees for public CI transfer."""
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from cryptography.fernet import Fernet

def encrypt(repository, sha, destination, key):
    if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha.lower()):
        raise ValueError('Expected full SHA')
    raw = subprocess.check_output(['git', '-C', repository, 'archive', '--format=tar.gz', sha])
    Path(destination).write_bytes(Fernet(key).encrypt(raw))

def decrypt(source, destination, key):
    raw = Fernet(key).decrypt(Path(source).read_bytes())
    base = Path(destination).resolve()
    base.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers()
        for member in members:
            path = Path(member.name)
            if (path.is_absolute() or '..' in path.parts or member.issym()
                or member.islnk() or member.isdev() or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe archive member: ' + member.name)
            target = (base / path).resolve()
            if not target.is_relative_to(base):
                raise ValueError('Archive escapes extraction directory')
        for member in members:
            dest = base / member.name
            if member.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as stream, dest.open('wb') as output:
                    import shutil
                    shutil.copyfileobj(stream, output)

if __name__ == '__main__':
    mode, input_path, output_path = sys.argv[1:4]
    key = os.environ['SOURCE_ARCHIVE_KEY'].encode()
    if mode == 'pack':
        encrypt(input_path, sys.argv[4], output_path, key)
    elif mode == 'unpack':
        decrypt(input_path, output_path, key)
    else:
        raise ValueError('Unknown mode')
