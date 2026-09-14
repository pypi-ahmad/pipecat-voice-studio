"""Incremental Google Calendar synchronization worker.

Runs as a background polling daemon that pulls external calendar events and
syncs status (such as external cancellations) back into local SQLite appointment
records. Must not crash on transient HTTP errors or raise when Google Calendar
credentials are absent. Next module to read: `integrations/google_calendar.py`
for the REST API client and `appointments.py` for appointment state transitions.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

import httpx

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.integrations.google_calendar import GoogleCalendar
from pipecat_voice_studio.storage import StudioStore

# Google Calendar API returns HTTP 410 Gone when an incremental sync token has
# expired or become invalid (typically after a long gap between sync passes).
SYNC_TOKEN_GONE = 410


async def synchronize_once(calendar: GoogleCalendar, store: StudioStore) -> int:
    """Fetch and apply one complete incremental Google Calendar page sequence."""
    state = store.get_calendar_sync()
    token = str(state["sync_token"]) if state and state["sync_token"] else None
    try:
        changes, next_token = await calendar.incremental_changes(token)
    except httpx.HTTPStatusError as error:
        # Fallback to full sync without a token recovers transparently if the token expired.
        if error.response.status_code == SYNC_TOKEN_GONE:
            changes, next_token = await calendar.incremental_changes(None)
        else:
            store.save_calendar_sync(sync_token=token, error=type(error).__name__)
            raise
    updated = store.apply_calendar_changes(changes)
    store.save_calendar_sync(sync_token=next_token)
    return updated


async def run() -> None:
    """Poll the configured calendar until the process is stopped."""
    settings = get_settings()
    if settings.google_service_account_json is None or settings.google_calendar_id is None:
        return
    store = StudioStore(settings.pvs_database_path)
    store.initialize()
    calendar = GoogleCalendar(
        settings.google_service_account_json.get_secret_value(), settings.google_calendar_id
    )
    while True:
        with suppress(httpx.HTTPError):
            await synchronize_once(calendar, store)
        await asyncio.sleep(settings.pvs_calendar_sync_seconds)


if __name__ == "__main__":
    asyncio.run(run())
