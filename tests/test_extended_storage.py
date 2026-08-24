"""Persistence tests for provider and governance records."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pipecat_voice_studio.appointments import AppointmentBook
from pipecat_voice_studio.storage import StudioStore


@pytest.fixture
def store(tmp_path: Path) -> StudioStore:
    value = StudioStore(tmp_path / "extended.db")
    value.initialize()
    return value


def _session(store: StudioStore, *, sensitive: bool = False) -> str:
    pipeline_id = store.list_graphs()[0]["id"]
    return store.create_session(pipeline_id, store.get_graph(pipeline_id), {}, sensitive=sensitive)


def test_bindings_calls_and_handoffs(store: StudioStore) -> None:
    pipeline_id = store.list_graphs()[0]["id"]
    store.set_integration_binding("twilio", pipeline_id)
    assert store.get_integration_binding("twilio") == pipeline_id
    with pytest.raises(KeyError):
        store.get_integration_binding("missing")

    call_id = store.create_call(
        provider="twilio",
        direction="outbound",
        remote_last_four="4567",
        remote_digest="digest",
        provider_call_id="CA1",
    )
    store.update_call(call_id, status="answered", session_id=_session(store))
    assert store.get_call(call_id)["status"] == "answered"
    assert store.get_call_by_provider_id("twilio", "CA1")["id"] == call_id

    handoff_id = store.create_handoff(
        call_id=call_id,
        session_id=None,
        provider="twilio",
        destination_last_four="9999",
        summary="Caller needs a human.",
    )
    store.update_handoff(handoff_id, status="transferred")
    assert store.get_handoff(handoff_id)["summary"] == "Caller needs a human."
    assert store.list_handoffs()[0]["status"] == "transferred"
    assert store.list_calls()[0]["remote_last_four"] == "4567"


def test_calendar_crm_healthcare_and_audit_records(store: StudioStore) -> None:
    session_id = _session(store, sensitive=True)
    book = AppointmentBook(store, "UTC")
    appointment_id = book.create(
        session_id=session_id,
        attendee_name="Ada",
        purpose="Review",
        starts_at=datetime(2030, 1, 2, 10, tzinfo=UTC),
        confirmed=True,
        flow_node="confirmation",
    )
    store.link_appointment_provider(
        appointment_id,
        provider="google",
        external_id="event-1",
        external_status="confirmed",
    )
    assert store.apply_calendar_changes([{"id": "event-1", "status": "cancelled"}]) == 1
    store.save_calendar_sync(sync_token="next")  # noqa: S106
    state = store.get_calendar_sync()
    assert state is not None
    assert state["sync_token"] == "next"  # noqa: S105

    record_id = store.record_crm_result(
        session_id=session_id,
        contact_id="contact",
        deal_id="deal",
        contact_last_four="4567",
        score=90,
        status="completed",
    )
    assert record_id

    store.save_healthcare_consent(session_id, accepted=True, policy_version="v1")
    intake_id = store.save_healthcare_intake(
        session_id,
        ciphertext=b"encrypted",
        nonce=b"nonce",
        status="review-required",
        escalated=False,
    )
    assert store.list_healthcare_metadata()[0]["id"] == intake_id
    store.append_audit(
        action="created",
        resource_type="intake",
        resource_id=intake_id,
        outcome="ok",
    )
