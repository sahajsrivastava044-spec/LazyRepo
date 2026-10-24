
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.evidence_builder import EvidencePackage
from src.file_reader import FileReadResult
from src.local_analyzer import (
    _contradictory_test_assertions,
    _fit_complete_lines,
    analyze_evidence,
)


class TestLocalAnalyzer(unittest.TestCase):

    def setUp(self):
        self.evidence = EvidencePackage(
            repository_root=Path("/fake/repo"),
            files=[
                FileReadResult(
                    path="src/auth.py",
                    status="read",
                    content="def login(): pass",
                    numbered_content="1: def login(): pass",
                )
            ],
            inventory_file_count=1,
            scan_complete=True,
            scan_warning=None,
        )

    @patch("src.local_analyzer.urlopen")
    def test_successful_analysis(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {"content": "Finding: see src/auth.py:1"}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence("Login fails", self.evidence)

        self.assertIn("src/auth.py:1", result.report)
        self.assertIn("## Verification status", result.report)
        self.assertEqual(result.evidence_files, ["src/auth.py"])
        self.assertEqual(result.warnings, [])

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "qwen2.5-coder:3b")
        self.assertFalse(payload["stream"])
        self.assertIn(
            "Do not invent an exception contract",
            payload["messages"][0]["content"],
        )

    def test_empty_issue_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_evidence("  ", self.evidence)

    def test_no_readable_evidence_is_rejected(self):
        empty_evidence = EvidencePackage(
            repository_root=Path("/fake/repo"),
            files=[
                FileReadResult(
                    path="src/auth.py",
                    status="skipped",
                    reason="File exceeds size limit.",
                )
            ],
            inventory_file_count=1,
            scan_complete=True,
            scan_warning=None,
        )

        with self.assertRaises(ValueError):
            analyze_evidence("Login fails", empty_evidence)

    @patch("src.local_analyzer.urlopen")
    def test_empty_model_response_is_rejected(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {"content": " "}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        with self.assertRaises(RuntimeError):
            analyze_evidence("Login fails", self.evidence)
    
    def test_fit_complete_lines_does_not_return_partial_line(self):
        content = "1: first line\n2: second line\n3: third line\n"

        result = _fit_complete_lines(content, 20)

        self.assertEqual(result, "1: first line\n")
        self.assertLessEqual(len(result), 20)

    def test_fit_complete_lines_keeps_later_line_after_oversized_line(self):
        content = "1: " + "x" * 30 + "\n2: useful\n"

        self.assertEqual(_fit_complete_lines(content, 20), "2: useful\n")

    def test_correctly_described_expected_null_is_not_a_contradiction(self):
        assertions = {
            "findProjectById": [
                (
                    "src/test/java/ProjectRegistryTest.java",
                    42,
                    'assertNull(registry.findProjectById("unknown-id"));',
                    "Null",
                )
            ]
        }
        report = (
            "The unknown-ID lookup returns null as expected; this is not a bug."
        )

        self.assertEqual(
            _contradictory_test_assertions(report, assertions),
            [],
        )

    def test_fit_complete_lines_returns_empty_when_first_line_does_not_fit(self):
        content = "1: a longer line\n"

        result = _fit_complete_lines(content, 3)

        self.assertEqual(result, "")

    @patch("src.local_analyzer.urlopen")
    def test_evidence_budget_favors_earlier_files_and_warns_on_truncation(
        self, mock_urlopen
    ):
        evidence = EvidencePackage(
            repository_root=Path("/fake/repo"),
            files=[
                FileReadResult(
                    path="src/important.py",
                    status="read",
                    content=None,
                    numbered_content="1: aaa\n2: bbb\n3: ccc\n",
                ),
                FileReadResult(
                    path="tests/test_important.py",
                    status="read",
                    content=None,
                    numbered_content="1: xxx\n2: yyy\n3: zzz\n",
                ),
            ],
            inventory_file_count=2,
            scan_complete=True,
            scan_warning=None,
        )

        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {"content": "Analysis completed."}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence(
            "Important behavior fails",
            evidence,
            max_total_chars=100,
        )

        request = mock_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        prompt = payload["messages"][1]["content"]

        # Both files should contribute evidence.
        self.assertEqual(
            result.evidence_files,
            ["src/important.py", "tests/test_important.py"],
        )
        self.assertIn("1: aaa\n2: bbb\n", prompt)
        self.assertIn("1: xxx\n", prompt)

        # The earlier file receives more content than the later file.
        first_file_content = prompt.split("FILE: src/important.py\n", 1)[1]
        first_file_content = first_file_content.split("```", 2)[1]

        second_file_content = prompt.split(
            "FILE: tests/test_important.py\n", 1
        )[1]
        second_file_content = second_file_content.split("```", 2)[1]

        self.assertGreater(
            len(first_file_content),
            len(second_file_content),
        )

        # Truncation must be visible to the caller.
        self.assertTrue(
            any("src/important.py" in warning for warning in result.warnings)
        )
        self.assertTrue(
            any(
                "tests/test_important.py" in warning
                for warning in result.warnings
            )
        )
        evidence_text = prompt.split(
            "REPOSITORY EVIDENCE:\n\n", 1
        )[1].split("\n\nEVIDENCE LIMITATIONS:", 1)[0]
        self.assertLessEqual(len(evidence_text), 100)

    @patch("src.local_analyzer.urlopen")
    def test_long_line_is_omitted_without_hiding_later_complete_lines(
        self, mock_urlopen
    ):
        evidence = EvidencePackage(
            repository_root=Path("/fake/repo"),
            files=[
                FileReadResult(
                    path="src/long.py",
                    status="read",
                    numbered_content=(
                        "1: " + "x" * 100 + "\n"
                        "2: useful later context\n"
                    ),
                )
            ],
            inventory_file_count=1,
            scan_complete=True,
            scan_warning=None,
        )
        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {"content": "Analysis completed."}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence(
            "Investigate this behavior",
            evidence,
            max_total_chars=70,
        )

        payload = json.loads(
            mock_urlopen.call_args.args[0].data.decode("utf-8")
        )
        prompt = payload["messages"][1]["content"]
        self.assertIn("2: useful later context\n", prompt)
        self.assertNotIn("1: " + "x" * 100, prompt)
        self.assertEqual(result.evidence_files, ["src/long.py"])
        self.assertTrue(
            any("source lines 1" in warning for warning in result.warnings)
        )
        evidence_text = prompt.split(
            "REPOSITORY EVIDENCE:\n\n", 1
        )[1].split("\n\nEVIDENCE LIMITATIONS:", 1)[0]
        self.assertLessEqual(len(evidence_text), 70)

    @patch("src.local_analyzer.urlopen")
    def test_malformed_response_shape_is_rejected(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"message": "not an object"}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        with self.assertRaisesRegex(RuntimeError, "malformed"):
            analyze_evidence("Login fails", self.evidence)

    @patch("src.local_analyzer.urlopen")
    def test_contradictory_null_claim_is_replaced_by_evidence_report(
        self, mock_urlopen
    ):
        evidence = EvidencePackage(
            repository_root=Path("/fake/repo"),
            files=[
                FileReadResult(
                    path="src/main/java/ProjectRegistry.java",
                    status="read",
                    numbered_content=(
                        "31: public Project findProjectById(String id){\n"
                        "32:     return projects.get(id);\n"
                        "33: }\n"
                    ),
                ),
                FileReadResult(
                    path="src/test/java/ProjectRegistryTest.java",
                    status="read",
                    numbered_content=(
                        "22: assertSame(project,registry.findProjectById(project.getId()));\n"
                        "42: assertNull(registry.findProjectById(\"unknown-id\"));\n"
                    ),
                ),
            ],
            inventory_file_count=2,
            scan_complete=True,
            scan_warning=None,
        )
        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {
                "content": (
                    "The likely issue is that findProjectById incorrectly "
                    "returns null for an unknown ID. Add a new test for "
                    "findProjectById with an unknown ID."
                )
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence(
            "Project registry fails to find a project by ID",
            evidence,
        )

        prompt = json.loads(
            mock_urlopen.call_args.args[0].data.decode("utf-8")
        )["messages"][1]["content"]
        self.assertIn("32:     return projects.get(id);", prompt)
        self.assertIn(
            '42: assertNull(registry.findProjectById("unknown-id"));',
            prompt,
        )
        self.assertIn("Insufficient evidence to identify a bug.", result.report)
        self.assertIn("ProjectRegistryTest.java:22", result.report)
        self.assertIn("ProjectRegistryTest.java:42", result.report)
        self.assertNotIn("The likely issue is", result.report)
        self.assertTrue(
            any("conflicts with visible test assertions" in warning
                for warning in result.warnings)
        )

    @patch("src.local_analyzer.urlopen")
    def test_evidence_backed_key_mismatch_diagnosis_is_retained(
        self, mock_urlopen
    ):
        evidence = EvidencePackage(
                repository_root=Path("/fake/repo"),
                files=[
                    FileReadResult(
                        path="src/main/java/ProjectRegistry.java",
                        status="read",
                        numbered_content=(
                            "10: projects.put(project.getId(), project);\n"
                            "11: public Project findProjectById(String id) {\n"
                            "12:     return projects.get(project.getPath());\n"
                        ),
                    ),
                    FileReadResult(
                        path="src/test/java/ProjectRegistryTest.java",
                        status="read",
                        numbered_content=(
                            "22: assertSame(project, "
                            "registry.findProjectById(project.getId()));\n"
                        ),
                    ),
                ],
                inventory_file_count=2,
                scan_complete=True,
                scan_warning=None,
        )
        response = MagicMock()
        response.read.return_value = json.dumps({
                "message": {
                    "content": (
                        "The lookup has a key mismatch: registration stores the "
                        "project under project.getId() "
                        "(src/main/java/ProjectRegistry.java:10), but "
                        "findProjectById retrieves using project.getPath() "
                        "(src/main/java/ProjectRegistry.java:12). The existing "
                        "test expects lookup by ID to return the registered "
                        "project (src/test/java/ProjectRegistryTest.java:22). "
                        "This mismatch plausibly explains the reported failure."
                    )
                }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence(
                "Project registry fails to find a project by ID",
                evidence,
        )

        self.assertIn("key mismatch", result.report)
        self.assertIn("src/main/java/ProjectRegistry.java:10", result.report)
        self.assertIn("src/main/java/ProjectRegistry.java:12", result.report)
        self.assertIn(
                "src/test/java/ProjectRegistryTest.java:22",
                result.report,
        )
        self.assertNotIn("Insufficient evidence to identify a bug.", result.report)
        self.assertNotIn("response was withheld", result.report)
        self.assertEqual(result.warnings, [])

    @patch("src.local_analyzer.urlopen")
    def test_reports_citations_missing_from_supplied_evidence(
        self, mock_urlopen
    ):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {"content": "See src/auth.py:2"}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence("Login fails", self.evidence)

        self.assertTrue(
            any("src/auth.py:2" in warning for warning in result.warnings)
        )
        self.assertIn("response was withheld", result.report)

    @patch("src.local_analyzer.urlopen")
    def test_unverified_claim_that_tests_ran_is_withheld(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({
            "message": {"content": "The tests passed and confirm the fix."}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = response

        result = analyze_evidence("Login fails", self.evidence)

        self.assertIn("response was withheld", result.report)
        self.assertNotIn("The tests passed", result.report)
        self.assertTrue(
            any("did not execute" in warning for warning in result.warnings)
        )


if __name__ == "__main__":
    unittest.main()
