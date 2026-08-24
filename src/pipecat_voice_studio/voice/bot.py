"""Pipecat runner entry point for validated studio pipelines."""

from __future__ import annotations

from typing import Any, Literal, cast

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.flows import FlowManager
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.run import main
from pipecat.runner.types import EvalRunnerArguments, RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.openai.realtime.events import (
    AudioConfiguration,
    AudioInput,
    AudioOutput,
    InputAudioNoiseReduction,
    InputAudioTranscription,
    SemanticTurnDetection,
    SessionProperties,
)
from pipecat.services.openai.realtime.llm import OpenAIRealtimeLLMService
from pipecat.services.openai.responses.llm import OpenAIResponsesLLMService
from pipecat.services.openai.stt import OpenAIRealtimeSTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.services.simli.video import SimliVideoService
from pipecat.transports.base_transport import TransportParams
from pipecat.workers.runner import WorkerRunner

from pipecat_voice_studio.appointments import AppointmentBook
from pipecat_voice_studio.config import Settings, get_settings
from pipecat_voice_studio.graph import NodeKind, PipelineMode, compile_graph
from pipecat_voice_studio.integrations.google_calendar import GoogleCalendar
from pipecat_voice_studio.security import HealthcareCipher
from pipecat_voice_studio.storage import StudioStore
from pipecat_voice_studio.voice.appointment_flow import build_appointment_flow
from pipecat_voice_studio.voice.business_flow import build_business_flow
from pipecat_voice_studio.voice.healthcare_flow import build_healthcare_flow
from pipecat_voice_studio.voice.timeline import SemanticTimelineObserver


def _api_key(settings: Settings) -> str:
    if settings.openai_api_key is None:
        message = "OPENAI_API_KEY is required to start a voice pipeline"
        raise RuntimeError(message)
    return settings.openai_api_key.get_secret_value()


def _websocket_url(http_url: str | None, endpoint: str) -> str | None:
    if http_url is None:
        return None
    return (
        http_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1).rstrip("/")
        + endpoint
    )


def _pipeline_id(runner_args: RunnerArguments) -> str:
    pipeline_id = (runner_args.body or {}).get("pipeline_id")
    if not isinstance(pipeline_id, str) or not pipeline_id:
        message = "The start request must contain a stored pipeline_id"
        raise ValueError(message)
    return pipeline_id


async def _realtime_processors(
    transport: Any, settings: Settings, graph_settings: dict[str, Any]
) -> list[Any]:
    prompt = str(graph_settings.get("prompt", "Be helpful and concise."))
    voice = str(graph_settings.get("voice", settings.pvs_realtime_voice))
    eagerness = cast(
        "Literal['low', 'medium', 'high', 'auto']",
        str(graph_settings.get("vad_eagerness", "auto")),
    )
    realtime = OpenAIRealtimeLLMService(
        api_key=_api_key(settings),
        model=settings.pvs_realtime_model,
        base_url=_websocket_url(settings.openai_base_url, "/realtime")
        or "wss://api.openai.com/v1/realtime",
        session_properties=SessionProperties(
            instructions=prompt,
            audio=AudioConfiguration(
                input=AudioInput(
                    transcription=InputAudioTranscription(
                        model=settings.pvs_cascade_stt_model,
                        language=str(graph_settings.get("language", "en")),
                    ),
                    noise_reduction=InputAudioNoiseReduction(type="near_field"),
                    turn_detection=SemanticTurnDetection(
                        eagerness=eagerness,
                        create_response=True,
                        interrupt_response=True,
                    ),
                ),
                output=AudioOutput(voice=voice),
            ),
        ),
    )
    context = LLMContext([{"role": "system", "content": prompt}])
    aggregators = LLMContextAggregatorPair(context, realtime_service_mode=True)
    return [
        transport.input(),
        aggregators.user(),
        realtime,
        transport.output(),
        aggregators.assistant(),
    ]


async def _cascade_processors(
    transport: Any,
    settings: Settings,
    graph_settings: dict[str, Any],
    kinds: set[NodeKind],
) -> tuple[list[Any], OpenAIResponsesLLMService, LLMContextAggregatorPair]:
    api_key = _api_key(settings)
    prompt = str(
        graph_settings.get(
            "prompt",
            "Collect appointment details, check availability, and ask for explicit confirmation.",
        )
    )
    realtime_base = _websocket_url(settings.openai_base_url, "/realtime")
    responses_base = _websocket_url(settings.openai_base_url, "/responses")
    stt = OpenAIRealtimeSTTService(
        api_key=api_key,
        model=settings.pvs_cascade_stt_model,
        base_url=realtime_base or "wss://api.openai.com/v1/realtime",
        noise_reduction="near_field",
    )
    llm = OpenAIResponsesLLMService(
        api_key=api_key,
        base_url=settings.openai_base_url,
        ws_url=responses_base or "wss://api.openai.com/v1/responses",
        settings=OpenAIResponsesLLMService.Settings(
            model=settings.pvs_cascade_llm_model,
            system_instruction=prompt,
        ),
    )
    tts = OpenAITTSService(
        api_key=api_key,
        base_url=settings.openai_base_url,
        model=settings.pvs_cascade_tts_model,
        voice=str(graph_settings.get("voice", settings.pvs_realtime_voice)),
        speed=float(graph_settings.get("speed", 1.0)),
    )
    context = LLMContext([{"role": "system", "content": prompt}])
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )
    output_processors: list[Any] = []
    if NodeKind.AVATAR in kinds:
        if settings.simli_api_key is None or settings.simli_face_id is None:
            message = "SIMLI_API_KEY and SIMLI_FACE_ID are required for avatar pipelines"
            raise RuntimeError(message)
        output_processors.append(
            SimliVideoService(
                api_key=settings.simli_api_key.get_secret_value(),
                face_id=settings.simli_face_id,
            )
        )
    return (
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            *output_processors,
            transport.output(),
            aggregators.assistant(),
        ],
        llm,
        aggregators,
    )


