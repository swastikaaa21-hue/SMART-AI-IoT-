"""
Voice endpoints for Indonesian Speech-to-Text, Text-to-Speech, and Voice AI Chat.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.chat import _execute_function
from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.voice import (
    VoiceChatResponse,
    VoiceSynthesizeRequest,
    VoiceTranscribeResponse,
)
from app.services.gemini_service import gemini_service
from app.services.voice_service import voice_service
from app.utils.exceptions import NotFoundError

router = APIRouter()


@router.post(
    "/transcribe",
    response_model=VoiceTranscribeResponse,
    summary="Transcribe audio to Indonesian text",
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, WebM)"),
    user: User = Depends(get_current_user),
) -> VoiceTranscribeResponse:
    """
    Transcribe uploaded Indonesian voice audio into text.
    Supports various accents, casual slang, and different intonations.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty",
        )

    transcript = voice_service.transcribe_audio_bytes(audio_bytes, language="id-ID")
    return VoiceTranscribeResponse(
        transcript=transcript,
        language="id-ID",
        success=bool(transcript.strip()),
    )


@router.post(
    "/synthesize",
    summary="Convert Indonesian text to speech audio",
    response_class=Response,
)
async def synthesize_speech(
    body: VoiceSynthesizeRequest,
    user: User = Depends(get_current_user),
) -> Response:
    """
    Convert text to natural-sounding Indonesian speech audio (MP3).
    """
    audio_bytes = voice_service.synthesize_speech(
        text=body.text,
        language=body.language,
        slow=body.slow,
    )
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate speech audio",
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="speech.mp3"'},
    )


@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    summary="Full Voice AI Chat with IoT execution",
)
async def voice_chat(
    file: UploadFile = File(..., description="Audio recording of voice command"),
    session_id: uuid.UUID | None = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VoiceChatResponse:
    """
    End-to-end voice control:
    1. Transcribes spoken Indonesian audio command.
    2. Interprets intent & executes IoT actions (function calling).
    3. Synthesizes AI response to Indonesian voice audio.
    4. Returns transcript, reply, IoT execution info, and audio output.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file received",
        )

    # 1. Speech to Text
    transcript = voice_service.transcribe_audio_bytes(audio_bytes, language="id-ID")

    # If speech could not be recognized
    if not transcript or not transcript.strip():
        fallback_reply = "Maaf, suara tidak terdengar jelas. Boleh tolong diulang kembali?"
        fallback_audio = voice_service.synthesize_speech(fallback_reply)
        return VoiceChatResponse(
            transcript="",
            reply=fallback_reply,
            audio_base64=voice_service.bytes_to_base64(fallback_audio) if fallback_audio else "",
            session_id=session_id or uuid.uuid4(),
            function_called=None,
            function_result=None,
            devices_affected=[],
        )

    # 2. Get or create chat session
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user.id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("ChatSession", str(session_id))
    else:
        session = ChatSession(
            user_id=user.id,
            title=f"🎙️ {transcript[:45]}" + ("..." if len(transcript) > 45 else ""),
        )
        db.add(session)
        await db.flush()

    # 3. Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=transcript,
    )
    db.add(user_msg)
    await db.flush()

    # 4. Execute AI + Function Calling
    async def executor(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return await _execute_function(name, args, db)

    ai_result = await gemini_service.chat(
        message=transcript,
        session_id=str(session.id),
        function_executor=executor,
    )

    reply_text = ai_result.get("reply", "")

    # 5. Save assistant message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=reply_text,
        function_call=ai_result.get("function_called"),
        function_response=(
            json.dumps(ai_result.get("function_result"))
            if ai_result.get("function_result")
            else None
        ),
    )
    db.add(assistant_msg)
    await db.flush()

    # 6. Synthesize AI reply to speech
    reply_audio_bytes = voice_service.synthesize_speech(reply_text)
    audio_base64 = voice_service.bytes_to_base64(reply_audio_bytes) if reply_audio_bytes else ""

    return VoiceChatResponse(
        transcript=transcript,
        reply=reply_text,
        audio_base64=audio_base64,
        session_id=session.id,
        function_called=ai_result.get("function_called"),
        function_result=ai_result.get("function_result"),
        devices_affected=ai_result.get("devices_affected", []),
    )
