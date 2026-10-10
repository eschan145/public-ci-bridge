"""Send harmless fixture to a public smoke runner (NOT for private source)."""
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

source = Path("/home/pi/ci-bridge-fixture")
out = io.BytesIO()
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in ["calculator.py", "tests/__init__.py", "tests/test_calculator.py"]:
        z.write(source / name, name)
raw = out.getvalue()
assert len(raw) < 20000
payload = {
    "event_type": "fixture-smoke-v1",
    "client_payload": {
        "fixture_zip_b64": base64.b64encode(raw).decode("ascii"),
        "fixture_zip_sha256": hashlib.sha256(raw).hexdigest(),
    },
}
subprocess.run(
    ["gh", "api", "repos/eschan145/public-ci-bridge/dispatches", "--method", "POST", "--input", "-"],
    input=json.dumps(payload),
    text=True,
    check=True,
)
print("Fixture smoke dispatch accepted")
