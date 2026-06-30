from __future__ import annotations

import uuid

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import OpenAI
from pydantic import BaseModel

from app.assistant.deps import DocumentAgentDeps
from app.auth.dependencies import get_current_user
from app.chat.pipeline import chat_pipeline
from app.chat.persistence import (
    get_or_create_thread,
    get_thread_messages,
    list_threads,
    set_thread_title,
)
from app.config import settings
from app.retrieval.retriever import DocumentRetriever

router = APIRouter(prefix="/chat")


class ChatMessagePayload(BaseModel):
    id: str
    role: str
    content: str


class ChatRequest(BaseModel):
    id: str
    messages: list[ChatMessagePayload]
    trigger: str = "submit-message"
    messageId: str | None = None


class RenameRequest(BaseModel):
    title: str


class CreateThreadResponse(BaseModel):
    id: str


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    thread_id = body.id
    owner_id = user["id"]
    email = user.get("email", "unknown@placeholder.com")
    user_message_id = body.messageId or str(uuid.uuid4())

    last_user_msg = next(
        (m for m in reversed(body.messages) if m.role == "user"), None
    )
    if last_user_msg is None:
        raise HTTPException(status_code=400, detail="No user message found")

    get_or_create_thread(thread_id, owner_id, email)

    ollama_client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")
    retriever = DocumentRetriever(
        db_url=settings.database_url,
        ollama_client=ollama_client,
    )
    deps = DocumentAgentDeps(
        user_id=owner_id,
        thread_id=thread_id,
        retriever=retriever,
    )

    async def event_stream():
        async for event in chat_pipeline(deps, last_user_msg.content, user_message_id):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/threads")
async def list_user_threads(user: dict = Depends(get_current_user)):
    return list_threads(user["id"])


@router.post("/threads")
async def create_thread(user: dict = Depends(get_current_user)):
    thread_id = str(uuid.uuid4())
    get_or_create_thread(thread_id, user["id"], user.get("email", ""))
    return CreateThreadResponse(id=thread_id)


@router.get("/threads/{thread_id}/messages")
async def thread_messages(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    msgs = get_thread_messages(thread_id, user["id"])
    if msgs is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return msgs


@router.patch("/threads/{thread_id}")
async def rename_thread(
    thread_id: str,
    body: RenameRequest,
    user: dict = Depends(get_current_user),
):
    set_thread_title(thread_id, body.title)
    return {"ok": True}
