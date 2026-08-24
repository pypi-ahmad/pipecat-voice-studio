"""Deterministic appointment availability and mutation policy."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4
from zoneinfo import ZoneInfo

from pipecat_voice_studio.storage import StudioStore, _now

if TYPE_CHECKING:
    from pipecat_voice_studio.integrations.google_calendar import GoogleCalendar

SLOT_MINUTES = 30
OPEN_HOUR = 9
CLOSE_HOUR = 17
WEEKEND_START = 5


class AppointmentBook:
    """Local mock calendar with explicit confirmation enforcement."""

    def __init__(
        self, store: StudioStore, timezone: str, calendar: GoogleCalendar | None = None
    ) -> None:
        self.store = store
        self.timezone = ZoneInfo(timezone)
        self.calendar = calendar

    def normalize(self, starts_at: datetime) -> datetime:
        """Require aware datetimes and normalize into the studio timezone."""
        if starts_at.tzinfo is None:
            raise ValueError("Appointment start must include a timezone")
        return starts_at.astimezone(self.timezone).replace(second=0, microsecond=0)

    def is_available(self, starts_at: datetime) -> bool:
        """Check business hours and collision state."""
        start = self.normalize(starts_at)
        end = start + timedelta(minutes=SLOT_MINUTES)
        if start.weekday() >= WEEKEND_START or start.minute not in {0, 30}:
            return False
        if (
            start.hour < OPEN_HOUR
            or end.hour > CLOSE_HOUR
            or (end.hour == CLOSE_HOUR and end.minute > 0)
        ):
            return False
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM appointments WHERE starts_at = ? AND status = 'confirmed'",
                (start.isoformat(),),
            ).fetchone()
        return row is None

    def suggest(self, starts_at: datetime, *, count: int = 3) -> list[datetime]:
        """Return the next available half-hour slots."""
        cursor = self.normalize(starts_at)
        suggestions: list[datetime] = []
        while len(suggestions) < count:
            cursor += timedelta(minutes=SLOT_MINUTES)
            if self.is_available(cursor):
                suggestions.append(cursor)
        return suggestions

    def create(
        self,
        *,
        session_id: str | None,
        attendee_name: str,
        purpose: str,
        starts_at: datetime,
        confirmed: bool,
        flow_node: str,
    ) -> str:
        """Create only from the confirmation node after a current affirmative response."""
        if not confirmed or flow_node != "confirmation":
            raise PermissionError("Appointment creation requires explicit confirmation")
        start = self.normalize(starts_at)
        if not attendee_name.strip() or not purpose.strip():
            raise ValueError("Attendee name and purpose are required")
        if not self.is_available(start):
            raise ValueError("The requested slot is unavailable")
        appointment_id = uuid4().hex
        try:
            with self.store.connect() as connection:
                connection.execute(
                    "INSERT INTO appointments(id, session_id, attendee_name, purpose, "
                    "starts_at, duration_minutes, status, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?)",
                    (
                        appointment_id,
                        session_id,
                        attendee_name.strip(),
                        purpose.strip(),
                        start.isoformat(),
                        SLOT_MINUTES,
                        _now(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("The requested slot was just taken") from error
        return appointment_id

    async def is_available_external(self, starts_at: datetime) -> bool:
        """Check local policy and Google Calendar when configured."""
        start = self.normalize(starts_at)
        return self.is_available(start) and (
            self.calendar is None or await self.calendar.is_available(start)
        )

    async def create_confirmed(
        self,
        *,
        session_id: str | None,
        attendee_name: str,
        purpose: str,
        starts_at: datetime,
    ) -> str:
        """Create a confirmation-gated local record and synchronized Google event."""
        start = self.normalize(starts_at)
        external: dict[str, object] | None = None
        if self.calendar is not None:
            external = await self.calendar.create_event(
                summary=f"Appointment with {attendee_name.strip()}",
                starts_at=start,
                description=purpose.strip(),
            )
        try:
            appointment_id = self.create(
                session_id=session_id,
                attendee_name=attendee_name,
                purpose=purpose,
                starts_at=start,
                confirmed=True,
                flow_node="confirmation",
            )
        except Exception:
            if self.calendar is not None and external and external.get("id"):
                await self.calendar.cancel_event(str(external["id"]))
            raise
        if external is not None:
            self.store.link_appointment_provider(
                appointment_id,
                provider="google",
                external_id=str(external["id"]),
                external_status=str(external.get("status", "confirmed")),
            )
        return appointment_id
