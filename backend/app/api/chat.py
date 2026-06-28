from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/chat")

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions about SEC filings. "
    "You are currently in stub mode and do not have access to the document corpus."
)


class ChatMessage(BaseModel):
    id: str
    role: str
    content: str


class ChatRequest(BaseModel):
    id: str
    messages: list[ChatMessage]
    trigger: str = "submit-message"
    messageId: str | None = None


@router.post("/stream")
async def chat_stream(body: ChatRequest, user: dict = Depends(get_current_user)) -> StreamingResponse:
    client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")

    openai_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in body.messages:
        openai_messages.append({"role": msg.role, "content": msg.content})

    assistant_msg_id = str(uuid.uuid4())

    def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'text-start', 'id': assistant_msg_id})}\n\n"

            stream = client.chat.completions.create(
                model=settings.llm_model,
                messages=openai_messages,
                stream=True,
            )

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield f"data: {json.dumps({'type': 'text-delta', 'id': assistant_msg_id, 'delta': delta.content})}\n\n"

            yield f"data: {json.dumps({'type': 'text-end', 'id': assistant_msg_id})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'errorText': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
