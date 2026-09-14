"""Streamlit Components v2 wrappers for the React visual graph and WebRTC client.

Bridges Python data dictionaries into the custom React frontend bundle
(`frontend/src/StudioComponent.tsx`), hosting either the interactive React Flow
pipeline visualizer or the browser-side SmallWebRTC microphone/audio interface.
Audio streaming is executed client-side in the browser, not inside the Streamlit
process. Next module to read: `ui/frontend/src/StudioComponent.tsx` for the React
implementation.
"""

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
    has_avatar: bool,
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
            "hasAvatar": has_avatar,
        },
        height=720,
        key=key,
    )
