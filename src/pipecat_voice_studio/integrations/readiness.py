"""Operator-facing integration readiness without exposing credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipecat_voice_studio.config import Settings


def integration_readiness(settings: Settings) -> dict[str, tuple[bool, str]]:
    """Return configuration readiness and a concise missing-setting hint."""
    public = settings.pvs_public_base_url is not None
    return {
        "Twilio": (
            public
            and settings.twilio_account_sid is not None
            and settings.twilio_auth_token is not None
            and settings.twilio_from_number is not None,
            "PVS_PUBLIC_BASE_URL, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER",
        ),
        "Vonage": (
            public
            and settings.vonage_application_id is not None
            and settings.vonage_api_key is not None
            and settings.vonage_private_key is not None
            and settings.vonage_signature_secret is not None
            and settings.vonage_from_number is not None,
            (
                "PVS_PUBLIC_BASE_URL, VONAGE_APPLICATION_ID, VONAGE_API_KEY, "
                "VONAGE_PRIVATE_KEY, VONAGE_SIGNATURE_SECRET, VONAGE_FROM_NUMBER"
            ),
        ),
        "Google Calendar": (
            settings.google_service_account_json is not None
            and settings.google_calendar_id is not None,
            "GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_CALENDAR_ID",
        ),
        "HubSpot": (
            settings.hubspot_private_app_token is not None,
            "HUBSPOT_PRIVATE_APP_TOKEN",
        ),
        "Simli": (
            settings.simli_api_key is not None and settings.simli_face_id is not None,
            "SIMLI_API_KEY, SIMLI_FACE_ID",
        ),
        "Healthcare": (
            settings.pvs_healthcare_enabled
            and settings.pvs_healthcare_data_key is not None
            and bool(settings.healthcare_approved_services),
            "PVS_HEALTHCARE_ENABLED, PVS_HEALTHCARE_DATA_KEY, PVS_HEALTHCARE_APPROVED_SERVICES",
        ),
    }
