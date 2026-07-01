from __future__ import annotations

from collections.abc import AsyncIterator

import structlog

from app.assistant.agent import run_agent
from app.assistant.deps import DocumentAgentDeps
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

logger = structlog.get_logger(__name__)


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

        # ---- generate ----
        yield status_event("generating", "Generating answer with citations...")
        try:
            answer = await run_agent(deps, user_message)
        except Exception:
            logger.exception("agent_generation_failed", thread_id=deps.thread_id)
            yield error_event("Failed to generate an answer. Please try again.")
            return

        # ---- validate ----
        yield status_event("grounding", "Validating citations...")
        validator = GroundingValidator(retrieved_chunk_ids=deps.retrieved_chunk_ids)
        validation = validator.validate(answer)

        if not validation.passed:
            logger.warning("grounding_failed", thread_id=deps.thread_id, errors=validation.errors)
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
        logger.exception("pipeline_crash", thread_id=deps.thread_id)
        yield error_event("An unexpected error occurred.")
        return
