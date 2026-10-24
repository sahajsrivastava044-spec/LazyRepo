
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileReadResult:
    path: str
    status: str
    content: str | None = None
    numbered_content: str | None = None
    reason: str | None = None

def read_repository_file(
    repository_root: str | Path,
    relative_path: str | Path,
    max_bytes: int = 1_000_000,
) -> FileReadResult:
    root = Path(repository_root).resolve()
    requested_path = Path(relative_path)

    if max_bytes < 1:
        raise ValueError("max_bytes must be at least 1")

    # Resolve the path to detect traversal and escaping symlinks.
    target = (root / requested_path).resolve()

    try:
        display_path = target.relative_to(root).as_posix()
    except ValueError:
        return FileReadResult(
            path=str(relative_path),
            status="skipped",
            reason="Requested path is outside the repository.",
        )

    if not target.is_file():
        return FileReadResult(
            path=display_path,
            status="error",
            reason="File does not exist or is not a regular file.",
        )

    try:
        # Reject obviously oversized files before reading them.
        if target.stat().st_size > max_bytes:
            return FileReadResult(
                path=display_path,
                status="skipped",
                reason=f"File exceeds the {max_bytes}-byte limit.",
            )

        # Read at most one byte beyond the limit. This also catches
        # a file that grows after the size check.
        with target.open("rb") as file:
            raw_content = file.read(max_bytes + 1)

        if len(raw_content) > max_bytes:
            return FileReadResult(
                path=display_path,
                status="skipped",
                reason=f"File exceeds the {max_bytes}-byte limit.",
            )

        if b"\x00" in raw_content:
            return FileReadResult(
                path=display_path,
                status="skipped",
                reason="Binary content detected.",
            )

        try:
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            return FileReadResult(
                path=display_path,
                status="skipped",
                reason="File is not valid UTF-8 text.",
            )

        numbered_lines = [
            f"{line_number}: {line}"
            for line_number, line in enumerate(
                content.splitlines(), start=1
            )
        ]

        return FileReadResult(
            path=display_path,
            status="read",
            content=content,
            numbered_content="\n".join(numbered_lines),
        )

    except OSError as error:
        return FileReadResult(
            path=display_path,
            status="error",
            reason=f"Could not read file: {error}",
        )
