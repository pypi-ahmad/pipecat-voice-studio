"""Session, appointment, telephone, and healthcare audit records page.

Presents multi-tab operator ledgers for:
1. Conversation sessions and completed dialogue turns
2. Scheduled appointments and external calendar sync states
3. Carrier telephone calls (with redacted numbers) and warm transfer handoffs
4. Healthcare consent status and escalation metadata (never exposing encrypted intake)
Next module to read: `storage.py` for database schemas and cascading delete behaviors.
"""

import streamlit as st

from pipecat_voice_studio.ui.store import studio_store

store = studio_store()
sessions_tab, appointments_tab, calls_tab, health_tab = st.tabs(
    ["Sessions", "Appointments", "Calls and handoffs", "Healthcare metadata"]
)

with sessions_tab:
    with store.connect() as connection:
        sessions = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            ).fetchall()
        ]
    if not sessions:
        st.info("No voice sessions have been recorded yet.")
    for session in sessions:
        with st.expander(f"{session['status']} · {session['started_at']}"):
            events = store.list_events(session["id"])
            for event in events:
                if event["event_type"] == "turn.final":
                    st.chat_message(event["payload"].get("role", "assistant")).write(
                        event["payload"].get("text", "")
                    )
            if st.button("Delete session", key=f"delete-{session['id']}"):
                store.delete_session(session["id"])
                st.rerun()
with appointments_tab:
    with store.connect() as connection:
        appointments = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM appointments ORDER BY starts_at"
            ).fetchall()
        ]
    st.dataframe(appointments, width="stretch", hide_index=True)
with calls_tab:
    st.caption("Telephone numbers are redacted; full numbers are never stored.")
    st.dataframe(store.list_calls(), width="stretch", hide_index=True)
    st.subheader("Human handoffs")
    st.dataframe(store.list_handoffs(), width="stretch", hide_index=True)
with health_tab:
    st.caption(
        "Only consent, state, and escalation metadata is shown. "
        "Structured intake remains encrypted."
    )
    st.dataframe(store.list_healthcare_metadata(), width="stretch", hide_index=True)
