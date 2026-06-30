from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from psycopg import DatabaseError

from app.assistant.agent import run_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.events import (
    citations_event,
    error_event,
    status_event,
    text_delta,
    text_end,
    text_start,
)
from app.chat.persistence import auto_title, save_assistant_message, save_user_message, set_thread_title
from app.grounding.validator import GroundingValidator

logger = logging.getLogger(__name__)


async def chat_pipeline(
    deps: DocumentAgentDeps,
    user_message: str,
    user_message_id: str,
) -> AsyncIterator[str]:
    assistant_msg_id: str | None = None
    answer: GroundedAnswer | None = None
    validation = None

    try:
        # ---- persist user message ----
        save_user_message(deps.thread_id, user_message, user_message_id)

        # ---- auto-title (first message only) ----
        title = auto_title(user_message)
        set_thread_title(deps.thread_id, title)

        # ---- retrieve ----
        yield status_event("retrieving", "Searching 22,209 filing chunks...")
        try:
            results = await asyncio.to_thread(deps.retriever.search, user_message)
        except DatabaseError:
            logger.exception("retrieval query failed")
            yield error_event("Search failed. Please try again.")
            return
        except Exception:
            logger.exception("retrieval failed")
            results = []

        chunk_ids = {r.chunk_id for r in results}

        # ---- generate ----
        yield status_event("generating", "Generating answer with citations...")
        try:
            answer = await run_agent(deps, user_message)
        except Exception:
            logger.exception("agent generation failed")
            yield error_event("Failed to generate an answer. Please try again.")
            return

        # ---- validate ----
        yield status_event("grounding", "Validating citations...")
        validator = GroundingValidator(retrieved_chunk_ids=chunk_ids)
        validation = validator.validate(answer)

        if not validation.passed:
            logger.warning("grounding failed", extra={"errors": validation.errors})
            yield status_event("grounding_failed", "; ".join(validation.errors))

        # ---- stream answer ----
        assistant_msg_id = save_assistant_message(
            deps.thread_id,
            answer.answer,
            validation.citations,
            meta={"grounding_errors": validation.errors} if validation.errors else None,
        )
        yield text_start(assistant_msg_id)

        paragraphs = answer.answer.split("\n")
        for i, para in enumerate(paragraphs):
            yield text_delta(assistant_msg_id, ("\n" if i > 0 else "") + para)

        yield citations_event(
            [c.model_dump() for c in validation.citations],
            message_id=assistant_msg_id,
        )
        yield text_end(assistant_msg_id)
        yield status_event("complete", "")

    except Exception:
        logger.exception("unhandled pipeline error")
        yield error_event("An unexpected error occurred.")
        return
