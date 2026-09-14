"""Command center page for environment, dependency, and GPU diagnostics.

Displays real-time package versions for Python, Pipecat, Streamlit, and PyTorch,
as well as CUDA accelerator availability and GPU device model names.
Next module to read: `diagnostics.py` for diagnostic inspection logic.
"""

import streamlit as st

from pipecat_voice_studio.diagnostics import RuntimeReadiness, runtime_readiness


@st.cache_resource
def get_runtime_readiness() -> RuntimeReadiness:
    """Cache process-level framework and GPU diagnostics."""

    return runtime_readiness()


readiness = get_runtime_readiness()

with st.container(horizontal=True):
    st.metric("Python", readiness["python"])
    st.metric("Pipecat", readiness["pipecat"])
    st.metric("Streamlit", readiness["streamlit"])
    st.metric("Torch", readiness["torch"])

with st.container(border=True):
    if readiness["cuda_available"]:
        st.success(f"CUDA ready: {readiness['gpu']}", icon=":material/check_circle:")
    else:
        st.info("CPU mode ready; CUDA is unavailable.", icon=":material/memory:")
