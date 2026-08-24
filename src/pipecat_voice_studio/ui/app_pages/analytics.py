"""Operational analytics derived from semantic events."""

import streamlit as st

from pipecat_voice_studio.ui.store import studio_store

with studio_store().connect() as connection:
    session_count = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    completed = connection.execute(
        "SELECT COUNT(*) FROM sessions WHERE status = 'completed'"
    ).fetchone()[0]
    appointments = connection.execute(
        "SELECT COUNT(*) FROM appointments WHERE status = 'confirmed'"
    ).fetchone()[0]
    tool_events = connection.execute(
        "SELECT event_type, COUNT(*) AS count FROM session_events "
        "WHERE event_type LIKE 'tool.%' GROUP BY event_type"
    ).fetchall()

first, second, third = st.columns(3)
first.metric("Sessions", session_count)
second.metric("Completion", f"{completed / session_count:.0%}" if session_count else "—")
third.metric("Appointments", appointments)
st.subheader("Tool outcomes")
st.dataframe([dict(row) for row in tool_events], hide_index=True, width="stretch")
