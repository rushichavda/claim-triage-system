"""
PHI (Protected Health Information) handling utilities.
Tokenization, redaction, and detection for HIPAA compliance.
"""

import hashlib
import re
from typing import Any

# Common PHI field names (for automatic detection)
PHI_FIELD_PATTERNS = [
    r".*name.*",
    r".*ssn.*",
    r".*social.*security.*",
    r".*dob.*",
    r".*date.*birth.*",
    r".*address.*",
    r".*phone.*",
    r".*email.*",
    r".*mrn.*",  # Medical Record Number
    r".*member.*id.*",
]


def is_phi_field(field_name: str) -> bool:
    """
    Check if a field name suggests it contains PHI.

    Args:
        field_name: Name of the field to check

    Returns:
        True if field likely contains PHI
    """
    field_lower = field_name.lower()

    for pattern in PHI_FIELD_PATTERNS:
        if re.match(pattern, field_lower):
            return True

    return False


def tokenize_phi(value: str, salt: str = "claim-triage-salt") -> str:
    """
    Create a deterministic token for PHI.
    This allows matching/grouping without exposing actual values.

    Args:
        value: PHI value to tokenize
        salt: Salt for hashing (use per-organization salt in production)

    Returns:
        Hex-encoded hash token (e.g., "PHI_a3f5c8...")
    """
    if not value:
        return ""

    hash_input = f"{salt}:{value}".encode()
    token_hash = hashlib.sha256(hash_input).hexdigest()[:16]  # First 16 chars

    return f"PHI_{token_hash}"


def redact_phi(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Redact common PHI patterns from text.
    This is a basic implementation - production systems should use
    Presidio or similar NLP-based PII detection.

    Args:
        text: Text potentially containing PHI
        replacement: String to replace PHI with

    Returns:
        Text with PHI patterns redacted
    """
    # SSN patterns
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", replacement, text)
    text = re.sub(r"\b\d{9}\b", replacement, text)

    # Phone numbers
    text = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", replacement, text)
    text = re.sub(r"\(\d{3}\)\s*\d{3}[-.]?\d{4}", replacement, text)

    # Email addresses
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", replacement, text)

    # Dates (potential DOB)
    text = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", replacement, text)
    text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", replacement, text)

    return text


def redact_dict_phi(data: dict[str, Any], auto_detect: bool = True) -> dict[str, Any]:
    """
    Redact PHI from a dictionary.

    Args:
        data: Dictionary potentially containing PHI
        auto_detect: Whether to automatically detect PHI fields by name

    Returns:
        New dictionary with PHI redacted
    """
    redacted = {}

    for key, value in data.items():
        # Check if field name suggests PHI
        if auto_detect and is_phi_field(key):
            redacted[key] = tokenize_phi(str(value)) if value else None
        elif isinstance(value, str):
            # Redact text content
            redacted[key] = redact_phi(value)
        elif isinstance(value, dict):
            # Recurse into nested dicts
            redacted[key] = redact_dict_phi(value, auto_detect=auto_detect)
        elif isinstance(value, list):
            # Handle lists
            redacted[key] = [
                redact_dict_phi(item, auto_detect=auto_detect) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value

    return redacted


def mask_phi(value: str, show_last: int = 4) -> str:
    """
    Partially mask PHI (e.g., show last 4 digits of SSN/account).

    Args:
        value: Value to mask
        show_last: Number of characters to show at the end

    Returns:
        Masked value (e.g., "***-**-1234")
    """
    if not value or len(value) <= show_last:
        return "*" * len(value) if value else ""

    masked_length = len(value) - show_last
    return "*" * masked_length + value[-show_last:]
