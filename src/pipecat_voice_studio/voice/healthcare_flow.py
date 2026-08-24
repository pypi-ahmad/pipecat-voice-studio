"""Consent-first encrypted healthcare intake Flow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipecat.flows import FlowManager, NodeConfig

    from pipecat_voice_studio.security import HealthcareCipher
    from pipecat_voice_studio.storage import StudioStore


POLICY_VERSION = "2026-08"


def build_healthcare_flow(
    store: StudioStore, cipher: HealthcareCipher, session_id: str
) -> NodeConfig:
    """Build a non-diagnostic intake flow with consent and escalation."""

    async def record_consent(
        flow_manager: FlowManager, accepted: bool
    ) -> tuple[dict[str, Any], NodeConfig]:
        del flow_manager
        store.save_healthcare_consent(session_id, accepted=accepted, policy_version=POLICY_VERSION)
        if not accepted:
            return {"status": "declined"}, finish_node("Respect the decision and end the intake.")
        return {"status": "accepted"}, intake_node()

    async def save_intake(
        flow_manager: FlowManager,
        chief_concern: str,
        symptoms: list[str],
        medications: list[str],
        allergies: list[str],
        emergency_signs: bool,
    ) -> tuple[dict[str, Any], NodeConfig]:
        del flow_manager
        payload = {
            "chief_concern": chief_concern,
            "symptoms": symptoms,
            "medications": medications,
            "allergies": allergies,
        }
        ciphertext, nonce = cipher.encrypt(payload, session_id=session_id)
        status = "escalation-required" if emergency_signs else "review-required"
        intake_id = store.save_healthcare_intake(
            session_id,
            ciphertext=ciphertext,
            nonce=nonce,
            status=status,
            escalated=emergency_signs,
        )
        store.append_audit(
            action="healthcare.intake.created",
            resource_type="healthcare_intake",
            resource_id=intake_id,
            outcome=status,
        )
        message = (
            "State that this is not medical advice and direct the caller to emergency services now."
            if emergency_signs
            else "Explain that a qualified human must review the intake."
        )
        return {"status": status, "intake_id": intake_id}, finish_node(message)

    def consent_node() -> NodeConfig:
        return {
            "name": "consent",
            "role_message": "You are a healthcare intake assistant, not a clinician.",
            "task_messages": [
                {
                    "role": "developer",
                    "content": (
                        "Explain data collection, human review, and that this is not medical "
                        "advice. "
                        "Ask for explicit consent before collecting health information."
                    ),
                }
            ],
            "functions": [record_consent],
        }

    def intake_node() -> NodeConfig:
        return {
            "name": "structured_intake",
            "task_messages": [
                {
                    "role": "developer",
                    "content": (
                        "Collect only chief concern, symptoms, medications, allergies, and whether "
                        "emergency warning signs are present. Never diagnose."
                    ),
                }
            ],
            "functions": [save_intake],
        }

    def finish_node(message: str) -> NodeConfig:
        return {
            "name": "finish",
            "task_messages": [{"role": "developer", "content": message}],
            "functions": [],
        }

    return consent_node()
