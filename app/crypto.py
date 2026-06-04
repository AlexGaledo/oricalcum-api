"""Symmetric encryption for project secrets (Fernet, AES-128-CBC + HMAC).

The key is read from `secrets_encryption_key` (a urlsafe-base64 32-byte key,
e.g. `Fernet.generate_key().decode()`). If unset, secret writes/reads raise a
clear 500 so misconfiguration is obvious rather than silently storing plaintext.
"""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    key = get_settings().secrets_encryption_key
    if not key:
        raise HTTPException(
            status_code=500,
            detail="secrets_encryption_key is not configured on the server",
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid secrets_encryption_key: {exc}",
        )


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise HTTPException(status_code=500, detail="Failed to decrypt secret")
