from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from app.api.deps import get_agent_service, get_voice_service
from app.integrations.exceptions import IntegrationNotConfigured
from app.schemas.agents import ConversationRequest
from app.schemas.voice import VoiceSynthesisRequest
from app.services.agent_service import AgentService
from app.services.voice_service import VoiceService

router = APIRouter()


@router.post("/twilio/inbound")
async def twilio_inbound(
    call_sid: Annotated[str, Form(alias="CallSid")],
    from_number: Annotated[str | None, Form(alias="From")] = None,
    to_number: Annotated[str | None, Form(alias="To")] = None,
    speech_result: Annotated[str | None, Form(alias="SpeechResult")] = None,
    voice_service: VoiceService = Depends(get_voice_service),
    agent_service: AgentService = Depends(get_agent_service),
) -> Response:
    await voice_service.record_twilio_turn(
        call_sid=call_sid,
        phone_from=from_number,
        phone_to=to_number,
        transcript=speech_result,
    )
    if not speech_result:
        return Response(content=voice_service.prompt_twilio(), media_type="application/xml")

    answer = await agent_service.conversation(
        ConversationRequest(
            message=speech_result,
            use_rag=True,
            metadata={"channel": "twilio", "call_sid": call_sid},
        )
    )
    return Response(
        content=voice_service.answer_twilio(answer.answer),
        media_type="application/xml",
    )


@router.post("/synthesize")
async def synthesize_voice(
    payload: VoiceSynthesisRequest,
    service: VoiceService = Depends(get_voice_service),
) -> StreamingResponse:
    try:
        audio = await service.synthesize(text=payload.text, voice_id=payload.voice_id)
    except IntegrationNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return StreamingResponse(
        iter([audio.content]),
        media_type=audio.content_type,
        headers={"Content-Disposition": 'inline; filename="agent-response.mp3"'},
    )
