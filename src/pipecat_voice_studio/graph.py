"""Closed, validated pipeline graph contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PipelineMode(StrEnum):
    """Supported execution modes."""

    REALTIME = "realtime"
    CASCADE = "cascade"
    EVAL = "eval"


class NodeKind(StrEnum):
    """Audited node implementations available to saved graphs."""

    WEBRTC = "small_webrtc"
    TELEPHONY = "telephony_websocket"
    EVAL_TRANSPORT = "eval_transport"
    REALTIME = "openai_realtime"
    STT = "openai_realtime_stt"
    CONTEXT = "context"
    TURN = "silero_turn"
    LLM = "openai_responses"
    TTS = "openai_tts"
    APPOINTMENT = "appointment_flow"
    CALENDAR = "google_calendar"
    CRM = "hubspot_crm"
    HANDOFF = "human_handoff"
    MULTI_AGENT = "multi_agent_router"
    HEALTHCARE = "healthcare_intake"
    AVATAR = "simli_avatar"
    POLICY = "policy_gate"
    TIMELINE = "timeline"
    METRICS = "metrics"
    PERSISTENCE = "persistence"


PATH_KINDS = {
    NodeKind.WEBRTC,
    NodeKind.TELEPHONY,
    NodeKind.EVAL_TRANSPORT,
    NodeKind.REALTIME,
    NodeKind.STT,
    NodeKind.CONTEXT,
    NodeKind.TURN,
    NodeKind.LLM,
    NodeKind.TTS,
    NodeKind.APPOINTMENT,
    NodeKind.CALENDAR,
    NodeKind.CRM,
    NodeKind.HANDOFF,
    NodeKind.MULTI_AGENT,
    NodeKind.HEALTHCARE,
    NodeKind.AVATAR,
    NodeKind.POLICY,
}
OPERATIONAL_KINDS = {NodeKind.TIMELINE, NodeKind.METRICS, NodeKind.PERSISTENCE}
ALLOWED_CONFIG = {"prompt", "voice", "speed", "language", "vad_eagerness"}


class GraphNode(BaseModel):
    """A graph node with an allowlisted implementation and safe configuration."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    kind: NodeKind
    label: str = Field(min_length=1, max_length=80)
    config: dict[str, str | float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_config(self) -> GraphNode:
        unknown = set(self.config) - ALLOWED_CONFIG
        if unknown:
            msg = f"Unsupported node configuration: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        return self


class GraphEdge(BaseModel):
    """A directed frame-path connection."""

    model_config = ConfigDict(extra="forbid")

    source: str
    target: str


class PipelineGraph(BaseModel):
    """Serializable pipeline definition accepted by the compiler."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    mode: PipelineMode
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @model_validator(mode="after")
    def validate_topology(self) -> PipelineGraph:
        by_id = {node.id: node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise ValueError("Node IDs must be unique")
        for edge in self.edges:
            if edge.source not in by_id or edge.target not in by_id:
                raise ValueError("Every edge must reference existing nodes")
            if edge.source == edge.target:
                raise ValueError("Self-referencing edges are not allowed")

        kinds = {node.kind for node in self.nodes}
        required_ops = OPERATIONAL_KINDS - kinds
        if required_ops:
            raise ValueError("Timeline, metrics, and persistence nodes are mandatory")

        if self.mode == PipelineMode.EVAL:
            transport = NodeKind.EVAL_TRANSPORT
            if NodeKind.EVAL_TRANSPORT not in kinds:
                raise ValueError("Evaluation graphs require the evaluation transport")
        else:
            transport = next(
                (kind for kind in (NodeKind.WEBRTC, NodeKind.TELEPHONY) if kind in kinds),
                None,
            )
        if (
            transport is None
            or sum(
                node.kind in {NodeKind.WEBRTC, NodeKind.TELEPHONY, NodeKind.EVAL_TRANSPORT}
                for node in self.nodes
            )
            != 1
        ):
            raise ValueError("The graph must contain exactly one transport for its mode")

        if self.mode == PipelineMode.REALTIME:
            if NodeKind.REALTIME not in kinds or kinds & {
                NodeKind.STT,
                NodeKind.TURN,
                NodeKind.LLM,
                NodeKind.TTS,
                NodeKind.APPOINTMENT,
                NodeKind.CALENDAR,
                NodeKind.CRM,
                NodeKind.HANDOFF,
                NodeKind.MULTI_AGENT,
                NodeKind.HEALTHCARE,
                NodeKind.AVATAR,
            }:
                raise ValueError("Realtime graphs require the combined realtime service only")
        else:
            required = {NodeKind.STT, NodeKind.CONTEXT, NodeKind.TURN, NodeKind.LLM, NodeKind.TTS}
            if NodeKind.REALTIME in kinds or not required <= kinds:
                raise ValueError("Cascade and eval graphs require the complete cascaded stack")
        if transport == NodeKind.TELEPHONY and self.mode != PipelineMode.CASCADE:
            raise ValueError("Telephony graphs require cascade mode")
        if NodeKind.AVATAR in kinds and (
            transport != NodeKind.WEBRTC or self.mode != PipelineMode.CASCADE
        ):
            raise ValueError("Avatar graphs require browser cascade mode")
        if NodeKind.HEALTHCARE in kinds and kinds & {
            NodeKind.CRM,
            NodeKind.CALENDAR,
            NodeKind.APPOINTMENT,
            NodeKind.MULTI_AGENT,
        }:
            raise ValueError("Healthcare graphs must remain isolated from business tools")

        path_ids = {node.id for node in self.nodes if node.kind in PATH_KINDS}
        path_edges = [
            (edge.source, edge.target)
            for edge in self.edges
            if edge.source in path_ids and edge.target in path_ids
        ]
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in path_ids}
        indegree = dict.fromkeys(path_ids, 0)
        for source, target in path_edges:
            adjacency[source].append(target)
            indegree[target] += 1
        queue = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited: list[str] = []
        while queue:
            current = queue.pop()
            visited.append(current)
            for target in adjacency[current]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        if len(visited) != len(path_ids):
            raise ValueError("The frame path must be acyclic")
        if path_ids and set(visited) != path_ids:
            raise ValueError("The frame path must be connected")
        undirected: dict[str, set[str]] = {node_id: set() for node_id in path_ids}
        for source, target in path_edges:
            undirected[source].add(target)
            undirected[target].add(source)
        reached: set[str] = set()
        stack = [next(iter(path_ids))]
        while stack:
            current = stack.pop()
            if current not in reached:
                reached.add(current)
                stack.extend(undirected[current] - reached)
        if reached != path_ids:
            raise ValueError("The frame path must be connected")
        return self


class CompiledPipeline(BaseModel):
    """Safe runtime recipe produced from a validated graph."""

    mode: PipelineMode
    ordered_nodes: list[NodeKind]
    settings: dict[str, Any]
    transport: Literal["webrtc", "telephony", "eval"]


def compile_graph(graph: PipelineGraph) -> CompiledPipeline:
    """Compile a validated graph into a deterministic runtime recipe."""
    path_nodes = {node.id: node for node in graph.nodes if node.kind in PATH_KINDS}
    targets = {
        edge.target
        for edge in graph.edges
        if edge.source in path_nodes and edge.target in path_nodes
    }
    current = next(node_id for node_id in path_nodes if node_id not in targets)
    ordered: list[NodeKind] = []
    while True:
        ordered.append(path_nodes[current].kind)
        outgoing = [
            edge.target
            for edge in graph.edges
            if edge.source == current and edge.target in path_nodes
        ]
        if not outgoing:
            break
        if len(outgoing) != 1:
            raise ValueError("The executable frame path cannot branch")
        current = outgoing[0]
    if len(ordered) != len(path_nodes):
        raise ValueError("The executable frame path must be a single chain")
    settings = {key: value for node in graph.nodes for key, value in node.config.items()}
    return CompiledPipeline(
        mode=graph.mode,
        ordered_nodes=ordered,
        settings=settings,
        transport=(
            "eval"
            if graph.mode == PipelineMode.EVAL
            else "telephony"
            if any(node.kind == NodeKind.TELEPHONY for node in graph.nodes)
            else "webrtc"
        ),
    )
