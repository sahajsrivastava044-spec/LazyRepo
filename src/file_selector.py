
import re
from dataclasses import dataclass

from src.repository_scanner import ScanResult


STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this",
    "when", "then", "into", "have", "has", "not", "are",
    "was", "were", "can", "could", "should", "would",
    "issue", "bug", "error", "fails", "failure", "problem",
}

GENERATED_DIRS = {
    "target",
    "out",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

GENERATED_SUFFIXES = {
    ".class",
    ".pyc",
}

COMMON_TERM_FILE_THRESHOLD = 3


@dataclass
class FileCandidate:
    path: str
    score: int
    matched_terms: list[str]


@dataclass
class FileSelection:
    candidates: list[FileCandidate]
    warning: str | None = None

    @property
    def selected_paths(self) -> list[str]:
        return [candidate.path for candidate in self.candidates]


def _tokenize(text: str) -> set[str]:
    # Split camelCase too: "loginController" -> "login", "controller"
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return {
        token.lower()
        for token in re.findall(r"[a-zA-Z0-9]+", text)
        if len(token) >= 2 and token.lower() not in STOP_WORDS
    }


def select_relevant_files(
    scan_result: ScanResult,
    issue_text: str,
    max_files: int = 5,
) -> FileSelection:
    if max_files < 1:
        raise ValueError("max_files must be at least 1")

    issue_terms = _tokenize(issue_text)

    if not issue_terms:
        return FileSelection(
            candidates=[],
            warning="The issue description contains no usable keywords.",
        )

    eligible_files: list[tuple[str, set[str], set[str]]] = []
    for path in scan_result.files:
        path_parts = path.split("/")
        lower_parts = [part.lower() for part in path_parts]

        # Build outputs are rarely the source of truth for an issue.
        if any(part in GENERATED_DIRS for part in lower_parts):
            continue

        if any(
            part.endswith(tuple(GENERATED_SUFFIXES))
            for part in lower_parts
        ):
            continue

        filename_terms = _tokenize(path_parts[-1])
        directory_terms = _tokenize(" ".join(path_parts[:-1]))

        eligible_files.append((path, filename_terms, directory_terms))

    term_file_counts: dict[str, int] = {}
    for _, filename_terms, directory_terms in eligible_files:
        for term in filename_terms | directory_terms:
            term_file_counts[term] = term_file_counts.get(term, 0) + 1

    common_issue_terms = {
        term
        for term in issue_terms
        if term_file_counts.get(term, 0) >= COMMON_TERM_FILE_THRESHOLD
    }
    specific_issue_terms = issue_terms - common_issue_terms
    has_specific_path_match = any(
        specific_issue_terms & (filename_terms | directory_terms)
        for _, filename_terms, directory_terms in eligible_files
    )
    ranked_issue_terms = (
        specific_issue_terms if has_specific_path_match else issue_terms
    )

    ranked: list[FileCandidate] = []
    for path, filename_terms, directory_terms in eligible_files:
        matched_filename = ranked_issue_terms & filename_terms
        matched_directories = (
            ranked_issue_terms & directory_terms
        ) - matched_filename

        score = len(matched_filename) * 3
        score += len(matched_directories)

        if score > 0:
            ranked.append(
                FileCandidate(
                    path=path,
                    score=score,
                    matched_terms=sorted(
                        matched_filename | matched_directories
                    ),
                )
            )

    # Stable tie-break: paths sort alphabetically.
    ranked.sort(key=lambda candidate: (-candidate.score, candidate.path))

    selected = ranked[:max_files]

    return FileSelection(
        candidates=selected,
        warning=(
            None
            if selected
            else "No repository paths matched the issue keywords."
        ),
    )
