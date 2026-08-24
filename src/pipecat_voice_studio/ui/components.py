"""Streamlit Components v2 wrappers."""

import streamlit as st

studio_graph = st.components.v2.component(
    "pipecat-voice-studio.studio_graph",
    html="<div id='root'></div>",
    js="assets/index-*.js",
    css="assets/index-*.css",
    isolate_styles=True,
)
