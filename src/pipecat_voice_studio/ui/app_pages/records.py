"""Session and appointment records."""

import streamlit as st

from pipecat_voice_studio.ui.store import studio_store

store = studio_store()
sessions_tab, appointments_tab = st.tabs(["Sessions", "Appointments"])
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
