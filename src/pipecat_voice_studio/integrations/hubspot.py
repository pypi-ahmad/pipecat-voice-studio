"""Consent-gated HubSpot CRM adapter."""

from __future__ import annotations

from typing import Any

import httpx

HUBSPOT_API = "https://api.hubapi.com"


class CrmConsentRequiredError(PermissionError):
    """Raised when CRM processing was not explicitly accepted."""


class HubSpot:
    """Create or update contacts and optional lead deals in HubSpot."""

    def __init__(self, token: str) -> None:
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(
        self, method: str, path: str, *, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method, f"{HUBSPOT_API}{path}", headers=self._headers, json=payload
            )
        response.raise_for_status()
        return response.json() if response.content else {}

    async def upsert_lead(
        self,
        *,
        consent: bool,
        email: str,
        first_name: str,
        last_name: str = "",
        phone: str | None = None,
        score: int | None = None,
        notes: str = "",
    ) -> tuple[str, str | None]:
        """Upsert a contact, then create a deal and note when supplied."""
        if not consent:
            raise CrmConsentRequiredError
        properties = {"email": email, "firstname": first_name, "lastname": last_name}
        if phone:
            properties["phone"] = phone
        result = await self._request(
            "POST",
            "/crm/v3/objects/contacts/batch/upsert",
            payload={"inputs": [{"idProperty": "email", "id": email, "properties": properties}]},
        )
        contact_id = str(result["results"][0]["id"])
        deal_id: str | None = None
        if score is not None:
            deal = await self._request(
                "POST",
                "/crm/v3/objects/deals",
                payload={"properties": {"dealname": f"Voice lead: {first_name}", "amount": "0"}},
            )
            deal_id = str(deal["id"])
            await self._request(
                "PUT",
                f"/crm/v4/objects/deals/{deal_id}/associations/contacts/{contact_id}/deal_to_contact",
            )
        if notes:
            await self._request(
                "POST",
                "/crm/v3/objects/notes",
                payload={
                    "properties": {"hs_note_body": notes, "hs_timestamp": "1970-01-01T00:00:00Z"},
                    "associations": [
                        {
                            "to": {"id": contact_id},
                            "types": [
                                {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}
                            ],
                        }
                    ],
                },
            )
        return contact_id, deal_id
