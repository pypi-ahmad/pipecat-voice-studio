"""Validated visual pipeline studio page.

Renders the interactive React Flow graph for any stored pipeline definition,
and enables safe pipeline cloning where operators can customize system prompts
and voice selections while server-enforced structural invariants remain locked.
Next module to read: `graph.py` for the pipeline graph validation rules.
"""

import streamlit as st

from pipecat_voice_studio.graph import PipelineGraph, compile_graph
from pipecat_voice_studio.ui.components import render_studio_graph
from pipecat_voice_studio.ui.store import studio_store

store = studio_store()
graphs = store.list_graphs()
selected = st.selectbox(
    "Pipeline",
    graphs,
    format_func=lambda item: f"{item['name']} · {item['mode']}",
)
graph = store.get_graph(selected["id"])
render_studio_graph(graph.model_dump(mode="json"), key=selected["id"])

with st.expander("Safe configuration", expanded=True):
    st.caption(
        "Provider, model, transport, timeline, metrics, and persistence are locked server-side."
    )
    prompt_node = next((node for node in graph.nodes if "prompt" in node.config), None)
    voice_node = next((node for node in graph.nodes if "voice" in node.config), None)
    with st.form("clone_pipeline"):
        name = st.text_input("Clone name", value=f"{graph.name} copy")
        prompt = st.text_area(
            "System prompt",
            value=str(prompt_node.config.get("prompt", "")) if prompt_node else "",
        )
        voice = st.selectbox(
            "Voice",
            ["marin", "cedar"],
            index=0 if not voice_node or voice_node.config.get("voice") == "marin" else 1,
        )
        if st.form_submit_button("Validate and save clone", type="primary"):
            payload = graph.model_dump()
            payload["name"] = name
            for node in payload["nodes"]:
                if "prompt" in node["config"]:
                    node["config"]["prompt"] = prompt
                if "voice" in node["config"]:
                    node["config"]["voice"] = voice
            clone = PipelineGraph.model_validate(payload)
            compile_graph(clone)
            store.save_graph(clone, active=True)
            st.success("Validated pipeline clone saved.")
            st.rerun()
