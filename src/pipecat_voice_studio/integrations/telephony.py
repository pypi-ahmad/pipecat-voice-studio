"""Twilio and Vonage Voice REST operations for calls and handoffs.

Implements outbound call initiation and call transfer (warm handoff) for Twilio
Programmable Voice and Vonage Voice APIs. Strictly enforces the outbound E.164
number allowlist to prevent accidental or malicious dialing. Next module to read:
`telephony_gateway.py` for how incoming carrier webhook callbacks are routed.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx
import jwt

from pipecat_voice_studio.security import require_e164

if TYPE_CHECKING:
    from pipecat_voice_studio.config import Settings


class TelephonyNotConfiguredError(RuntimeError):
    """Raised when a selected provider is missing required configuration."""


class DestinationNotAllowedError(PermissionError):
    """Raised when an outbound destination is not explicitly allowlisted."""


def require_allowed_destination(settings: Settings, destination: str) -> str:
    """Validate E.164 and require an exact configured outbound match."""

    number = require_e164(destination)
    if number not in settings.outbound_allowlist:
        raise DestinationNotAllowedError
    return number


class TwilioVoice:
    """Minimal Twilio Programmable Voice client."""

    def __init__(self, settings: Settings) -> None:
        auth_token = settings.twilio_auth_token
        if not all(
            [
                settings.twilio_account_sid,
                auth_token,
                settings.twilio_from_number,
                settings.pvs_public_base_url,
            ]
        ):
            raise TelephonyNotConfiguredError
        if auth_token is None:
            raise TelephonyNotConfiguredError
        self._settings = settings
        self._sid = str(settings.twilio_account_sid)
        self._token = auth_token.get_secret_value()

    async def create_call(self, destination: str) -> str:
        """Start an outbound call through the configured answer webhook."""
        number = require_allowed_destination(self._settings, destination)
        payload = {
            "To": number,
            "From": self._settings.twilio_from_number,
            "Url": f"{self._settings.pvs_public_base_url}/telephony/twilio/answer",
            "StatusCallback": f"{self._settings.pvs_public_base_url}/telephony/twilio/status",
            "StatusCallbackEvent": "initiated ringing answered completed",
        }
        async with httpx.AsyncClient(auth=(self._sid, self._token), timeout=20) as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Calls.json",
                data=payload,
            )
        response.raise_for_status()
        return str(response.json()["sid"])

    async def redirect_to_handoff(self, call_sid: str, destination: str, handoff_id: str) -> None:
        """Brief the human destination, then bridge the existing caller."""
        target = require_e164(destination)
        briefing_url = f"{self._settings.pvs_public_base_url}/telephony/twilio/handoff/{handoff_id}"
        twiml = f'<Response><Dial><Number url="{briefing_url}">{target}</Number></Dial></Response>'
        async with httpx.AsyncClient(auth=(self._sid, self._token), timeout=20) as client:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Calls/{call_sid}.json",
                data={"Twiml": twiml},
            )
        response.raise_for_status()


class VonageVoice:
    """Minimal Vonage Voice API client."""

    def __init__(self, settings: Settings) -> None:
        private_key = settings.vonage_private_key
        if not all(
            [
                settings.vonage_application_id,
                private_key,
                settings.vonage_from_number,
                settings.pvs_public_base_url,
            ]
        ):
            raise TelephonyNotConfiguredError
        if private_key is None:
            raise TelephonyNotConfiguredError
        self._settings = settings
        self._application_id = str(settings.vonage_application_id)
        self._private_key = private_key.get_secret_value()

    def token(self) -> str:
        """Create a short-lived application JWT for one Voice API request."""
        now = int(time.time())
        return jwt.encode(
            {
                "application_id": self._application_id,
                "iat": now,
                "exp": now + 300,
                "jti": uuid4().hex,
            },
            self._private_key,
            algorithm="RS256",
        )

    async def _request(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"https://api.nexmo.com/v1{path}",
                headers={"Authorization": f"Bearer {self.token()}"},
                json=payload,
            )
        response.raise_for_status()
        return response.json() if response.content else {}

    async def create_call(self, destination: str) -> str:
        """Start an outbound call through the configured answer webhook."""
        number = require_allowed_destination(self._settings, destination)
        result = await self._request(
            "POST",
            "/calls",
            {
                "to": [{"type": "phone", "number": number}],
                "from": [{"type": "phone", "number": self._settings.vonage_from_number}],
                "answer_url": [f"{self._settings.pvs_public_base_url}/telephony/vonage/answer"],
                "event_url": [f"{self._settings.pvs_public_base_url}/telephony/vonage/events"],
            },
        )
        return str(result["uuid"])

    async def redirect_to_handoff(self, call_uuid: str, destination: str, handoff_id: str) -> None:
        """Transfer an active Vonage call to a human telephone endpoint."""
        await self._request(
            "PUT",
            f"/calls/{call_uuid}",
            {
                "action": "transfer",
                "destination": {
                    "type": "ncco",
                    "ncco": [
                        {
                            "action": "connect",
                            "from": self._settings.vonage_from_number,
                            "endpoint": [
                                {
                                    "type": "phone",
                                    "number": require_e164(destination),
                                    "onAnswer": {
                                        "url": (
                                            f"{self._settings.pvs_public_base_url}"
                                            f"/telephony/vonage/handoff/{handoff_id}"
                                        )
                                    },
                                }
                            ],
                        }
                    ],
                },
            },
        )
