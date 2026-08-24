"""Deterministic evaluation catalog."""

import streamlit as st

from pipecat_voice_studio.ui.store import studio_store

SCENARIOS = {
    "Happy path": "Collect details, confirm once, then create exactly one appointment.",
    "Unavailable slot": "Reject a collision and offer the next three valid slots.",
    "Policy denial": "Deny creation without an affirmative confirmation turn.",
    "Interruption": "Stop assistant output when the scripted user interrupts.",
    "Synthetic audio smoke": "Transcribe a generated speech fixture without retaining audio.",
}

graphs = [graph for graph in studio_store().list_graphs() if graph["mode"] == "eval"]
st.selectbox("Evaluation pipeline", graphs, format_func=lambda item: item["name"])
scenario = st.selectbox("Scenario", list(SCENARIOS))
st.info(SCENARIOS[scenario])
st.warning(
    "Evaluation execution starts an isolated Pipecat EvalTransport process and may call "
    "configured models. "
    "It is intentionally not triggered automatically."
)
