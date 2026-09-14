"""Shared Streamlit data access.

Provides a singleton `StudioStore` connection pool across Streamlit script
reruns and browser sessions via `@st.cache_resource`. Next module to read:
`storage.py` for database operations.
"""

import streamlit as st

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.storage import StudioStore


@st.cache_resource
def studio_store() -> StudioStore:
    """Return the initialized process-local store singleton."""
    store = StudioStore(get_settings().pvs_database_path)
    store.initialize()
    return store
