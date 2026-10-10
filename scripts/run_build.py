#!/usr/bin/env python3
"""Run bridge-owned build commands without shell interpolation."""
import argparse
import subprocess
from validate import validate

parser = argparse.ArgumentParser()
parser.add_argument("project")
parser.add_argument("sha")
parser.add_argument("platform", choices=["linux", "windows"])
args = parser.parse_args()
config = validate(args.project, args.sha)
for phase, cmd in config[args.platform].items():
    print(f"Starting {phase}", flush=True)
    subprocess.run(cmd, check=True)
