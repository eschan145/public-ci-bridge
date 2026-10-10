#!/usr/bin/env python3
"""Fetch commit from a registered repository using gh authentication."""
import os
import subprocess
import sys
from validate import validate

project, sha = sys.argv[1:]
config = validate(project, sha)
repo = config["source_repo"]
owner, name = repo.split("/")
if owner != os.environ.get("SOURCE_OWNER"):
    raise SystemExit("Configured owner mismatch")
# gh supplies an ephemeral credential to git via gh auth git-credential.
# No token is embedded in URLs, command arguments, or persistent git configuration.
subprocess.run(["gh", "auth", "setup-git"], check=True)
subprocess.run(["git", "init", "source"], check=True)
subprocess.run(["git", "-C", "source", "remote", "add", "origin", f"https://github.com/{repo}.git"], check=True)
subprocess.run(["git", "-C", "source", "-c", "protocol.version=2", "fetch", "--no-tags", "--depth=1", "origin", sha], check=True)
subprocess.run(["git", "-C", "source", "checkout", "--detach", "FETCH_HEAD"], check=True)
actual = subprocess.check_output(["git", "-C", "source", "rev-parse", "HEAD"], text=True).strip()
if actual.lower() != sha.lower():
    raise SystemExit("Fetched unexpected commit")
