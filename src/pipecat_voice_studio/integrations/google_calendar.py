"""Google Calendar adapter using service-account OAuth and the REST API.

Provides slot availability checking, confirmed event creation, event cancellation,
and incremental change pagination using Google OAuth service account credentials.
Next module to read: `calendar_worker.py` for the background sync daemon or
`appointments.py` for slot coordination.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"


class GoogleCalendar:
    """Read and write one operator-configured Google calendar."""

    def __init__(self, service_account_json: str, calendar_id: str) -> None:
        info = json.loads(service_account_json)
        self._credentials = service_account.Credentials.from_service_account_info(
            info, scopes=[CALENDAR_SCOPE]
        )
        self._calendar_id = calendar_id

    async def _headers(self) -> dict[str, str]:
        # Refreshes the OAuth access token in a worker thread because Google Auth
        # transport requests perform blocking I/O.
        if not self._credentials.valid:
            await asyncio.to_thread(self._credentials.refresh, Request())
        return {"Authorization": f"Bearer {self._credentials.token}"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = await self._headers()
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{CALENDAR_API}/calendars/{self._calendar_id}/{path}",
                headers=headers,
                params=params,
                json=payload,
            )
        response.raise_for_status()
        return response.json() if response.content else {}

    async def is_available(self, starts_at: datetime, *, minutes: int = 30) -> bool:
        """Return whether the calendar is free for an exact interval."""
        ends_at = starts_at + timedelta(minutes=minutes)
        result = await self._request(
            "GET",
            "events",
            params={
                "timeMin": starts_at.isoformat(),
                "timeMax": ends_at.isoformat(),
                "singleEvents": "true",
                "maxResults": "1",
            },
        )
        return not result.get("items")

    async def create_event(
        self, *, summary: str, starts_at: datetime, minutes: int = 30, description: str = ""
    ) -> dict[str, Any]:
        """Create a confirmed calendar event."""
        return await self._request(
            "POST",
            "events",
            payload={
                "summary": summary,
                "description": description,
                "start": {"dateTime": starts_at.isoformat()},
                "end": {"dateTime": (starts_at + timedelta(minutes=minutes)).isoformat()},
            },
        )

    async def cancel_event(self, event_id: str) -> None:
        """Delete one event by provider identifier."""
        await self._request("DELETE", f"events/{event_id}")

    async def incremental_changes(
        self, sync_token: str | None
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return all changes and the next incremental synchronization token."""
        params = {"syncToken": sync_token} if sync_token else {"singleEvents": "true"}
        changes: list[dict[str, Any]] = []
        while True:
            result = await self._request("GET", "events", params=params)
            changes.extend(result.get("items", []))
            page_token = result.get("nextPageToken")
            if not page_token:
                return changes, result.get("nextSyncToken")
            params["pageToken"] = page_token
