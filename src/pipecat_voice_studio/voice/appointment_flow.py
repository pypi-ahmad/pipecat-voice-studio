"""Pipecat Flow nodes for the local appointment tool."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipecat.flows import FlowManager, NodeConfig

    from pipecat_voice_studio.appointments import AppointmentBook


def build_appointment_flow(book: AppointmentBook, session_id: str) -> NodeConfig:
    """Build a confirmation-gated appointment flow for one session."""

    def record_node(node: str, *, outcome: str | None = None) -> None:
        payload = {"node": node}
        if outcome is not None:
            payload["outcome"] = outcome
        book.store.append_event(session_id, "flow.node", payload)

    async def confirm_appointment(
        flow_manager: FlowManager, confirmed: bool
    ) -> tuple[dict[str, Any], NodeConfig]:
        """Create the proposed appointment only after the user explicitly confirms it."""
        proposal = flow_manager.state.get("proposal", {})
        if not confirmed:
            record_node("finish", outcome="denied")
            return {"status": "cancelled"}, finish_node("The user cancelled the appointment.")
        appointment_id = book.create(
            session_id=session_id,
            attendee_name=str(proposal["attendee_name"]),
            purpose=str(proposal["purpose"]),
            starts_at=datetime.fromisoformat(str(proposal["starts_at"])),
            confirmed=True,
            flow_node="confirmation",
        )
        record_node("finish", outcome="confirmed")
        return {"status": "confirmed", "appointment_id": appointment_id}, finish_node(
            "Confirm the appointment details and end politely."
        )

    def confirmation_node() -> NodeConfig:
        return {
            "name": "confirmation",
            "role_message": "You are a careful appointment assistant.",
            "task_messages": [
                {
                    "role": "developer",
                    "content": (
                        "Read back every appointment field and ask for explicit confirmation."
                    ),
                }
            ],
            "functions": [confirm_appointment],
        }

    async def check_availability(
        flow_manager: FlowManager,
        attendee_name: str,
        purpose: str,
        starts_at: str,
    ) -> tuple[dict[str, Any], NodeConfig]:
        """Check a timezone-aware ISO start and prepare a 30-minute appointment proposal."""
        start = datetime.fromisoformat(starts_at)
        if not book.is_available(start):
            suggestions = [slot.isoformat() for slot in book.suggest(start)]
            record_node("collect", outcome="unavailable")
            return {"status": "unavailable", "suggestions": suggestions}, collect_node()
        flow_manager.state["proposal"] = {
            "attendee_name": attendee_name,
            "purpose": purpose,
            "starts_at": start.isoformat(),
            "duration_minutes": 30,
        }
        record_node("confirmation", outcome="available")
        return {"status": "available", "duration_minutes": 30}, confirmation_node()

    def collect_node() -> NodeConfig:
        return {
            "name": "collect",
            "role_message": "You are a careful appointment assistant.",
            "task_messages": [
                {
                    "role": "developer",
                    "content": "Collect attendee name, purpose, and a timezone-aware start time.",
                }
            ],
            "functions": [check_availability],
        }

    def finish_node(message: str) -> NodeConfig:
        return {
            "name": "finish",
            "task_messages": [{"role": "developer", "content": message}],
            "functions": [],
        }

    return collect_node()
