"""Harmless-fixture-only smoke test. Public payload: NEVER use for secret source."""
import base64
import hashlib
import io
import os
from pathlib import Path
import subprocess
import zipfile

raw = base64.b64decode(os.environ["SOURCE_DATA"], validate=True)
assert len(raw) <= 20000, "Fixture exceeds safe smoke-test size"
assert hashlib.sha256(raw).hexdigest() == os.environ["SOURCE_SHA256"]
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    names = z.namelist()
    assert sorted(names) == ["calculator.py", "tests/__init__.py", "tests/test_calculator.py"]
    for name in names:
        destination = Path("smoke-source") / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(z.read(name))
subprocess.run(
    [os.environ["PYTHON_CMD"], "-m", "unittest", "discover", "-s", "tests", "-v"],
    cwd="smoke-source",
    check=True,
)
print("Fixture snapshot SHA256 verified and tests passed.")
