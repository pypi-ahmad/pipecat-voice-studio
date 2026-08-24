"""Small security primitives shared by external integration boundaries."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
AES_256_KEY_BYTES = 32


class InvalidTelephoneNumberError(ValueError):
    """Raised when a telephone number is not canonical E.164."""


class InvalidHealthcareKeyError(ValueError):
    """Raised when the configured healthcare encryption key is invalid."""


class InvalidMediaTokenError(ValueError):
    """Raised when a media token is malformed, invalid, or expired."""


def require_e164(value: str) -> str:
    """Validate and return a canonical E.164 telephone number."""
    if not E164_PATTERN.fullmatch(value):
        raise InvalidTelephoneNumberError
    return value


def redact_phone(value: str) -> str:
    """Return only the final four digits of a validated telephone number."""
    return require_e164(value)[-4:]


def digest_phone(value: str, secret: str) -> str:
    """Return a keyed stable identifier without retaining the telephone number."""
    return hmac.new(secret.encode(), require_e164(value).encode(), hashlib.sha256).hexdigest()


class HealthcareCipher:
    """Encrypt structured healthcare intake using an operator-owned AES-256 key."""

    def __init__(self, encoded_key: str) -> None:
        try:
            key = base64.urlsafe_b64decode(encoded_key)
        except (ValueError, TypeError) as error:
            raise InvalidHealthcareKeyError from error
        if len(key) != AES_256_KEY_BYTES:
            raise InvalidHealthcareKeyError
        self._cipher = AESGCM(key)

    def encrypt(self, payload: dict[str, Any], *, session_id: str) -> tuple[bytes, bytes]:
        """Encrypt one JSON payload and bind it to its session identifier."""
        nonce = os.urandom(12)
        plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        return self._cipher.encrypt(nonce, plaintext, session_id.encode()), nonce

    def decrypt(self, ciphertext: bytes, nonce: bytes, *, session_id: str) -> dict[str, Any]:
        """Decrypt a payload for tests and controlled non-UI exports."""
        value = json.loads(self._cipher.decrypt(nonce, ciphertext, session_id.encode()))
        if not isinstance(value, dict):
            raise TypeError
        return value


def sign_media_token(call_id: str, secret: str, *, now: int | None = None) -> str:
    """Create a short-lived token binding a media connection to one call."""
    timestamp = int(time.time()) if now is None else now
    payload = f"{call_id}.{timestamp}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_media_token(
    token: str, secret: str, *, max_age_seconds: int = 300, now: int | None = None
) -> str:
    """Verify a media token and return its bound call identifier."""
    try:
        call_id, raw_timestamp, supplied = token.rsplit(".", 2)
        timestamp = int(raw_timestamp)
    except (TypeError, ValueError) as error:
        raise InvalidMediaTokenError from error
    current = int(time.time()) if now is None else now
    if timestamp > current + 30 or current - timestamp > max_age_seconds:
        raise InvalidMediaTokenError
    expected = hmac.new(
        secret.encode(), f"{call_id}.{timestamp}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied, expected):
        raise InvalidMediaTokenError
    return call_id


def verify_twilio_signature(url: str, params: dict[str, str], signature: str, token: str) -> bool:
    """Verify Twilio's HMAC-SHA1 webhook signature."""
    message = url + "".join(key + params[key] for key in sorted(params))
    expected = base64.b64encode(hmac.new(token.encode(), message.encode(), hashlib.sha1).digest())
    return hmac.compare_digest(signature.encode(), expected)


def verify_vonage_webhook(authorization: str, secret: str, api_key: str) -> bool:
    """Verify a signed Vonage webhook JWT and its expected API key."""
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return False
    try:
        payload = jwt.decode(
            authorization.removeprefix(prefix),
            secret,
            algorithms=["HS256"],
            options={"require": ["iat"]},
        )
    except jwt.PyJWTError:
        return False
    return hmac.compare_digest(str(payload.get("api_key", "")), api_key)
