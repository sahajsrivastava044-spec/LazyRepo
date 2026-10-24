
import tempfile
import unittest
from pathlib import Path

from src.repository_scanner import scan_repository


class TestRepositoryScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_file(self, relative_path: str):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("example", encoding="utf-8")

    def test_scans_files_in_sorted_relative_path_order(self):
        self.create_file("src/z.py")
        self.create_file("README.md")
        self.create_file("src/a.py")

        result = scan_repository(self.root)

        self.assertEqual(
            result.files,
            ["README.md", "src/a.py", "src/z.py"],
        )
        self.assertTrue(result.complete)
        self.assertIsNone(result.warning)

    def test_ignores_unwanted_directories(self):
        self.create_file("src/main.py")
        self.create_file(".git/config")
        self.create_file(".venv/lib/package.py")
        self.create_file("node_modules/package/index.js")

        result = scan_repository(self.root)

        self.assertEqual(result.files, ["src/main.py"])

    def test_returns_partial_inventory_with_warning(self):
        self.create_file("a.py")
        self.create_file("b.py")
        self.create_file("c.py")

        result = scan_repository(self.root, max_files=2)

        self.assertEqual(len(result.files), 2)
        self.assertFalse(result.complete)
        self.assertIsNotNone(result.warning)

    def test_exact_limit_can_still_be_complete(self):
        self.create_file("a.py")
        self.create_file("b.py")

        result = scan_repository(self.root, max_files=2)

        self.assertEqual(len(result.files), 2)
        self.assertTrue(result.complete)
        self.assertIsNone(result.warning)

    def test_rejects_nonexistent_path(self):
        missing = self.root / "does-not-exist"

        with self.assertRaises(FileNotFoundError):
            scan_repository(missing)

    def test_rejects_file_as_repository_path(self):
        self.create_file("README.md")

        with self.assertRaises(NotADirectoryError):
            scan_repository(self.root / "README.md")

    def test_rejects_invalid_file_limit(self):
        with self.assertRaises(ValueError):
            scan_repository(self.root, max_files=0)

    def test_custom_ignored_directories(self):
        self.create_file("build/output.py")
        self.create_file("src/main.py")

        result = scan_repository(
            self.root,
            ignored_dirs={".git", "build"},
        )

        self.assertEqual(result.files, ["src/main.py"])


if __name__ == "__main__":
    unittest.main()
