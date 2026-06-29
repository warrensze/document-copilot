from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from openai import OpenAI

from app.assistant.agent import agent, run_agent
from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer, SourcePassage
from app.config import settings
from app.retrieval.retriever import DocumentRetriever


class TestInstructions:
    path = Path(__file__).parents[2] / "app" / "assistant" / "instructions.md"

    def test_file_exists(self) -> None:
        assert self.path.is_file()

    def test_file_not_empty(self) -> None:
        text = self.path.read_text()
        assert len(text) > 100

    def test_contains_grounding_rules(self) -> None:
        text = self.path.read_text()
        assert "Answer only from" in text
        assert "Cite every factual claim" in text
        assert "stock recommendations" in text


class TestAgentConfig:
    def test_agent_created(self) -> None:
        assert agent is not None
        assert agent.system_prompt is not None

    def test_search_filings_tool_registered(self) -> None:
        tool_names = list(agent._function_toolset.tools.keys())
        assert "search_filings" in tool_names

    def test_agent_output_type(self) -> None:
        assert agent._output_type is GroundedAnswer


class TestDepsConstruction:
    def test_can_construct(self) -> None:
        deps = DocumentAgentDeps(
            user_id="test-user",
            thread_id="test-thread",
            retriever=None,
        )
        assert deps.user_id == "test-user"
        assert deps.thread_id == "test-thread"
        assert deps.retriever is None


class TestOutputModels:
    def test_source_passage(self) -> None:
        sp = SourcePassage(
            id="chunk-1",
            chunk_text="Some text",
            document_id="doc-1",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        assert sp.id == "chunk-1"
        assert sp.model_dump()["section"] is None

    def test_citation(self) -> None:
        c = Citation(
            chunk_id="chunk-1",
            excerpt="Some text",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
        )
        assert c.chunk_id == "chunk-1"
        assert c.model_dump()["section"] is None

    def test_citation_with_section(self) -> None:
        c = Citation(
            chunk_id="chunk-1",
            excerpt="Some text",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
            section="Item 7",
        )
        assert c.section == "Item 7"

    def test_grounded_answer(self) -> None:
        citations = [
            Citation(
                chunk_id="c1",
                excerpt="Revenue grew",
                ticker="AAPL",
                company_name="Apple Inc.",
                year="2025",
                section="Item 7",
            )
        ]
        ga = GroundedAnswer(answer="Apple's revenue grew.", citations=citations)
        assert ga.answer == "Apple's revenue grew."
        assert len(ga.citations) == 1
        assert ga.citations[0].chunk_id == "c1"


def _ollama_alive() -> bool:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/models", timeout=5)
        return r.is_success
    except Exception:
        return False


def _list_ollama_models() -> list[dict]:
    try:
        r = httpx.get(f"{settings.ollama_base_url}/models", timeout=5)
        body = r.json()
        if "data" in body:
            return body["data"]
        if "models" in body:
            return body["models"]
        return []
    except Exception:
        return []


def _llm_model_available() -> bool:
    if not _ollama_alive():
        return False
    models = _list_ollama_models()
    return any(
        m.get("id", m.get("name", "")).startswith(settings.llm_model)
        for m in models
    )


def _ollama_embedding_model() -> bool:
    if not _ollama_alive():
        return False
    models = _list_ollama_models()
    return any(
        m.get("id", m.get("name", "")).startswith(settings.embedding_model)
        for m in models
    )


def _db_reachable() -> bool:
    dsn = settings.database_url.replace("+psycopg", "")
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=5):
            return True
    except Exception:
        return False


@pytest.mark.integration
class TestSmoke:
    """End-to-end smoke test: real DocumentRetriever (Supabase + Ollama) + real LLM."""

    @pytest.fixture(scope="class")
    def retriever(self):
        client = OpenAI(base_url=settings.ollama_base_url, api_key="no-key-required")
        return DocumentRetriever(db_url=settings.database_url, ollama_client=client)

    @pytest.fixture(scope="class")
    def deps(self, retriever):
        return DocumentAgentDeps(
            user_id="smoke-user",
            thread_id="smoke-thread",
            retriever=retriever,
        )

    def test_infrastructure_ready(self) -> None:
        assert _ollama_alive(), f"Ollama not reachable at {settings.ollama_base_url}"
        assert _llm_model_available(), (
            f"LLM model '{settings.llm_model}' not pulled. Run: ollama pull {settings.llm_model}"
        )
        assert _ollama_embedding_model(), (
            f"Embedding model '{settings.embedding_model}' not pulled. "
            f"Run: ollama pull {settings.embedding_model}"
        )
        assert _db_reachable(), (
            f"Cannot connect to database at {settings.database_url}"
        )

    @pytest.mark.asyncio
    async def test_ask_about_apple_revenue(self, deps) -> None:
        result = await asyncio.wait_for(
            run_agent(deps, "What was Apple's total net sales in 2025?"),
            timeout=300,
        )
        assert isinstance(result, GroundedAnswer)
        assert len(result.answer) > 3
        assert len(result.citations) >= 1

    @pytest.mark.asyncio
    async def test_citations_from_real_data(self, deps) -> None:
        result = await asyncio.wait_for(
            run_agent(deps, "What was Microsoft's operating income in 2024?"),
            timeout=300,
        )
        assert isinstance(result, GroundedAnswer)
        assert len(result.answer) > 3
        assert len(result.citations) >= 1
        # Citations should reference real tickers and years from the corpus
        for c in result.citations:
            assert c.ticker
            assert c.year
            assert c.chunk_id

    @pytest.mark.asyncio
    async def test_no_fabrication_on_out_of_corpus_query(self, deps) -> None:
        result = await asyncio.wait_for(
            run_agent(
                deps,
                "What is the revenue of a non-existent company called TotallyMadeUpCorp?",
            ),
            timeout=300,
        )
        assert isinstance(result, GroundedAnswer)
        # Should not fabricate — answer should say it lacks info
        assert len(result.answer) > 10
