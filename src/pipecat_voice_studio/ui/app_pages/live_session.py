"""Live voice session launcher."""

import httpx
import streamlit as st

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.ui.components import render_voice_session
from pipecat_voice_studio.ui.store import studio_store

settings = get_settings()
graphs = [graph for graph in studio_store().list_graphs() if graph["mode"] != "eval"]
selected = st.selectbox(
    "Active pipeline",
    graphs,
    format_func=lambda item: item["name"],
    key="live_pipeline",
    persist_state="page",
)

st.subheader("Browser voice")
status_url = f"{settings.pvs_bot_base_url.rstrip('/')}/status"
try:
    response = httpx.get(status_url, timeout=1)
    response.raise_for_status()
    worker_ready = response.json().get("status") == "ready"
except (httpx.HTTPError, ValueError):
    worker_ready = False

if worker_ready:
    st.success("Pipecat worker is ready.", icon=":material/check_circle:")
else:
    st.warning("The separate Pipecat worker is not reachable.", icon=":material/warning:")
    st.code(
        "uv run python -m pipecat_voice_studio.voice.bot --host 127.0.0.1 "
        "--port 7860 --allowed-origins http://localhost:8501 http://127.0.0.1:8501",
        language="powershell",
    )

render_voice_session(
    bot_base_url=settings.pvs_bot_base_url,
    pipeline_id=selected["id"],
    pipeline_name=selected["name"],
    mode=selected["mode"],
    key=f"voice-{selected['id']}",
)
st.caption(
    "Audio remains in the live WebRTC stream and is never written to the studio database."
)
