"""Built-in editable pipeline definitions."""

from pipecat_voice_studio.graph import GraphEdge, GraphNode, NodeKind, PipelineGraph, PipelineMode


def _operational_nodes() -> list[GraphNode]:
    return [
        GraphNode(id="timeline", kind=NodeKind.TIMELINE, label="Semantic timeline"),
        GraphNode(id="metrics", kind=NodeKind.METRICS, label="Metrics"),
        GraphNode(id="persistence", kind=NodeKind.PERSISTENCE, label="Persistence"),
    ]


def seed_graphs() -> list[PipelineGraph]:
    """Return fresh copies of the three starter graphs."""
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
    return [
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
