import { PipecatClient, type PipecatMetricsData, type TransportState } from "@pipecat-ai/client-js";
import { PipecatClientAudio, PipecatClientProvider } from "@pipecat-ai/client-react";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useState } from "react";

type GraphData = {
  view: "graph";
  graph: {
    name: string;
    mode: string;
    nodes: Array<{ id: string; kind: string; label: string }>;
    edges: Array<{ source: string; target: string }>;
  };
};

type VoiceData = {
  view: "voice";
  botBaseUrl: string;
  pipelineId: string;
  pipelineName: string;
  mode: string;
};

export type StudioData = GraphData | VoiceData;

type TranscriptItem = {
  id: number;
  role: "user" | "assistant";
  text: string;
};

function GraphView({ data }: { data: GraphData }) {
  const nodes: Node[] = data.graph.nodes.map((node, index) => ({
    id: node.id,
    position: { x: (index % 4) * 235, y: Math.floor(index / 4) * 150 },
    data: {
      label: (
        <>
          <small>{node.kind}</small>
          <strong>{node.label}</strong>
        </>
      ),
    },
    className: ["timeline", "metrics", "persistence"].includes(node.kind)
      ? "locked"
      : "",
  }));
  const edges: Edge[] = data.graph.edges.map((edge, index) => ({
    id: `edge-${index}`,
    source: edge.source,
    target: edge.target,
    animated: true,
  }));

  return (
    <section className="graph-shell">
      <header className="studio-header">
        <span className="badge">{data.graph.mode}</span>
        <h3>{data.graph.name}</h3>
      </header>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <MiniMap pannable zoomable />
        <Controls />
        <Background gap={18} />
      </ReactFlow>
    </section>
  );
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function VoiceView({ data }: { data: VoiceData }) {
  const [transportState, setTransportState] = useState<TransportState>("disconnected");
  const [mics, setMics] = useState<MediaDeviceInfo[]>([]);
  const [selectedMic, setSelectedMic] = useState("");
  const [micEnabled, setMicEnabled] = useState(true);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [botSpeaking, setBotSpeaking] = useState(false);
  const [partialTranscript, setPartialTranscript] = useState("");
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [metrics, setMetrics] = useState<PipecatMetricsData>({});
  const [toolStatus, setToolStatus] = useState("");
  const [error, setError] = useState("");

  const appendTranscript = useCallback((role: TranscriptItem["role"], text: string) => {
    const clean = text.trim();
    if (!clean) return;
    setTranscript((items) => [
      ...items.slice(-199),
      { id: Date.now() + Math.random(), role, text: clean },
    ]);
  }, []);

  const client = useMemo(
    () =>
      new PipecatClient({
        transport: new SmallWebRTCTransport(),
        enableMic: true,
        enableCam: false,
        callbacks: {
          onTransportStateChanged: setTransportState,
          onAvailableMicsUpdated: setMics,
          onMicUpdated: (mic) => setSelectedMic(mic.deviceId),
          onUserStartedSpeaking: () => setUserSpeaking(true),
          onUserStoppedSpeaking: () => setUserSpeaking(false),
          onBotStartedSpeaking: () => setBotSpeaking(true),
          onBotStoppedSpeaking: () => setBotSpeaking(false),
          onUserTranscript: (event) => {
            if (event.final) {
              appendTranscript("user", event.text);
              setPartialTranscript("");
            } else {
              setPartialTranscript(event.text);
            }
          },
          onBotOutput: (event) => appendTranscript("assistant", event.text),
          onMetrics: setMetrics,
          onLLMFunctionCallStarted: (event) =>
            setToolStatus(`Starting ${event.function_name ?? "tool"}`),
          onLLMFunctionCallInProgress: (event) =>
            setToolStatus(`Running ${event.function_name ?? "tool"}`),
          onLLMFunctionCallStopped: (event) =>
            setToolStatus(`${event.cancelled ? "Cancelled" : "Completed"} ${event.function_name ?? "tool"}`),
          onDeviceError: (event) => setError(errorMessage(event)),
          onError: (event) => setError(errorMessage(event.data ?? event)),
        },
      }),
    [appendTranscript],
  );

  useEffect(() => {
    return () => {
      void client.disconnect();
    };
  }, [client]);

  const connected = ["connected", "ready"].includes(transportState);
  const busy = ["initializing", "authenticating", "connecting", "disconnecting"].includes(
    transportState,
  );

  const connect = async () => {
    setError("");
    if (window.location.protocol === "https:" && data.botBaseUrl.startsWith("http:")) {
      setError("HTTPS Streamlit pages require an HTTPS Pipecat worker URL.");
      return;
    }
    if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
      setError("Microphone access requires HTTPS or localhost.");
      return;
    }
    try {
      await client.initDevices();
      setMics(await client.getAllMics());
      const current = client.selectedMic;
      if ("deviceId" in current) setSelectedMic(current.deviceId);
      await client.startBotAndConnect({
        endpoint: `${data.botBaseUrl.replace(/\/$/, "")}/start`,
        requestData: {
          transport: "webrtc",
          enableDefaultIceServers: true,
          body: { pipeline_id: data.pipelineId },
        },
      });
    } catch (caught) {
      setError(errorMessage(caught));
      await client.disconnect();
    }
  };

  const disconnect = async () => {
    setError("");
    await client.disconnect();
  };

  const toggleMic = () => {
    const enabled = !micEnabled;
    client.enableMic(enabled);
    setMicEnabled(enabled);
  };

  const updateMic = (deviceId: string) => {
    client.updateMic(deviceId);
    setSelectedMic(deviceId);
  };

  const metricRows = [
    ...(metrics.ttfb ?? []).map((metric) => ({ kind: "TTFB", ...metric })),
    ...(metrics.processing ?? []).map((metric) => ({ kind: "Processing", ...metric })),
  ].slice(-4);

  return (
    <PipecatClientProvider client={client}>
      <PipecatClientAudio />
      <section className="voice-shell">
        <header className="studio-header">
          <div>
            <span className="badge">{data.mode}</span>
            <h3>{data.pipelineName}</h3>
          </div>
          <span className={`connection-state state-${transportState}`}>{transportState}</span>
        </header>

        <div className="voice-controls" role="group" aria-label="Voice session controls">
          <button type="button" className="primary" onClick={() => void connect()} disabled={connected || busy}>
            Connect
          </button>
          <button type="button" onClick={() => void disconnect()} disabled={!connected || busy}>
            Disconnect
          </button>
          <button
            type="button"
            className={`mic-toggle ${micEnabled ? "mic-on" : "mic-off"}`}
            onClick={toggleMic}
            disabled={!connected}
            aria-pressed={micEnabled}
            aria-label={micEnabled ? "Turn microphone off" : "Turn microphone on"}
            title={micEnabled ? "Turn microphone off" : "Turn microphone on"}
          >
            <span aria-hidden="true">{micEnabled ? "🎙" : "🔇"}</span>
            {micEnabled ? "Mic on" : "Mic off"}
          </button>
          <label>
            Microphone
            <select value={selectedMic} onChange={(event) => updateMic(event.target.value)} disabled={!mics.length}>
              {!mics.length && <option value="">Available after permission</option>}
              {mics.map((mic, index) => (
                <option key={mic.deviceId} value={mic.deviceId}>
                  {mic.label || `Microphone ${index + 1}`}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && <div className="error" role="alert">{error}</div>}

        <div className="voice-grid">
          <div className="conversation" aria-live="polite">
            <div className="section-heading">
              <h4>Conversation</h4>
              <div className="speaking-status">
                <span className={userSpeaking ? "active" : ""}>You</span>
                <span className={botSpeaking ? "active" : ""}>Assistant</span>
              </div>
            </div>
            <div className="transcript">
              {!transcript.length && !partialTranscript && (
                <p className="empty">Connect and speak to begin.</p>
              )}
              {transcript.map((item) => (
                <div key={item.id} className={`message ${item.role}`}>
                  <strong>{item.role === "user" ? "You" : "Assistant"}</strong>
                  <p>{item.text}</p>
                </div>
              ))}
              {partialTranscript && (
                <div className="message user partial">
                  <strong>You</strong>
                  <p>{partialTranscript}</p>
                </div>
              )}
            </div>
          </div>

          <aside className="telemetry">
            <h4>Live signals</h4>
            <dl>
              <div><dt>Tool</dt><dd>{toolStatus || "Idle"}</dd></div>
              <div><dt>Microphone</dt><dd>{micEnabled ? "Enabled" : "Muted"}</dd></div>
              {metricRows.map((metric) => (
                <div key={`${metric.kind}-${metric.processor}`}>
                  <dt>{metric.kind}</dt>
                  <dd>{metric.processor}: {metric.value.toFixed(3)}</dd>
                </div>
              ))}
            </dl>
          </aside>
        </div>
      </section>
    </PipecatClientProvider>
  );
}

export default function StudioComponent({ data }: { data: StudioData }) {
  return data.view === "voice" ? <VoiceView data={data} /> : <GraphView data={data} />;
}
