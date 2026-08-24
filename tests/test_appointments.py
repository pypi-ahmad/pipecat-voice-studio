"""Appointment policy tests."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from pipecat_voice_studio.appointments import AppointmentBook
from pipecat_voice_studio.storage import StudioStore


@pytest.fixture
def book(tmp_path: Path) -> AppointmentBook:
    store = StudioStore(tmp_path / "studio.db")
    store.initialize()
    return AppointmentBook(store, "Asia/Calcutta")


def test_create_requires_confirmation_node_and_affirmation(book: AppointmentBook) -> None:
    start = datetime(2026, 8, 25, 10, 0, tzinfo=ZoneInfo("Asia/Calcutta"))

    with pytest.raises(PermissionError, match="explicit confirmation"):
        book.create(
            session_id=None,
            attendee_name="Ada",
            purpose="Demo",
            starts_at=start,
            confirmed=False,
            flow_node="confirmation",
        )


def test_create_rechecks_collision_and_suggests_three_slots(book: AppointmentBook) -> None:
    start = datetime(2026, 8, 25, 10, 0, tzinfo=ZoneInfo("Asia/Calcutta"))
    appointment_id = book.create(
        session_id=None,
        attendee_name="Ada",
        purpose="Demo",
        starts_at=start,
        confirmed=True,
        flow_node="confirmation",
    )

    assert appointment_id
    assert not book.is_available(start)
    suggestions = book.suggest(start)
    assert len(suggestions) == 3
    assert suggestions[0].hour == 10 and suggestions[0].minute == 30
    with pytest.raises(ValueError, match="unavailable"):
        book.create(
            session_id=None,
            attendee_name="Grace",
            purpose="Review",
            starts_at=start,
            confirmed=True,
            flow_node="confirmation",
        )
