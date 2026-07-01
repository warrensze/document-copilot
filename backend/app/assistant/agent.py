from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import structlog
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import GroundedAnswer
from app.config import settings

logger = structlog.get_logger(__name__)

_instructions = (Path(__file__).parent / "instructions.md").read_text()

_provider = OllamaProvider(base_url=settings.ollama_base_url)
_profile = _provider.model_profile(settings.llm_model)
# Embed the JSON schema in the prompt text so the model can still call
# search_filings as a regular tool while producing structured output.
_profile = replace(_profile, default_structured_output_mode='prompted')

_model = OpenAIChatModel(
    settings.llm_model,
    provider=_provider,
    profile=_profile,
)

agent: Agent[DocumentAgentDeps, GroundedAnswer] = Agent(
    _model,
    system_prompt=_instructions,
    output_type=GroundedAnswer,
    deps_type=DocumentAgentDeps,
    retries=2,
)


@agent.tool
async def search_filings(
    ctx: RunContext[DocumentAgentDeps],
    query: str,
    top_k: int = 10,
) -> str:
    results = await asyncio.to_thread(ctx.deps.retriever.search, query, top_k)

    ctx.deps.retrieved_chunk_ids.update({r.chunk_id for r in results})

    if not results:
        return "No relevant passages found in the SEC filing corpus."

    passages: list[str] = []
    for i, r in enumerate(results, start=1):
        excerpt = r.chunk_text[:500]
        passages.append(
            f"[{i}] chunk_id={r.chunk_id} | "
            f"{r.ticker} ({r.company_name}), {r.year} | "
            f"Section: {r.section or 'N/A'}\n"
            f"{excerpt}"
        )

    return "\n\n---\n\n".join(passages)


async def run_agent(deps: DocumentAgentDeps, user_message: str) -> GroundedAnswer:
    try:
        result = await agent.run(user_message, deps=deps)
        return result.output
    except Exception:
        logger.exception("agent_run_failed", thread_id=deps.thread_id, message=user_message[:200])
        return GroundedAnswer(
            answer=(
                "I encountered an issue processing your request. "
                "My expertise is limited to SEC filing analysis. "
                "Please try asking about a specific company's SEC 10-K filing."
            ),
            citations=[],
        )
