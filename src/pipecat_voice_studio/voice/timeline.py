"""Semantic Pipecat frame observer; deliberately excludes raw audio."""

from typing import TYPE_CHECKING

from pipecat.frames.frames import InterruptionFrame, MetricsFrame, TranscriptionFrame
from pipecat.observers.base_observer import BaseObserver, FramePushed

if TYPE_CHECKING:
    from pipecat_voice_studio.storage import StudioStore


class SemanticTimelineObserver(BaseObserver):
    """Persist final user turns, interruptions, and metric signals once."""

    def __init__(self, store: StudioStore, session_id: str) -> None:
        super().__init__()
        self.store = store
        self.session_id = session_id
        self._seen: set[int] = set()

    async def on_push_frame(self, data: FramePushed) -> None:
        """Map selected Pipecat frames into bounded semantic events."""
        if data.frame.id in self._seen:
            return
        self._seen.add(data.frame.id)
        if isinstance(data.frame, TranscriptionFrame) and data.frame.finalized:
            self.store.append_event(
                self.session_id,
                "turn.final",
                {"role": "user", "text": data.frame.text, "language": str(data.frame.language)},
            )
        elif isinstance(data.frame, InterruptionFrame):
            self.store.append_event(self.session_id, "turn.interrupted", {})
        elif isinstance(data.frame, MetricsFrame):
            self.store.append_event(
                self.session_id,
                "metrics.observed",
                {"measurements": [type(metric).__name__ for metric in data.frame.data]},
            )
