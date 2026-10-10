import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate import validate

class TestValidation(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate("example", "a" * 40)["checkout_path"], "source")
    def test_reject_injection(self):
        for name in ("../example", "example;echo", "example/../x", ""):
            with self.assertRaises(ValueError):
                validate(name, "a" * 40)
    def test_reject_branch_names(self):
        with self.assertRaises(ValueError):
            validate("example", "main")

if __name__ == "__main__":
    unittest.main()
