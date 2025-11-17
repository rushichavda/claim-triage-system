"""
Content hashing and verification utilities for document integrity.
"""

import hashlib
from pathlib import Path
from typing import Union


def hash_content(content: Union[str, bytes], algorithm: str = "sha256") -> str:
    """
    Generate a cryptographic hash of content.

    Args:
        content: Content to hash (string or bytes)
        algorithm: Hash algorithm (sha256, sha512, etc.)

    Returns:
        Hexadecimal hash digest
    """
    if isinstance(content, str):
        content = content.encode()

    hasher = hashlib.new(algorithm)
    hasher.update(content)

    return hasher.hexdigest()


def hash_file(file_path: Union[str, Path], algorithm: str = "sha256") -> str:
    """
    Generate a cryptographic hash of a file.
    Handles large files efficiently using chunked reading.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm

    Returns:
        Hexadecimal hash digest
    """
    hasher = hashlib.new(algorithm)
    path = Path(file_path)

    with open(path, "rb") as f:
        # Read in 64KB chunks for memory efficiency
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_hash(content: Union[str, bytes], expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    Verify content matches an expected hash.

    Args:
        content: Content to verify
        expected_hash: Expected hash value
        algorithm: Hash algorithm used

    Returns:
        True if hash matches
    """
    actual_hash = hash_content(content, algorithm)
    return actual_hash == expected_hash


def verify_file_hash(file_path: Union[str, Path], expected_hash: str, algorithm: str = "sha256") -> bool:
    """
    Verify file matches an expected hash.

    Args:
        file_path: Path to file
        expected_hash: Expected hash value
        algorithm: Hash algorithm used

    Returns:
        True if hash matches
    """
    actual_hash = hash_file(file_path, algorithm)
    return actual_hash == expected_hash
