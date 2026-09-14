"""Built-in editable pipeline definitions.

Constructs the seven starter `PipelineGraph`s that `storage.StudioStore.initialize`
inserts for any name not already present, so a fresh or upgraded database always
has the full built-in set. Every node kind and config key used here must already
be allowlisted in `graph.py`; this module only assembles graphs, it does not
relax what `PipelineGraph`/`GraphNode` will accept.
"""

from itertools import pairwise

from pipecat_voice_studio.graph import GraphEdge, GraphNode, NodeKind, PipelineGraph, PipelineMode


def _operational_nodes() -> list[GraphNode]:
    # Every graph mode requires these three kinds (see graph.py's OPERATIONAL_KINDS);
    # they are appended to every starter graph below rather than made optional.
    return [
        GraphNode(id="timeline", kind=NodeKind.TIMELINE, label="Semantic timeline"),
        GraphNode(id="metrics", kind=NodeKind.METRICS, label="Metrics"),
        GraphNode(id="persistence", kind=NodeKind.PERSISTENCE, label="Persistence"),
    ]


def seed_graphs() -> list[PipelineGraph]:
    """Return fresh copies of all supported starter graphs."""
    realtime_nodes = [
        GraphNode(id="transport", kind=NodeKind.WEBRTC, label="Browser WebRTC"),
        GraphNode(id="context", kind=NodeKind.CONTEXT, label="Conversation context"),
        GraphNode(
            id="realtime",
            kind=NodeKind.REALTIME,
            label="OpenAI Realtime",
            config={
                "prompt": "Be concise, helpful, and explicit before taking actions.",
                "voice": "marin",
                "language": "en",
                "vad_eagerness": "auto",
            },
        ),
        *_operational_nodes(),
    ]
    cascade_nodes = [
        GraphNode(id="transport", kind=NodeKind.WEBRTC, label="Browser WebRTC"),
        GraphNode(id="stt", kind=NodeKind.STT, label="Streaming speech recognition"),
        GraphNode(id="turn", kind=NodeKind.TURN, label="Silero turn handling"),
        GraphNode(id="context", kind=NodeKind.CONTEXT, label="Conversation context"),
        GraphNode(id="llm", kind=NodeKind.LLM, label="OpenAI Responses"),
        GraphNode(id="policy", kind=NodeKind.POLICY, label="Appointment policy"),
        GraphNode(id="flow", kind=NodeKind.APPOINTMENT, label="Appointment Flow"),
        GraphNode(id="tts", kind=NodeKind.TTS, label="OpenAI speech", config={"voice": "marin"}),
        *_operational_nodes(),
    ]
    eval_nodes = [node.model_copy(deep=True) for node in cascade_nodes]
    eval_nodes[0] = GraphNode(id="transport", kind=NodeKind.EVAL_TRANSPORT, label="Eval transport")
    graphs = [
        PipelineGraph(
            name="Realtime assistant",
            mode=PipelineMode.REALTIME,
            nodes=realtime_nodes,
            edges=[
                GraphEdge(source="transport", target="context"),
                GraphEdge(source="context", target="realtime"),
            ],
        ),
        PipelineGraph(
            name="Cascaded appointment assistant",
            mode=PipelineMode.CASCADE,
            nodes=cascade_nodes,
            edges=[
                GraphEdge(source="transport", target="stt"),
                GraphEdge(source="stt", target="turn"),
                GraphEdge(source="turn", target="context"),
                GraphEdge(source="context", target="llm"),
                GraphEdge(source="llm", target="policy"),
                GraphEdge(source="policy", target="flow"),
                GraphEdge(source="flow", target="tts"),
            ],
        ),
        PipelineGraph(
            name="Appointment evaluation",
            mode=PipelineMode.EVAL,
            nodes=eval_nodes,
            edges=[
                GraphEdge(source="transport", target="stt"),
                GraphEdge(source="stt", target="turn"),
                GraphEdge(source="turn", target="context"),
                GraphEdge(source="context", target="llm"),
                GraphEdge(source="llm", target="policy"),
                GraphEdge(source="policy", target="flow"),
                GraphEdge(source="flow", target="tts"),
            ],
        ),
    ]
    extension_specs = [
        (
            "Business phone agent",
            NodeKind.TELEPHONY,
            [NodeKind.MULTI_AGENT, NodeKind.CRM, NodeKind.HANDOFF],
            "Route callers across billing, technical support, sales, and human escalation.",
        ),
        (
            "Google Calendar appointment assistant",
            NodeKind.WEBRTC,
            [NodeKind.POLICY, NodeKind.APPOINTMENT, NodeKind.CALENDAR],
            "Book confirmed appointments against the synchronized organization calendar.",
        ),
        (
            "Simli avatar assistant",
            NodeKind.WEBRTC,
            [NodeKind.AVATAR],
            "Be a concise on-screen avatar assistant.",
        ),
        (
            "Healthcare intake assistant",
            NodeKind.WEBRTC,
            [NodeKind.HEALTHCARE, NodeKind.POLICY],
            "Collect consent-first structured intake. Never diagnose or provide medical advice.",
        ),
    ]
    for name, transport_kind, tools, prompt in extension_specs:
        # pairwise(path) below wires each node to the next in list order, so `path`
        # must already be in the exact execution order the compiled pipeline needs.
        path = [
            GraphNode(id="transport", kind=transport_kind, label="Voice transport"),
            GraphNode(id="stt", kind=NodeKind.STT, label="Streaming speech recognition"),
            GraphNode(id="turn", kind=NodeKind.TURN, label="Silero turn handling"),
            GraphNode(id="context", kind=NodeKind.CONTEXT, label="Conversation context"),
            GraphNode(
                id="llm",
                kind=NodeKind.LLM,
                label="OpenAI Responses",
                config={"prompt": prompt},
            ),
            *[
                GraphNode(
                    id=f"feature-{index}", kind=kind, label=kind.value.replace("_", " ").title()
                )
                for index, kind in enumerate(tools)
            ],
            GraphNode(
                id="tts",
                kind=NodeKind.TTS,
                label="OpenAI speech",
                config={"voice": "marin"},
            ),
        ]
        graphs.append(
            PipelineGraph(
                name=name,
                mode=PipelineMode.CASCADE,
                nodes=[*path, *_operational_nodes()],
                edges=[
                    GraphEdge(source=source.id, target=target.id)
                    for source, target in pairwise(path)
                ],
            )
        )
    return graphs
