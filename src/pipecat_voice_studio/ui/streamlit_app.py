"""Streamlit application entry point and multi-page router.

Configures the top-level page layout, mounts navigation across the 7 operator
dashboards (Command center, Agent studio, Live session, Integrations, Records,
Evaluations, Analytics), and renders contextual operator guides for each page.
Next module to read: individual page files in `ui/app_pages/`.
"""

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Pipecat Voice Studio", page_icon=":material/graphic_eq:")


PAGE_GUIDES = {
    "Command center": """
Check that Python, Pipecat, Streamlit, and Torch report versions. **CUDA ready** means GPU
acceleration is available; **CPU mode ready** is also valid. Start here when diagnosing setup or
hardware problems.
""",
    "Agent studio": """
1. Select a saved pipeline to inspect its processing graph.
2. Open **Safe configuration** to clone it with a new name, system prompt, or voice.
3. Choose **Validate and save clone**. The original pipeline is not changed.
""",
    "Live session": """
1. Select a browser pipeline: realtime, appointment, Google Calendar, Simli avatar, or healthcare.
2. Confirm the worker shows as ready, then choose **Connect** and allow microphone access.
3. Use **Mic on / Mic off** during the call and **Disconnect** when finished. Raw audio is not
   stored. Healthcare pipelines also suppress conversation transcript persistence.
""",
    "Records": """
Use **Sessions** to review final conversation turns or delete a session. Use **Appointments** to
review bookings and external status. **Calls and handoffs** contains redacted telephone state;
**Healthcare metadata** never decrypts intake. Deleting a session removes its timeline but keeps
its appointment record.
""",
    "Evaluations": """
1. Select an evaluation pipeline and an allowlisted scenario.
2. Read the scenario expectation, then choose **Run evaluation**.
3. Review the result, diagnostics, and recent runs. Evaluations may call paid models but do not
   retain audio.
""",
    "Analytics": """
Review aggregate session, completion, and appointment counts. **Tool outcomes** summarizes persisted
tool lifecycle events; run voice sessions or evaluations first if this page is empty.
""",
    "Integrations": """
1. Configure provider environment variables and restart the launcher.
2. Bind Twilio or Vonage to the business telephone pipeline.
3. Add exact E.164 destinations to `PVS_OUTBOUND_ALLOWLIST`, then explicitly confirm each
   outbound call.
Readiness also covers Google Calendar, HubSpot, Simli, and healthcare. Provider credentials are
never displayed or stored in SQLite.
""",
}

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
            page_directory / "integrations.py",
            title="Integrations",
            icon=":material/extension:",
        ),
        st.Page(
            page_directory / "records.py",
            title="Records",
            icon=":material/folder_open:",
        ),
        st.Page(
            page_directory / "evaluations.py",
            title="Evaluations",
            icon=":material/science:",
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
with st.expander(":material/help: How to use this page", expanded=True):
    st.markdown(PAGE_GUIDES[page.title])
page.run()
