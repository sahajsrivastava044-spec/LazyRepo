
from dataclasses import dataclass
from pathlib import Path


DEFAULT_IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
}


@dataclass
class ScanResult:
    root: Path
    files: list[str]
    complete: bool
    warning: str | None = None


def scan_repository(
    repository_path: str | Path,
    max_files: int = 500,
    ignored_dirs: set[str] | None = None,
) -> ScanResult:
    root = Path(repository_path).resolve()

    if not root.exists():
        raise FileNotFoundError(
            f"Repository path does not exist: {root}"
        )

    if not root.is_dir():
        raise NotADirectoryError(
            f"Repository path is not a directory: {root}"
        )

    if max_files < 1:
        raise ValueError("max_files must be at least 1")

    ignored = (
        DEFAULT_IGNORED_DIRS
        if ignored_dirs is None
        else ignored_dirs
    )

    discovered_files: list[str] = []

    for current_dir, dir_names, file_names in __import__(
        "os"
    ).walk(root):
        # Prune ignored directories before descending into them.
        dir_names[:] = sorted(
            name for name in dir_names if name not in ignored
        )

        for file_name in sorted(file_names):
            file_path = Path(current_dir) / file_name

            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(root).as_posix()
            discovered_files.append(relative_path)

            if len(discovered_files) >= max_files:
                # Determine whether eligible files remain.
                # We cannot assume the inventory is incomplete
                # just because the limit was reached exactly.
                has_more = _has_more_eligible_files(
                    root,
                    ignored,
                    set(discovered_files),
                )

                return ScanResult(
                    root=root,
                    files=sorted(discovered_files),
                    complete=not has_more,
                    warning=(
                        "Scan limit reached; inventory may be "
                        "incomplete."
                        if has_more
                        else None
                    ),
                )

    return ScanResult(
        root=root,
        files=sorted(discovered_files),
        complete=True,
    )


def _has_more_eligible_files(
    root: Path,
    ignored_dirs: set[str],
    discovered: set[str],
) -> bool:
    import os

    for current_dir, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(
            name for name in dir_names if name not in ignored_dirs
        )

        for file_name in file_names:
            file_path = Path(current_dir) / file_name

            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(root).as_posix()

            if relative_path not in discovered:
                return True

    return False
