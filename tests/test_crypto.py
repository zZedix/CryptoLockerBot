import os
import tempfile
import unittest

from crypto import build_context, decrypt, encrypt


class CryptoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.salt_path = os.path.join(self.temp_dir.name, "salt")
        with open(self.salt_path, "wb") as fh:
            fh.write(b"0123456789abcdef")
        self.context = build_context("test-passphrase", self.salt_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_encrypt_roundtrip(self) -> None:
        plaintext = "secret123"
        ciphertext = encrypt(plaintext, self.context)
        self.assertNotEqual(ciphertext, plaintext.encode("utf-8"))
        recovered = decrypt(ciphertext, self.context)
        self.assertEqual(recovered, plaintext)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
