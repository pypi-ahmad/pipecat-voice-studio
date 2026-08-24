"""Live voice session launcher."""

import streamlit as st

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.ui.store import studio_store

settings = get_settings()
graphs = [graph for graph in studio_store().list_graphs() if graph["mode"] != "eval"]
selected = st.selectbox("Active pipeline", graphs, format_func=lambda item: item["name"])

left, right = st.columns([2, 1])
with left:
    st.subheader("Browser voice")
    st.info(
        "Start the Pipecat worker, then connect using its built-in SmallWebRTC client. "
        "The start payload must include the selected pipeline ID."
    )
    st.code(
        "uv run python -m pipecat_voice_studio.voice.bot --host 127.0.0.1 "
        "--port 7860 --allowed-origins http://localhost:8501 http://127.0.0.1:8501",
        language="powershell",
    )
    st.link_button("Open Pipecat WebRTC client", settings.pvs_bot_base_url, type="primary")
with right:
    st.metric("Mode", selected["mode"])
    st.text_input("Pipeline ID", value=selected["id"], disabled=True)
    st.caption("Audio is streamed and is never written to the studio database.")

st.subheader("Semantic timeline")
st.caption(
    "Final turns, interruptions, flow nodes, tool outcomes, and latency appear during a session."
)
