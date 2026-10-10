#!/usr/bin/env python3
"""Validate a dispatch request against bridge-owned project configuration."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
ALLOWED = {"source_repo", "checkout_path", "linux", "windows"}

def validate(project, sha):
    if not ID.fullmatch(project):
        raise ValueError("Invalid project identifier")
    if not SHA.fullmatch(sha):
        raise ValueError("Expected full 40-character commit SHA")
    path = ROOT / "projects" / (project + ".json")
    config = json.loads(path.read_text(encoding="utf-8"))
    if set(config) - ALLOWED:
        raise ValueError("Unknown config keys")
    if not REPO.fullmatch(config["source_repo"]):
        raise ValueError("Invalid source repository")
    if config.get("checkout_path") != "source":
        raise ValueError("checkout_path must be source")
    for platform in ("linux", "windows"):
        tasks = config[platform]
        if set(tasks) != {"configure", "build", "test"}:
            raise ValueError("Invalid task keys")
        for task in tasks.values():
            if not isinstance(task, list) or not task or any(not isinstance(arg, str) or not arg or "\x00" in arg or "\n" in arg for arg in task):
                raise ValueError("Commands must be nonempty argv arrays")
    return config

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("sha")
    args = parser.parse_args()
    print(json.dumps(validate(args.project, args.sha)))
