"""Streamlit application entry point."""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Pipecat Voice Studio", page_icon=":material/graphic_eq:")

page_directory = Path(__file__).parent / "app_pages"
page = st.navigation(
    [
        st.Page(
            page_directory / "command_center.py",
            title="Command center",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            page_directory / "agent_studio.py",
            title="Agent studio",
            icon=":material/smart_toy:",
        ),
        st.Page(
            page_directory / "live_session.py",
            title="Live session",
            icon=":material/mic:",
        ),
        st.Page(
            page_directory / "records.py",
            title="Records",
            icon=":material/folder_open:",
        ),
        st.Page(
            page_directory / "analytics.py",
            title="Analytics",
            icon=":material/analytics:",
        ),
    ],
    position="top",
)

st.title(page.title)
st.caption("Build and operate real-time voice and multimodal agents with Pipecat.")
page.run()
