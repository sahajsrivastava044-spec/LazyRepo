
import unittest
from pathlib import Path

from src.file_selector import select_relevant_files
from src.repository_scanner import ScanResult


class TestFileSelector(unittest.TestCase):

    def setUp(self):
        self.scan = ScanResult(
            root=Path("/fake/repo"),
            files=[
                "src/auth/login_controller.py",
                "src/auth/email_service.py",
                "tests/test_login.py",
                "docs/setup.md",
                "src/payment/checkout.py",
            ],
            complete=True,
        )

    def test_filename_match_ranks_higher(self):
        result = select_relevant_files(
            self.scan,
            "login controller returns incorrect email",
        )

        self.assertEqual(
            result.selected_paths[0],
            "src/auth/login_controller.py",
        )

    def test_selection_respects_limit(self):
        result = select_relevant_files(
            self.scan,
            "login email",
            max_files=2,
        )

        self.assertEqual(len(result.selected_paths), 2)

    def test_results_are_deterministic(self):
        first = select_relevant_files(self.scan, "login email")
        second = select_relevant_files(self.scan, "login email")

        self.assertEqual(first.candidates, second.candidates)

    def test_unmatched_issue_returns_warning(self):
        result = select_relevant_files(
            self.scan,
            "quantum satellite telemetry",
        )

        self.assertEqual(result.selected_paths, [])
        self.assertIsNotNone(result.warning)

    def test_empty_issue_returns_warning(self):
        result = select_relevant_files(self.scan, "the and for")

        self.assertEqual(result.selected_paths, [])
        self.assertIsNotNone(result.warning)

    def test_invalid_limit_raises_error(self):
        with self.assertRaises(ValueError):
            select_relevant_files(self.scan, "login", max_files=0)

    def test_candidate_explains_its_match(self):
        result = select_relevant_files(self.scan, "login controller")

        candidate = result.candidates[0]
        self.assertIn("login", candidate.matched_terms)
        self.assertIn("controller", candidate.matched_terms)
    
    
    def test_generated_build_directories_are_excluded(self):
        scan = ScanResult(
            root=Path("/fake/repo"),
            files=[
                "target/classes/ProjectRegistry.class",
                "target/surefire-reports/ProjectRegistryTest.xml",
                "src/main/java/ProjectRegistry.java",
            ],
            complete=True,
        )

        result = select_relevant_files(
            scan,
            "ProjectRegistry lookup fails",
        )

        self.assertEqual(
            result.selected_paths,
            ["src/main/java/ProjectRegistry.java"],
        )

    def test_class_files_are_excluded_outside_build_directories(self):
        scan = ScanResult(
            root=Path("/fake/repo"),
            files=[
                "out/ProjectRegistry.class",
                "ProjectRegistry.class",
                "ProjectRegistry.java",
            ],
            complete=True,
        )

        result = select_relevant_files(scan, "ProjectRegistry lookup fails")

        self.assertNotIn("out/ProjectRegistry.class", result.selected_paths)
        self.assertNotIn("ProjectRegistry.class", result.selected_paths)
        self.assertIn("ProjectRegistry.java", result.selected_paths)

    def test_unrelated_generated_files_do_not_fill_selection_limit(self):
        scan = ScanResult(
            root=Path("/fake/repo"),
            files=[
                "target/classes/Login.class",
                "build/Login.class",
                "src/Login.java",
            ],
            complete=True,
        )

        result = select_relevant_files(
            scan,
            "Login fails",
            max_files=3,
        )

        self.assertEqual(result.selected_paths, ["src/Login.java"])

    def test_project_registry_issue_selects_implementation_and_test_together(self):
        scan = ScanResult(
            root=Path("/fake/repo"),
            files=[
                "src/main/java/com/nexus/domain/project/ProjectRegistry.java",
                "src/test/java/com/nexus/domain/project/ProjectRegistryTest.java",
                "src/main/java/com/nexus/domain/project/Project.java",
                "src/main/java/com/nexus/discovery/ProjectDiscovery.java",
                "src/main/java/com/nexus/storage/ProjectStorage.java",
            ],
            complete=True,
        )

        result = select_relevant_files(
            scan,
            "Project registry fails to find a project by ID",
        )

        self.assertEqual(
            result.selected_paths,
            [
                "src/main/java/com/nexus/domain/project/ProjectRegistry.java",
                "src/test/java/com/nexus/domain/project/ProjectRegistryTest.java",
            ],
        )



if __name__ == "__main__":
    unittest.main()
