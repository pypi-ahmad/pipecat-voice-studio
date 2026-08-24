"""Pipeline graph validation and compiler tests."""

import pytest
from pydantic import ValidationError

from pipecat_voice_studio.graph import GraphEdge, PipelineGraph, compile_graph
from pipecat_voice_studio.seeds import seed_graphs


@pytest.mark.parametrize("graph", seed_graphs(), ids=lambda graph: graph.name)
def test_seed_graphs_validate_and_compile(graph: PipelineGraph) -> None:
    compiled = compile_graph(graph)

    assert compiled.mode == graph.mode
    assert compiled.ordered_nodes


def test_graph_rejects_unknown_config() -> None:
    payload = seed_graphs()[0].model_dump()
    payload["nodes"][2]["config"]["base_url"] = "https://untrusted.example"

    with pytest.raises(ValidationError, match="Unsupported node configuration"):
        PipelineGraph.model_validate(payload)


def test_graph_rejects_cycle() -> None:
    graph = seed_graphs()[0]
    payload = graph.model_dump()
    payload["edges"].append(GraphEdge(source="realtime", target="context").model_dump())

    with pytest.raises(ValidationError, match="acyclic"):
        PipelineGraph.model_validate(payload)


def test_compiler_rejects_branches() -> None:
    payload = seed_graphs()[1].model_dump()
    payload["edges"].append(GraphEdge(source="context", target="tts").model_dump())
    graph = PipelineGraph.model_validate(payload)

    with pytest.raises(ValueError, match="cannot branch"):
        compile_graph(graph)
