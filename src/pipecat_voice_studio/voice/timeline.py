"""Semantic Pipecat frame observer; deliberately excludes raw audio.

Intercepts typed frames from the Pipecat pipeline (transcriptions, speech turns,
interruption markers, tool execution milestones, and transport metrics) and
persists them as structured JSON events in SQLite. Must never persist raw audio
frames, and must suppress turn text when conversation persistence is disabled
(e.g., healthcare intake). Next module to read: `storage.py` for how the
resulting `session_events` rows are queried and ordered.
"""

from collections import deque
from typing import TYPE_CHECKING

from pipecat.frames.frames import (
    FunctionCallCancelFrame,
    FunctionCallInProgressFrame,
    FunctionCallResultFrame,
    FunctionCallsStartedFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    MetricsFrame,
    TranscriptionFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed

if TYPE_CHECKING:
    from pipecat_voice_studio.storage import StudioStore


class SemanticTimelineObserver(BaseObserver):
    """Persist bounded semantic conversation events without retaining audio."""

    def __init__(
        self, store: StudioStore, session_id: str, *, persist_conversation: bool = True
    ) -> None:
        super().__init__()
        self.store = store
        self.session_id = session_id
        self.persist_conversation = persist_conversation
        self._seen: set[int] = set()
        # Bounded 500-item sliding window prevents duplicate frame observations
        # while keeping memory strictly bounded during long sessions.
        self._history: deque[int] = deque(maxlen=500)
        self._assistant_text: list[str] = []

    def _mark_seen(self, frame_id: int) -> bool:
        if frame_id in self._seen:
            return False
        self._seen.add(frame_id)
        self._history.append(frame_id)
        if len(self._seen) > len(self._history):
            self._seen = set(self._history)
        return True

    async def on_push_frame(self, data: FramePushed) -> None:
        """Map selected Pipecat frames into bounded semantic events."""
        if not self._mark_seen(data.frame.id):
            return
        if isinstance(data.frame, TranscriptionFrame) and data.frame.finalized:
            if not self.persist_conversation:
                return
            self.store.append_event(
                self.session_id,
                "turn.final",
                {"role": "user", "text": data.frame.text, "language": str(data.frame.language)},
            )
        elif isinstance(data.frame, InterruptionFrame):
            self._assistant_text.clear()
            self.store.append_event(self.session_id, "turn.interrupted", {})
        elif isinstance(data.frame, LLMFullResponseStartFrame):
            self._assistant_text.clear()
        elif isinstance(data.frame, LLMTextFrame):
            self._assistant_text.append(data.frame.text)
        elif isinstance(data.frame, LLMFullResponseEndFrame):
            text = "".join(self._assistant_text).strip()
            self._assistant_text.clear()
            if text and self.persist_conversation:
                self.store.append_event(
                    self.session_id,
                    "turn.final",
                    {"role": "assistant", "text": text},
                )
        elif isinstance(data.frame, FunctionCallsStartedFrame):
            self.store.append_event(
                self.session_id,
                "tool.requested",
                {
                    "tools": [
                        {
                            "name": call.function_name,
                            "tool_call_id": call.tool_call_id,
                        }
                        for call in data.frame.function_calls
                    ]
                },
            )
        elif isinstance(data.frame, FunctionCallInProgressFrame):
            self.store.append_event(
                self.session_id,
                "tool.started",
                {
                    "name": data.frame.function_name,
                    "tool_call_id": data.frame.tool_call_id,
                },
            )
        elif isinstance(data.frame, FunctionCallResultFrame):
            result = data.frame.result if isinstance(data.frame.result, dict) else {}
            self.store.append_event(
                self.session_id,
                "tool.completed",
                {
                    "name": data.frame.function_name,
                    "tool_call_id": data.frame.tool_call_id,
                    "status": result.get("status"),
                },
            )
        elif isinstance(data.frame, FunctionCallCancelFrame):
            self.store.append_event(
                self.session_id,
                "tool.cancelled",
                {
                    "name": data.frame.function_name,
                    "tool_call_id": data.frame.tool_call_id,
                },
            )
        elif isinstance(data.frame, MetricsFrame):
            self.store.append_event(
                self.session_id,
                "metrics.observed",
                {
                    "measurements": [
                        {"kind": type(metric).__name__, **metric.model_dump(mode="json")}
                        for metric in data.frame.data
                    ]
                },
            )
