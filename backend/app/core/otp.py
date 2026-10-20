"""Secure email OTP generation and storage hashing.

OTPs are short numeric codes. Because a 6-digit code has a tiny keyspace, we
never store the raw code, and we do not store a plain unkeyed hash either (a
database-only attacker could brute-force all 10**6 candidates instantly).
Instead we store a keyed HMAC-SHA256 digest computed with a dedicated
server-side secret. Without that secret the stored digests cannot be reversed
or enumerated.

The purpose ("password_recovery" or "password_change") is bound into the digest
so a code issued for one workflow can never be replayed in the other, even if
the raw digits happen to match.
"""

import hashlib
import hmac
import secrets
from typing import Optional

from app.core.config import settings

# Purposes must be stable strings: they are part of the hashed message and are
# stored on the record, so changing them would invalidate outstanding codes.
PURPOSE_PASSWORD_RECOVERY = "password_recovery"
PURPOSE_PASSWORD_CHANGE = "password_change"

VALID_PURPOSES = frozenset({PURPOSE_PASSWORD_RECOVERY, PURPOSE_PASSWORD_CHANGE})

# HKDF parameters for deriving a distinct key from SECRET_KEY when no dedicated
# OTP_HMAC_SECRET is configured.
_HKDF_SALT = b"sports-injury-risk/otp-hmac/salt-v1"
_HKDF_INFO = b"sports-injury-risk/otp-hmac/key-v1"


def generate_otp(length: Optional[int] = None) -> str:
    """Generate a cryptographically secure numeric OTP.

    Returned as a zero-padded string so codes with leading zeros (e.g.
    "004281") survive intact - callers must treat OTPs as strings, never ints.
    """
    length = length or settings.OTP_LENGTH
    if length < 4:
        raise ValueError("OTP length must be at least 4 digits")
    upper = 10 ** length
    return f"{secrets.randbelow(upper):0{length}d}"


def _hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """Minimal HKDF (RFC 5869) using only the standard library."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm = b""
    block = b""
    counter = 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm += block
        counter += 1
    return okm[:length]


def _otp_key() -> bytes:
    """Return the keyed-HMAC key for OTP hashing."""
    secret = (settings.OTP_HMAC_SECRET or "").strip()
    if secret:
        return secret.encode("utf-8")
    # No dedicated key configured: derive a *distinct* key from SECRET_KEY using
    # HKDF with domain separation. This is key derivation, not naive reuse of
    # SECRET_KEY as the OTP key.
    return _hkdf_sha256(settings.SECRET_KEY.encode("utf-8"), _HKDF_SALT, _HKDF_INFO)


def hash_otp(otp: str, purpose: str) -> str:
    """Return the keyed HMAC-SHA256 hex digest stored for an OTP."""
    if purpose not in VALID_PURPOSES:
        raise ValueError(f"Unknown OTP purpose: {purpose!r}")
    message = f"{purpose}:{otp}".encode("utf-8")
    return hmac.new(_otp_key(), message, hashlib.sha256).hexdigest()


def verify_otp(otp: str, purpose: str, stored_hash: str) -> bool:
    """Constant-time comparison of a candidate OTP against a stored digest."""
    if not otp or not stored_hash:
        return False
    return hmac.compare_digest(hash_otp(otp, purpose), stored_hash)
