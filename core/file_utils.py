"""
File Utilities

Utilities for safe file reading, including handling of large files.
"""

import os
from typing import Optional, Tuple
from pathlib import Path


# Maximum file size to read at once (in MB)
MAX_FILE_SIZE_MB = 50

# Maximum file size for safe reading (in bytes) - 50MB
MAX_SAFE_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB
    """
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def is_file_too_large(file_path: str, max_size_mb: int = MAX_FILE_SIZE_MB) -> bool:
    """
    Check if a file is too large to read safely.

    Args:
        file_path: Path to the file
        max_size_mb: Maximum allowed file size in MB

    Returns:
        True if file exceeds the maximum size
    """
    try:
        size_mb = get_file_size_mb(file_path)
        return size_mb > max_size_mb
    except OSError:
        return False


def read_file_safe(
    file_path: str,
    encoding: str = 'utf-8',
    max_size_mb: Optional[int] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely read a text file with size checking.

    Args:
        file_path: Path to the file
        encoding: File encoding (default: utf-8)
        max_size_mb: Maximum allowed file size in MB (default: 50MB)

    Returns:
        Tuple of (content, error_message)
        - If successful: (file_content, None)
        - If error: (None, error_message)
    """
    if max_size_mb is None:
        max_size_mb = MAX_FILE_SIZE_MB

    # Check if file exists
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"

    # Check file size
    try:
        size_mb = get_file_size_mb(file_path)
        if size_mb > max_size_mb:
            return None, (
                f"File too large: {size_mb:.1f}MB (max: {max_size_mb}MB). "
                f"Consider using chunked reading for large files."
            )
    except OSError as e:
        return None, f"Cannot determine file size: {str(e)}"

    # Read file
    try:
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
        return content, None
    except Exception as e:
        return None, f"Error reading file: {str(e)}"


def read_file_chunked(
    file_path: str,
    chunk_size: int = 1024 * 1024,  # 1MB chunks
    encoding: str = 'utf-8'
):
    """
    Read a file in chunks (generator function).

    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk in bytes
        encoding: File encoding

    Yields:
        Chunks of file content
    """
    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def read_file_with_limit(
    file_path: str,
    max_chars: int = 1000000,  # 1M characters
    encoding: str = 'utf-8'
) -> Tuple[str, bool]:
    """
    Read a file up to a maximum number of characters.

    Args:
        file_path: Path to the file
        max_chars: Maximum number of characters to read
        encoding: File encoding

    Returns:
        Tuple of (content, was_truncated)
    """
    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
        content = f.read(max_chars + 1)
        was_truncated = len(content) > max_chars
        if was_truncated:
            content = content[:max_chars]
        return content, was_truncated


def process_large_file_in_place(
    file_path: str,
    replacements: dict,
    encoding: str = 'utf-8',
    backup: bool = True
) -> Tuple[bool, Optional[str], int]:
    """
    Process a large file by reading and writing in chunks.
    Useful for path replacement in large AEPX files.

    Args:
        file_path: Path to the file
        replacements: Dictionary of {old_value: new_value} for replacements
        encoding: File encoding
        backup: Whether to create a backup before modifying

    Returns:
        Tuple of (success, error_message, replacement_count)
    """
    try:
        # Create backup if requested
        if backup:
            backup_path = f"{file_path}.backup"
            import shutil
            shutil.copy2(file_path, backup_path)

        # Read file with size check
        size_mb = get_file_size_mb(file_path)

        # For smaller files (< 50MB), read all at once
        if size_mb < MAX_FILE_SIZE_MB:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                content = f.read()

            replacement_count = 0
            for old_value, new_value in replacements.items():
                count = content.count(old_value)
                replacement_count += count
                content = content.replace(old_value, new_value)

            # Write back
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            return True, None, replacement_count

        # For larger files, use a temporary file and process in chunks
        else:
            temp_path = f"{file_path}.tmp"
            replacement_count = 0

            with open(file_path, 'r', encoding=encoding, errors='ignore') as infile, \
                 open(temp_path, 'w', encoding=encoding) as outfile:

                # Process in larger chunks for better performance
                chunk_size = 10 * 1024 * 1024  # 10MB chunks

                while True:
                    chunk = infile.read(chunk_size)
                    if not chunk:
                        break

                    # Apply replacements
                    for old_value, new_value in replacements.items():
                        count = chunk.count(old_value)
                        replacement_count += count
                        chunk = chunk.replace(old_value, new_value)

                    outfile.write(chunk)

            # Replace original with temp file
            import shutil
            shutil.move(temp_path, file_path)

            return True, None, replacement_count

    except Exception as e:
        return False, f"Error processing file: {str(e)}", 0
