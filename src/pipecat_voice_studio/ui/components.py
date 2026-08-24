"""Streamlit Components v2 wrappers."""

from typing import Any

import streamlit as st

_studio_component = st.components.v2.component(
    "pipecat-voice-studio.studio_graph",
    html='<div class="react-root"></div>',
    js="index-*.js",
    css="index-*.css",
    isolate_styles=True,
)


def render_studio_graph(graph: dict[str, Any], *, key: str) -> None:
    """Render one validated pipeline graph."""
    _studio_component(data={"view": "graph", "graph": graph}, height=590, key=key)


def render_voice_session(
    *,
    bot_base_url: str,
    pipeline_id: str,
    pipeline_name: str,
    mode: str,
    key: str,
) -> None:
    """Render the browser-owned Pipecat WebRTC session UI."""
    _studio_component(
        data={
            "view": "voice",
            "botBaseUrl": bot_base_url,
            "pipelineId": pipeline_id,
            "pipelineName": pipeline_name,
            "mode": mode,
        },
        height=720,
        key=key,
    )
