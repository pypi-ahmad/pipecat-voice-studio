"""Pipecat Flow routing for business specialists, CRM, and human handoff.

Implements the multi-agent business flow: a receptionist node that routes callers
to specialist departments (`billing`, `technical`, `sales`, `appointments`),
handles consent-verified lead creation into HubSpot CRM, and transfers callers
to human agents over active Twilio or Vonage telephone calls. Must not create CRM
records without caller consent or initiate handoffs without a configured carrier
destination. Next module to read: `integrations/telephony.py` for carrier
bridging and `integrations/hubspot.py` for CRM lead upserting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pipecat_voice_studio.integrations.hubspot import HubSpot
from pipecat_voice_studio.integrations.telephony import TwilioVoice, VonageVoice
from pipecat_voice_studio.security import redact_phone

if TYPE_CHECKING:
    from pipecat.flows import FlowManager, NodeConfig

    from pipecat_voice_studio.config import Settings
    from pipecat_voice_studio.storage import StudioStore


def build_business_flow(
    store: StudioStore,
    settings: Settings,
    session_id: str,
    *,
    call_id: str | None,
) -> NodeConfig:
    """Build a deterministic receptionist and specialist handoff flow."""

    def specialist_node(department: str) -> NodeConfig:
        tasks = {
            "billing": "Resolve billing questions. Never invent account data.",
            "technical": "Diagnose the technical issue and give concise verified steps.",
            "sales": "Qualify the lead. Ask need, timeline, budget, name, and email.",
            "appointments": "Help the caller clarify their appointment request.",
        }
        functions: list[Any] = [route_department, request_human]
        if department == "sales" and settings.hubspot_private_app_token is not None:
            functions.append(save_lead)
        return {
            "name": department,
            "role_message": f"You are the {department} specialist.",
            "task_messages": [{"role": "developer", "content": tasks[department]}],
            "functions": functions,
        }

    async def route_department(
        flow_manager: FlowManager,
        department: Literal["billing", "technical", "sales", "appointments"],
    ) -> tuple[dict[str, str], NodeConfig]:
        """Route the conversation to one allowlisted specialist."""
        del flow_manager
        store.append_event(session_id, "agent.routed", {"department": department})
        return {"status": "routed", "department": department}, specialist_node(department)

    async def save_lead(
        flow_manager: FlowManager,
        consent: bool,
        email: str,
        first_name: str,
        last_name: str = "",
        phone: str | None = None,
        score: int | None = None,
        notes: str = "",
    ) -> tuple[dict[str, str], NodeConfig]:
        """Write a lead only after the caller explicitly grants CRM consent."""
        del flow_manager
        if settings.hubspot_private_app_token is None:
            return {"status": "unavailable"}, specialist_node("sales")
        hubspot = HubSpot(settings.hubspot_private_app_token.get_secret_value())
        try:
            contact_id, deal_id = await hubspot.upsert_lead(
                consent=consent,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                score=score,
                notes=notes,
            )
        except Exception as error:
            store.record_crm_result(
                session_id=session_id,
                contact_id=None,
                deal_id=None,
                contact_last_four=redact_phone(phone) if phone else None,
                score=score,
                status="failed",
                failure=type(error).__name__,
            )
            raise
        store.record_crm_result(
            session_id=session_id,
            contact_id=contact_id,
            deal_id=deal_id,
            contact_last_four=redact_phone(phone) if phone else None,
            score=score,
            status="completed",
        )
        return {"status": "saved", "contact_id": contact_id}, specialist_node("sales")

    async def request_human(
        flow_manager: FlowManager, reason: str, summary: str
    ) -> tuple[dict[str, str], NodeConfig]:
        """Transfer a telephone caller to the configured human destination."""
        del flow_manager, reason
        if call_id is None:
            return {
                "status": "unavailable",
                "message": "Human transfer requires a phone call.",
            }, reception_node()
        call = store.get_call(call_id)
        provider = str(call["provider"])
        destination = (
            settings.twilio_handoff_destination
            if provider == "twilio"
            else settings.vonage_handoff_destination
        )
        if destination is None or call["provider_call_id"] is None:
            return {"status": "unavailable"}, reception_node()
        handoff_id = store.create_handoff(
            call_id=call_id,
            session_id=session_id,
            provider=provider,
            destination_last_four=redact_phone(destination),
            summary=summary,
        )
        try:
            voice = TwilioVoice(settings) if provider == "twilio" else VonageVoice(settings)
            await voice.redirect_to_handoff(str(call["provider_call_id"]), destination, handoff_id)
        except Exception as error:
            store.update_handoff(handoff_id, status="failed", failure=type(error).__name__)
            raise
        store.update_handoff(handoff_id, status="transferred")
        return {"status": "transferred", "handoff_id": handoff_id}, finish_node()

    def reception_node() -> NodeConfig:
        return {
            "name": "reception",
            "role_message": "You are the receptionist.",
            "task_messages": [
                {
                    "role": "developer",
                    "content": "Ask what the caller needs, then route to exactly one specialist.",
                }
            ],
            "functions": [route_department, request_human],
        }

    def finish_node() -> NodeConfig:
        return {
            "name": "human_handoff",
            "task_messages": [
                {"role": "developer", "content": "Tell the caller they are being connected."}
            ],
            "functions": [],
        }

    return reception_node()
