"""Shared Streamlit data access."""

import streamlit as st

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.storage import StudioStore


@st.cache_resource
def studio_store() -> StudioStore:
    """Return the initialized process-local store."""
    store = StudioStore(get_settings().pvs_database_path)
    store.initialize()
    return store
