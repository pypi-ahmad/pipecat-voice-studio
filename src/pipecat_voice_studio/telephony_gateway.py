"""Public callback gateway for Twilio and Vonage media WebSockets.

Accepts public internet webhook and WebSocket traffic from telephony carriers,
validating carrier signatures, minting short-lived media tokens, and bridging
carrier audio streams into Pipecat pipeline workers. Must not accept unsigned
callbacks or expired media tokens, and must not store unredacted phone numbers.
See `integrations/telephony.py` for outbound call initiation and `voice/bot.py`
for how the audio pipeline is constructed and executed.
"""

from __future__ import annotations

import json
from html import escape
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.serializers.vonage import VonageFrameSerializer
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from pipecat_voice_studio.config import Settings, get_settings
from pipecat_voice_studio.security import (
    digest_phone,
    redact_phone,
    sign_media_token,
    verify_media_token,
    verify_twilio_signature,
    verify_vonage_webhook,
)
from pipecat_voice_studio.storage import StudioStore
from pipecat_voice_studio.voice.bot import run_pipeline

app = FastAPI(title="Pipecat Voice Studio Telephony Gateway", docs_url=None, redoc_url=None)


def _store(settings: Settings) -> StudioStore:
    store = StudioStore(settings.pvs_database_path)
    store.initialize()
    return store


def _secret(settings: Settings, provider: str) -> str:
    value = settings.twilio_auth_token if provider == "twilio" else settings.vonage_private_key
    if value is None:
        raise HTTPException(status_code=503, detail="Provider is not configured")
    return value.get_secret_value()


def _bound_pipeline(store: StudioStore, provider: str) -> str:
    try:
        return store.get_integration_binding(provider)
    except KeyError as error:
        raise HTTPException(status_code=503, detail="No pipeline is bound to provider") from error


async def _form(request: Request) -> dict[str, str]:
    return {key: str(value) for key, value in (await request.form()).items()}


async def _verified_twilio_form(request: Request, settings: Settings) -> dict[str, str]:
    params = await _form(request)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = f"{settings.pvs_public_base_url}{request.url.path}"
    if not verify_twilio_signature(url, params, signature, _secret(settings, "twilio")):
        raise HTTPException(status_code=403, detail="Invalid provider signature")
    return params


def _verify_vonage(request: Request, settings: Settings) -> None:
    if settings.vonage_signature_secret is None or settings.vonage_api_key is None:
        raise HTTPException(status_code=503, detail="Vonage signed webhooks are not configured")
    if not verify_vonage_webhook(
        request.headers.get("Authorization", ""),
        settings.vonage_signature_secret.get_secret_value(),
        settings.vonage_api_key,
    ):
        raise HTTPException(status_code=403, detail="Invalid provider signature")


def _ensure_call(
    store: StudioStore,
    settings: Settings,
    *,
    provider: str,
    provider_call_id: str,
    remote: str,
    direction: str,
) -> str:
    try:
        return str(store.get_call_by_provider_id(provider, provider_call_id)["id"])
    except KeyError:
        secret = _secret(settings, provider)
        return store.create_call(
            provider=provider,
            provider_call_id=provider_call_id,
            direction=direction,
            remote_last_four=redact_phone(remote),
            remote_digest=digest_phone(remote, secret),
        )


@app.get("/health")
def health() -> dict[str, str]:
    """Return callback-gateway liveness without configuration details."""
    return {"status": "ok"}


