"""Pipecat behavioral evaluation runner."""

import streamlit as st

from pipecat_voice_studio.config import get_settings
from pipecat_voice_studio.evaluations import SCENARIOS, run_evaluation
from pipecat_voice_studio.ui.store import studio_store

store = studio_store()
settings = get_settings()
graphs = [graph for graph in store.list_graphs() if graph["mode"] == "eval"]

st.subheader("Behavioral evaluations")
selected = st.selectbox(
    "Evaluation pipeline",
    graphs,
    format_func=lambda item: item["name"],
    key="evaluation_pipeline",
    persist_state="page",
)
scenario_name = st.selectbox(
    "Scenario",
    list(SCENARIOS),
    format_func=lambda value: value.replace("-", " ").title(),
    key="evaluation_scenario",
    persist_state="page",
)
st.info(SCENARIOS[scenario_name].description)
st.caption(
    "Each run uses a disposable database and worker process. It may call configured "
    "OpenAI models, but generated or streamed audio is never retained."
)

can_run = settings.openai_api_key is not None
if not can_run:
    st.warning("Set OPENAI_API_KEY before running paid evaluations.")

if st.button(
    "Run evaluation",
    type="primary",
    icon=":material/play_arrow:",
    disabled=not can_run,
):
    with st.status("Running isolated Pipecat evaluation…", expanded=True) as status:
        result = run_evaluation(store, selected["id"], scenario_name)
        st.session_state["last_eval_result"] = result
        if result["passed"]:
            status.update(label="Evaluation passed", state="complete", expanded=False)
        else:
            status.update(label="Evaluation failed", state="error", expanded=True)

result = st.session_state.get("last_eval_result")
if result:
    if result["passed"]:
        st.success(f"{result['scenario']} passed in {result.get('duration_ms', 0)} ms.")
    else:
        st.error("\n".join(result.get("failures", ["Evaluation failed."])))
    with st.expander("Latest evaluation diagnostics"):
        st.json(result)

st.subheader("Recent runs")
runs = store.list_eval_runs()
if not runs:
    st.info("No evaluations have run yet.")
for run in runs:
    icon = ":material/check_circle:" if run["status"] == "passed" else ":material/error:"
    with st.expander(
        f"{icon} {run['scenario']} · {run['status']} · {run['created_at']}",
    ):
        st.json(run["result"])
