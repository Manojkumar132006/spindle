"""Content hashing and incremental file change detection."""

import enum
import hashlib
from pathlib import Path


class FileChangeStatus(enum.StrEnum):
    """Change status for incremental synchronization."""

    UNMODIFIED = "unmodified"
    MODIFIED = "modified"
    NEW = "new"
    DELETED = "deleted"


def calculate_content_hash(content: str | bytes) -> str:
    """Calculate SHA-256 hash of string or byte content."""
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content
    return hashlib.sha256(content_bytes).hexdigest()


def calculate_file_hash(file_path: Path | str) -> str:
    """Read a local file and return its SHA-256 hash."""
    path = Path(file_path)
    return calculate_content_hash(path.read_bytes())


def detect_file_changes(
    indexed_hashes: dict[str, str],
    incoming_contents: dict[str, str],
) -> dict[str, tuple[FileChangeStatus, str]]:
    """Compare incoming file contents against indexed hashes to determine changes.

    Returns a mapping of file_path -> (FileChangeStatus, content_hash).
    """
    results: dict[str, tuple[FileChangeStatus, str]] = {}

    # Check incoming files
    for file_path, content in incoming_contents.items():
        current_hash = calculate_content_hash(content)
        if file_path not in indexed_hashes:
            results[file_path] = (FileChangeStatus.NEW, current_hash)
        elif indexed_hashes[file_path] != current_hash:
            results[file_path] = (FileChangeStatus.MODIFIED, current_hash)
        else:
            results[file_path] = (FileChangeStatus.UNMODIFIED, current_hash)

    # Check for deleted files (in indexed_hashes but not in incoming_contents)
    for file_path, existing_hash in indexed_hashes.items():
        if file_path not in incoming_contents:
            results[file_path] = (FileChangeStatus.DELETED, existing_hash)

    return results
