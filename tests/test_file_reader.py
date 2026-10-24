
import tempfile
import unittest
from pathlib import Path

from src.file_reader import read_repository_file


class TestFileReader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_file(self, relative_path, content=b"example"):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_reads_text_and_preserves_relative_path(self):
        self.create_file("src/auth.py", b"def login():\n    return True\n")

        result = read_repository_file(self.root, "src/auth.py")

        self.assertEqual(result.status, "read")
        self.assertEqual(result.path, "src/auth.py")
        self.assertIn("def login():", result.content)
        self.assertIn("2:     return True", result.numbered_content)

    def test_skips_file_over_size_limit(self):
        self.create_file("large.txt", b"x" * 11)

        result = read_repository_file(
            self.root, "large.txt", max_bytes=10
        )

        self.assertEqual(result.status, "skipped")
        self.assertIn("exceeds", result.reason)
        self.assertIsNone(result.content)

    def test_accepts_file_exactly_at_size_limit(self):
        self.create_file("exact.txt", b"12345")

        result = read_repository_file(
            self.root, "exact.txt", max_bytes=5
        )

        self.assertEqual(result.status, "read")
        self.assertEqual(result.content, "12345")

    def test_rejects_path_traversal(self):
        outside = self.root.parent / "outside-lazyrepo-test.txt"
        outside.write_text("secret", encoding="utf-8")
        try:
            result = read_repository_file(
                self.root, "../outside-lazyrepo-test.txt"
            )
            self.assertEqual(result.status, "skipped")
            self.assertIn("outside", result.reason)
        finally:
            outside.unlink(missing_ok=True)

    def test_reports_missing_file(self):
        result = read_repository_file(self.root, "missing.py")

        self.assertEqual(result.status, "error")
        self.assertIsNotNone(result.reason)

    def test_skips_binary_content(self):
        self.create_file("image.bin", b"\x00\x01\x02")

        result = read_repository_file(self.root, "image.bin")

        self.assertEqual(result.status, "skipped")
        self.assertIn("Binary", result.reason)

    def test_skips_invalid_utf8(self):
        self.create_file("invalid.txt", b"\xff\xfe")

        result = read_repository_file(self.root, "invalid.txt")

        self.assertEqual(result.status, "skipped")
        self.assertIn("UTF-8", result.reason)

    def test_rejects_invalid_size_limit(self):
        with self.assertRaises(ValueError):
            read_repository_file(self.root, "file.txt", max_bytes=0)

    def test_does_not_modify_the_file(self):
        original = b"print('hello')\n"
        self.create_file("main.py", original)

        read_repository_file(self.root, "main.py")

        self.assertEqual(
            (self.root / "main.py").read_bytes(), original
        )


if __name__ == "__main__":
    unittest.main()
