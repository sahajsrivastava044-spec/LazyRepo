
import tempfile
import unittest
from pathlib import Path

from src.evidence_builder import build_evidence
from src.repository_scanner import scan_repository


class TestEvidenceBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_file(self, relative_path, content="example"):
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_builds_evidence_from_selected_files(self):
        self.create_file("src/auth.py", "def login():\n    return True\n")
        self.create_file("tests/test_auth.py", "def test_login():\n    pass\n")
        self.create_file("README.md", "Project documentation")

        scan = scan_repository(self.root)
        package = build_evidence(
            scan, ["src/auth.py", "tests/test_auth.py"]
        )

        self.assertEqual(package.inventory_file_count, 3)
        self.assertEqual(package.successfully_read_count, 2)
        self.assertEqual(
            [item.path for item in package.files],
            ["src/auth.py", "tests/test_auth.py"],
        )

    def test_preserves_incomplete_scan_warning(self):
        self.create_file("a.py", "a")
        self.create_file("b.py", "b")
        self.create_file("c.py", "c")

        scan = scan_repository(self.root, max_files=2)
        package = build_evidence(scan, scan.files[:1])

        self.assertFalse(package.scan_complete)
        self.assertIsNotNone(package.scan_warning)
        self.assertEqual(package.successfully_read_count, 1)

    def test_reports_selected_path_missing_from_inventory(self):
        self.create_file("src/main.py", "print('hello')")

        scan = scan_repository(self.root)
        package = build_evidence(scan, ["not_in_inventory.py"])

        self.assertEqual(package.files[0].status, "skipped")
        self.assertIn("inventory", package.files[0].reason)

    def test_does_not_process_duplicate_paths_twice(self):
        self.create_file("src/main.py", "print('hello')")

        scan = scan_repository(self.root)
        package = build_evidence(
            scan, ["src/main.py", "src/main.py"]
        )

        self.assertEqual(len(package.files), 1)
        self.assertEqual(package.successfully_read_count, 1)

    def test_preserves_reader_size_limit_exclusion(self):
        self.create_file("large.txt", "x" * 20)

        scan = scan_repository(self.root)
        package = build_evidence(
            scan, ["large.txt"], max_bytes_per_file=10
        )

        self.assertEqual(package.files[0].status, "skipped")
        self.assertIn("exceeds", package.files[0].reason)

    def test_empty_selection_produces_empty_evidence(self):
        self.create_file("src/main.py", "print('hello')")

        scan = scan_repository(self.root)
        package = build_evidence(scan, [])

        self.assertEqual(package.files, [])
        self.assertEqual(package.successfully_read_count, 0)

    def test_rejects_invalid_file_size_limit(self):
        scan = scan_repository(self.root)

        with self.assertRaises(ValueError):
            build_evidence(scan, [], max_bytes_per_file=0)


if __name__ == "__main__":
    unittest.main()
