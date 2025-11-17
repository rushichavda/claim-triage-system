"""
Encryption utilities for PHI and sensitive data protection.
Uses Fernet (symmetric encryption) for field-level encryption.
"""

import base64
import hashlib
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


# Global encryption key - in production, load from secure key management service
_ENCRYPTION_KEY: Optional[bytes] = None


def get_encryption_key() -> bytes:
    """
    Get or generate encryption key.
    In production, this should load from AWS KMS, HashiCorp Vault, etc.
    """
    global _ENCRYPTION_KEY

    if _ENCRYPTION_KEY is None:
        # Try to load from environment variable
        key_str = os.getenv("ENCRYPTION_KEY")

        if key_str:
            _ENCRYPTION_KEY = key_str.encode()
        else:
            # Generate a new key (for development/demo only)
            # In production, this should NEVER auto-generate
            _ENCRYPTION_KEY = Fernet.generate_key()

    return _ENCRYPTION_KEY


def set_encryption_key(key: bytes) -> None:
    """Set the encryption key (for testing or initialization)."""
    global _ENCRYPTION_KEY
    _ENCRYPTION_KEY = key


def derive_key_from_passphrase(passphrase: str, salt: Optional[bytes] = None) -> bytes:
    """
    Derive an encryption key from a passphrase using PBKDF2.
    Use this for demo/testing when you don't have KMS.
    """
    if salt is None:
        salt = b"claim-triage-system-salt"  # In production, use random salt per entity

    kdf = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=passphrase.encode(),
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf)


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt a field value (e.g., patient name, DOB).

    Args:
        plaintext: The sensitive data to encrypt

    Returns:
        Base64-encoded encrypted value
    """
    if not plaintext:
        return ""

    key = get_encryption_key()
    f = Fernet(key)
    encrypted_bytes = f.encrypt(plaintext.encode())
    return base64.urlsafe_b64encode(encrypted_bytes).decode()


def decrypt_field(encrypted: str) -> str:
    """
    Decrypt a field value.

    Args:
        encrypted: Base64-encoded encrypted value

    Returns:
        Decrypted plaintext

    Raises:
        InvalidToken: If decryption fails (wrong key or corrupted data)
    """
    if not encrypted:
        return ""

    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
        decrypted_bytes = f.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt field: invalid token or wrong key") from e


def encrypt_dict_fields(data: dict[str, any], fields_to_encrypt: list[str]) -> dict[str, any]:
    """
    Encrypt specific fields in a dictionary.

    Args:
        data: Dictionary with sensitive data
        fields_to_encrypt: List of field names to encrypt

    Returns:
        New dictionary with specified fields encrypted
    """
    encrypted_data = data.copy()

    for field in fields_to_encrypt:
        if field in encrypted_data and encrypted_data[field]:
            encrypted_data[field] = encrypt_field(str(encrypted_data[field]))

    return encrypted_data


def decrypt_dict_fields(data: dict[str, any], fields_to_decrypt: list[str]) -> dict[str, any]:
    """
    Decrypt specific fields in a dictionary.

    Args:
        data: Dictionary with encrypted data
        fields_to_decrypt: List of field names to decrypt

    Returns:
        New dictionary with specified fields decrypted
    """
    decrypted_data = data.copy()

    for field in fields_to_decrypt:
        if field in decrypted_data and decrypted_data[field]:
            try:
                decrypted_data[field] = decrypt_field(decrypted_data[field])
            except ValueError:
                # Field might not be encrypted, leave as-is
                pass

    return decrypted_data
