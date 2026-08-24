import React from "react";
import { createRoot } from "react-dom/client";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { FrontendRenderer } from "@streamlit/component-v2-lib";
import "./style.css";

type StudioData = {
  graph: {
    name: string;
    mode: string;
    nodes: Array<{ id: string; kind: string; label: string }>;
    edges: Array<{ source: string; target: string }>;
  };
};

function Graph({ data }: { data: StudioData }) {
  const nodes: Node[] = data.graph.nodes.map((node, index) => ({
    id: node.id,
    position: { x: (index % 4) * 235, y: Math.floor(index / 4) * 150 },
    data: { label: <><small>{node.kind}</small><strong>{node.label}</strong></> },
    className: node.kind === "timeline" || node.kind === "metrics" || node.kind === "persistence" ? "locked" : "",
  }));
  const edges: Edge[] = data.graph.edges.map((edge, index) => ({
    id: `edge-${index}`,
    source: edge.source,
    target: edge.target,
    animated: true,
  }));
  return <div className="shell">
    <header><span>{data.graph.mode}</span><h3>{data.graph.name}</h3></header>
    <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={true}>
      <MiniMap pannable zoomable />
      <Controls />
      <Background gap={18} />
    </ReactFlow>
  </div>;
}

const StudioGraph: FrontendRenderer<Record<string, unknown>, StudioData> = ({ data, parentElement }) => {
  const mount = parentElement.querySelector("#root");
  if (!(mount instanceof HTMLElement)) throw new Error("Component mount was not found");
  const root = createRoot(mount);
  root.render(<Graph data={data} />);
  return () => root.unmount();
};

export default StudioGraph;
