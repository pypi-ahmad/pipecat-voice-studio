"""Security boundary tests."""

import base64
import hashlib
import hmac

import jwt
import pytest
from cryptography.exceptions import InvalidTag

from pipecat_voice_studio.security import (
    HealthcareCipher,
    InvalidHealthcareKeyError,
    InvalidMediaTokenError,
    InvalidTelephoneNumberError,
    digest_phone,
    redact_phone,
    require_e164,
    sign_media_token,
    verify_media_token,
    verify_twilio_signature,
    verify_vonage_webhook,
)


def test_phone_validation_redaction_and_digest() -> None:
    assert require_e164("+15551234567") == "+15551234567"
    assert redact_phone("+15551234567") == "4567"
    assert digest_phone("+15551234567", "secret") == digest_phone("+15551234567", "secret")
    with pytest.raises(InvalidTelephoneNumberError):
        require_e164("5551234567")


def test_healthcare_cipher_round_trip_and_session_binding() -> None:
    key = base64.urlsafe_b64encode(b"k" * 32).decode()
    cipher = HealthcareCipher(key)
    encrypted, nonce = cipher.encrypt({"symptoms": ["cough"]}, session_id="one")

    assert cipher.decrypt(encrypted, nonce, session_id="one") == {"symptoms": ["cough"]}
    with pytest.raises(InvalidTag):
        cipher.decrypt(encrypted, nonce, session_id="two")
    with pytest.raises(InvalidHealthcareKeyError):
        HealthcareCipher(base64.urlsafe_b64encode(b"short").decode())


def test_media_token_authentication_and_expiry() -> None:
    token = sign_media_token("call", "secret", now=100)

    assert verify_media_token(token, "secret", now=101) == "call"
    with pytest.raises(InvalidMediaTokenError):
        verify_media_token(token, "wrong", now=101)
    with pytest.raises(InvalidMediaTokenError):
        verify_media_token(token, "secret", now=1000)


def test_provider_webhook_signatures() -> None:
    url = "https://voice.example/answer"
    params = {"CallSid": "CA1", "From": "+15551234567"}
    message = url + "".join(key + params[key] for key in sorted(params))
    signature = base64.b64encode(
        hmac.new(b"token", message.encode(), hashlib.sha1).digest()
    ).decode()
    assert verify_twilio_signature(url, params, signature, "token")
    assert not verify_twilio_signature(url, params, "wrong", "token")

    authorization = "Bearer " + jwt.encode(
        {"api_key": "key", "iat": 100}, "signature-secret", algorithm="HS256"
    )
    assert verify_vonage_webhook(authorization, "signature-secret", "key")
    assert not verify_vonage_webhook(authorization, "wrong", "key")