@app.post("/telephony/twilio/answer")
async def twilio_answer(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> Response:
    """Return TwiML connecting an authenticated call to Pipecat media."""
    params = await _verified_twilio_form(request, settings)
    store = _store(settings)
    _bound_pipeline(store, "twilio")
    call_sid = params["CallSid"]
    direction = "outbound" if params.get("Direction", "").startswith("outbound") else "inbound"
    remote = params["To"] if direction == "outbound" else params["From"]
    call_id = _ensure_call(
        store,
        settings,
        provider="twilio",
        provider_call_id=call_sid,
        remote=remote,
        direction=direction,
    )
    token = sign_media_token(call_id, _secret(settings, "twilio"))
    media_url = f"{settings.public_websocket_base_url}/telephony/twilio/media/{token}"
    xml = f'<Response><Connect><Stream url="{media_url}" /></Connect></Response>'
    return Response(xml, media_type="application/xml")


@app.post("/telephony/twilio/status")
async def twilio_status(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, bool]:
    """Persist Twilio call lifecycle callbacks."""
    params = await _verified_twilio_form(request, settings)
    store = _store(settings)
    try:
        call = store.get_call_by_provider_id("twilio", params["CallSid"])
    except KeyError:
        return {"accepted": False}
    status = params.get("CallStatus", "unknown")
    store.update_call(
        str(call["id"]),
        status=status,
        ended=status in {"completed", "failed", "busy", "no-answer", "canceled"},
    )
    return {"accepted": True}


@app.websocket("/telephony/twilio/media/{token}")
async def twilio_media(websocket: WebSocket, token: str) -> None:
    """Run one Twilio Media Stream through its bound cascade pipeline."""
    settings = get_settings()
    try:
        # Rejects connection with WebSocket 1008 (Policy Violation) if token is expired (>300s)
        # or has an invalid HMAC signature.
        call_id = verify_media_token(token, _secret(settings, "twilio"))
    except ValueError:
        await websocket.close(code=1008)
        return
    store = _store(settings)
    pipeline_id = _bound_pipeline(store, "twilio")
    await websocket.accept()
    # Twilio sends a JSON handshake packet with streamSid/callSid before streaming raw μ-law audio.
    first = json.loads(await websocket.receive_text())
    start: dict[str, Any] = first.get("start", {})
    serializer = TwilioFrameSerializer(
        stream_sid=str(start.get("streamSid", "")),
        call_sid=str(start.get("callSid", "")),
        account_sid=settings.twilio_account_sid,
        auth_token=_secret(settings, "twilio"),
    )
    transport = FastAPIWebsocketTransport(
        websocket,
        FastAPIWebsocketParams(
            audio_in_enabled=True, audio_out_enabled=True, serializer=serializer
        ),
    )
    await run_pipeline(transport, pipeline_id, settings=settings, store=store, call_id=call_id)


@app.post("/telephony/twilio/handoff/{handoff_id}")
async def twilio_handoff_briefing(
    handoff_id: str,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Brief the answered human leg before Twilio joins it to the caller."""
    await _verified_twilio_form(request, settings)
    try:
        handoff = _store(settings).get_handoff(handoff_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Handoff not found") from error
    xml = f"<Response><Say>{escape(str(handoff['summary']))}</Say></Response>"
    return Response(xml, media_type="application/xml")


@app.get("/telephony/vonage/answer")
async def vonage_answer(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> list[dict[str, Any]]:
    """Return an NCCO connecting a Vonage Voice call to Pipecat media."""
    _verify_vonage(request, settings)
    store = _store(settings)
    _bound_pipeline(store, "vonage")
    call_uuid = request.query_params.get("uuid", "")
    remote = request.query_params.get("from", "")
    if not call_uuid or not remote:
        raise HTTPException(status_code=400, detail="Missing call identity")
    call_id = _ensure_call(
        store,
        settings,
        provider="vonage",
        provider_call_id=call_uuid,
        remote=remote,
        direction="inbound",
    )
    token = sign_media_token(call_id, _secret(settings, "vonage"))
    return [
        {
            "action": "connect",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": f"{settings.public_websocket_base_url}/telephony/vonage/media/{token}",
                    "content-type": "audio/l16;rate=16000",
                }
            ],
        }
    ]


@app.post("/telephony/vonage/events")
async def vonage_events(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, bool]:
    """Persist Vonage call lifecycle callbacks."""
    _verify_vonage(request, settings)
    payload = await request.json()
    store = _store(settings)
    try:
        call = store.get_call_by_provider_id("vonage", str(payload["uuid"]))
    except KeyError:
        return {"accepted": False}
    status = str(payload.get("status", "unknown"))
    store.update_call(
        str(call["id"]),
        status=status,
        ended=status in {"completed", "failed", "busy", "unanswered", "rejected"},
    )
    return {"accepted": True}


@app.websocket("/telephony/vonage/media/{token}")
async def vonage_media(websocket: WebSocket, token: str) -> None:
    """Run one Vonage audio WebSocket through its bound cascade pipeline."""
    settings = get_settings()
    try:
        # Rejects connection with WebSocket 1008 if media token expired or failed HMAC verification.
        call_id = verify_media_token(token, _secret(settings, "vonage"))
    except ValueError:
        await websocket.close(code=1008)
        return
    store = _store(settings)
    pipeline_id = _bound_pipeline(store, "vonage")
    await websocket.accept()
    # 640 bytes = 20ms of 16kHz 16-bit mono linear PCM audio (16000 * 2 * 0.02 = 640 bytes).
    transport = FastAPIWebsocketTransport(
        websocket,
        FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            serializer=VonageFrameSerializer(),
            fixed_audio_packet_size=640,
        ),
    )
    await run_pipeline(transport, pipeline_id, settings=settings, store=store, call_id=call_id)


@app.get("/telephony/vonage/handoff/{handoff_id}")
async def vonage_handoff_briefing(
    handoff_id: str,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[dict[str, str]]:
    """Brief the answered human leg before Vonage joins it to the caller."""
    _verify_vonage(request, settings)
    try:
        handoff = _store(settings).get_handoff(handoff_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Handoff not found") from error
    return [{"action": "talk", "text": str(handoff["summary"])}]
