import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from cryptography.fernet import Fernet

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from secure_bundle import encrypt, decrypt

class BundleTests(unittest.TestCase):
    def test_roundtrip_exact_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / 'repo'
            repo.mkdir()
            subprocess.run(['git','init','-q',str(repo)], check=True)
            (repo/'source.txt').write_text('initial')
            subprocess.run(['git','-C',str(repo),'add','.'], check=True)
            subprocess.run(['git','-C',str(repo),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','first'],check=True)
            sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], text=True).strip()
            (repo/'source.txt').write_text('uncommitted secret')
            key=Fernet.generate_key()
            encrypt(str(repo), sha, root/'archive.bin', key)
            ciphertext=(root/'archive.bin').read_bytes()
            self.assertNotIn(b'initial',ciphertext)
            self.assertNotIn(b'uncommitted secret',ciphertext)
            decrypt(root/'archive.bin', root/'output',key)
            self.assertEqual((root/'output/source.txt').read_text(),'initial')
            with self.assertRaises(Exception):
                decrypt(root/'archive.bin', root/'wrong', Fernet.generate_key())

    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            tarbytes=io.BytesIO()
            with tarfile.open(fileobj=tarbytes,mode='w:gz') as tar:
                content=b'untrusted'
                info=tarfile.TarInfo('../escape.txt')
                info.size=len(content)
                tar.addfile(info,io.BytesIO(content))
            key=Fernet.generate_key()
            (root/'archive.bin').write_bytes(Fernet(key).encrypt(tarbytes.getvalue()))
            with self.assertRaises(ValueError):
                decrypt(root/'archive.bin',root/'output',key)
            self.assertFalse((root/'escape.txt').exists())

if __name__=='__main__':
    unittest.main()
