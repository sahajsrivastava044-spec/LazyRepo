
from dataclasses import dataclass
from pathlib import Path

from src.file_reader import FileReadResult, read_repository_file
from src.repository_scanner import ScanResult


@dataclass
class EvidencePackage:
    repository_root: Path
    files: list[FileReadResult]
    inventory_file_count: int
    scan_complete: bool
    scan_warning: str | None

    @property
    def successfully_read_count(self) -> int:
        return sum(
            result.status == "read"
            for result in self.files
        )


def build_evidence(
    scan_result: ScanResult,
    selected_paths: list[str],
    max_bytes_per_file: int = 1_000_000,
) -> EvidencePackage:
    if max_bytes_per_file < 1:
        raise ValueError("max_bytes_per_file must be at least 1")

    # Only files present in the inventory can be read.
    inventoried_paths = set(scan_result.files)
    results: list[FileReadResult] = []
    seen_paths: set[str] = set()

    for selected_path in selected_paths:
        relative_path = Path(selected_path).as_posix()

        # Avoid duplicate work if a path was selected more than once.
        if relative_path in seen_paths:
            continue
        seen_paths.add(relative_path)

        if relative_path not in inventoried_paths:
            results.append(
                FileReadResult(
                    path=relative_path,
                    status="skipped",
                    reason="File was not present in the repository inventory.",
                )
            )
            continue

        result = read_repository_file(
            repository_root=scan_result.root,
            relative_path=relative_path,
            max_bytes=max_bytes_per_file,
        )
        results.append(result)

    return EvidencePackage(
        repository_root=scan_result.root,
        files=results,
        inventory_file_count=len(scan_result.files),
        scan_complete=scan_result.complete,
        scan_warning=scan_result.warning,
    )