async def bot(runner_args: RunnerArguments) -> None:
    """Load, validate, compile, and run one stored pipeline."""
    settings = get_settings()
    store = StudioStore(settings.pvs_database_path)
    store.initialize()
    pipeline_id = _pipeline_id(runner_args)
    graph = store.get_graph(pipeline_id)
    compile_graph(graph)
    if isinstance(runner_args, EvalRunnerArguments) != (graph.mode == PipelineMode.EVAL):
        message = "The selected graph mode does not match the runner transport"
        raise ValueError(message)
    transport = await create_transport(
        runner_args,
        {
            "webrtc": lambda: TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                video_out_enabled=NodeKind.AVATAR in {node.kind for node in graph.nodes},
            ),
            "eval": lambda: TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
            ),
        },
    )
    await run_pipeline(transport, pipeline_id, settings=settings, store=store)


async def run_pipeline(
    transport: Any,
    pipeline_id: str,
    *,
    settings: Settings | None = None,
    store: StudioStore | None = None,
    call_id: str | None = None,
) -> None:
    """Run a stored pipeline over an already-created Pipecat transport."""
    settings = settings or get_settings()
    store = store or StudioStore(settings.pvs_database_path)
    store.initialize()
    graph = store.get_graph(pipeline_id)
    compiled = compile_graph(graph)
    kinds = {node.kind for node in graph.nodes}
    sensitive = NodeKind.HEALTHCARE in kinds
    session_id = store.create_session(
        pipeline_id,
        graph,
        {
            "realtime": settings.pvs_realtime_model,
            "stt": settings.pvs_cascade_stt_model,
            "llm": settings.pvs_cascade_llm_model,
            "tts": settings.pvs_cascade_tts_model,
        },
        sensitive=sensitive,
    )
    if call_id is not None:
        store.update_call(call_id, status="in-progress", session_id=session_id)
    store.append_event(session_id, "transport.connecting", {"transport": compiled.transport})
    flow_parts = None
    if graph.mode == PipelineMode.REALTIME:
        processors = await _realtime_processors(transport, settings, compiled.settings)
    else:
        processors, llm, aggregators = await _cascade_processors(
            transport, settings, compiled.settings, kinds
        )
        flow_parts = (llm, aggregators)
    worker = PipelineWorker(
        Pipeline(processors),
        conversation_id=session_id,
        observers=[SemanticTimelineObserver(store, session_id, persist_conversation=not sensitive)],
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )
    if flow_parts is not None and kinds & {
        NodeKind.APPOINTMENT,
        NodeKind.MULTI_AGENT,
        NodeKind.CRM,
        NodeKind.HANDOFF,
        NodeKind.HEALTHCARE,
    }:
        llm, aggregators = flow_parts
        flow = FlowManager(
            llm=llm,  # ty: ignore[invalid-argument-type]
            context_aggregator=aggregators,
            worker=worker,
            transport=transport,
        )
        if NodeKind.HEALTHCARE in kinds:
            if (
                not settings.pvs_healthcare_enabled
                or settings.pvs_healthcare_data_key is None
                or "openai" not in settings.healthcare_approved_services
            ):
                message = "Healthcare requires enablement, an encryption key, and openai approval"
                raise RuntimeError(message)
            initial_node = build_healthcare_flow(
                store,
                HealthcareCipher(settings.pvs_healthcare_data_key.get_secret_value()),
                session_id,
            )
        elif kinds & {NodeKind.MULTI_AGENT, NodeKind.CRM, NodeKind.HANDOFF}:
            initial_node = build_business_flow(store, settings, session_id, call_id=call_id)
        else:
            calendar = None
            if (
                NodeKind.CALENDAR in kinds
                and settings.google_service_account_json is not None
                and settings.google_calendar_id is not None
            ):
                calendar = GoogleCalendar(
                    settings.google_service_account_json.get_secret_value(),
                    settings.google_calendar_id,
                )
            book = AppointmentBook(store, settings.pvs_timezone, calendar)
            initial_node = build_appointment_flow(book, session_id)
        await flow.initialize(initial_node)
        store.append_event(session_id, "flow.node", {"node": initial_node["name"]})
    try:
        store.append_event(session_id, "transport.connected", {"transport": compiled.transport})
        await WorkerRunner(handle_sigint=False).run(worker)
    except Exception as error:
        store.finish_session(session_id, failure=type(error).__name__)
        if call_id is not None:
            store.update_call(call_id, status="failed", failure=type(error).__name__, ended=True)
        raise
    else:
        store.finish_session(session_id)
        if call_id is not None:
            store.update_call(call_id, status="completed", ended=True)


if __name__ == "__main__":
    main()
