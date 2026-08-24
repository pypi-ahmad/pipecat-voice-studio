"""External provider setup and telephone operations."""

from __future__ import annotations

import asyncio

import streamlit as st

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.integrations.readiness import integration_readiness
from pipecat_voice_studio.integrations.telephony import TwilioVoice, VonageVoice
from pipecat_voice_studio.security import digest_phone, redact_phone, require_e164
from pipecat_voice_studio.ui.store import studio_store

settings = get_settings()
store = studio_store()

st.subheader("Provider readiness")
for provider, (ready, required) in integration_readiness(settings).items():
    if ready:
        st.success(f"{provider}: ready", icon=":material/check_circle:")
    else:
        st.warning(f"{provider}: not configured. Required: {required}")

st.subheader("Telephone pipeline bindings")
telephone_graphs = [
    graph
    for graph in store.list_graphs()
    if "telephony_websocket" in store.get_graph(graph["id"]).model_dump_json()
]
if not telephone_graphs:
    st.info("No active telephony pipeline is available.")
else:
    with st.form("telephone-bindings"):
        graph = st.selectbox(
            "Telephone pipeline",
            telephone_graphs,
            format_func=lambda item: item["name"],
        )
        providers = st.multiselect("Bind providers", ["twilio", "vonage"])
        if st.form_submit_button("Save bindings"):
            for provider in providers:
                store.set_integration_binding(provider, graph["id"])
            st.success("Bindings saved.")

st.subheader("Start an outbound call")
st.caption("Only exact E.164 numbers in PVS_OUTBOUND_ALLOWLIST can be called.")
with st.form("outbound-call"):
    provider = st.selectbox("Provider", ["twilio", "vonage"])
    destination = st.text_input("Destination", placeholder="+15551234567")
    confirmed = st.checkbox("I confirm this destination and authorize this call.")
    submitted = st.form_submit_button("Place call", type="primary", disabled=not confirmed)
if submitted:
    try:
        number = require_e164(destination)
        secret_value = (
            settings.twilio_auth_token if provider == "twilio" else settings.vonage_private_key
        )
        if secret_value is None:
            raise RuntimeError("Selected provider is not configured")
        call_id = store.create_call(
            provider=provider,
            direction="outbound",
            remote_last_four=redact_phone(number),
            remote_digest=digest_phone(number, secret_value.get_secret_value()),
        )
        client = TwilioVoice(settings) if provider == "twilio" else VonageVoice(settings)
        provider_call_id = asyncio.run(client.create_call(number))
        store.update_call(call_id, status="initiated", provider_call_id=provider_call_id)
        store.append_audit(
            action="telephone.outbound.created",
            resource_type="call",
            resource_id=call_id,
            outcome="initiated",
            metadata={"provider": provider, "remote_last_four": redact_phone(number)},
        )
        st.success(f"Call initiated. Local call ID: {call_id}")
    except Exception as error:
        if "call_id" in locals():
            store.update_call(call_id, status="failed", failure=type(error).__name__, ended=True)
        st.error(f"Call could not be started: {type(error).__name__}")
