from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.pipeline import chat_pipeline
from app.retrieval.queries import SearchResult


@pytest.fixture
def mock_deps():
    retriever = MagicMock()
    retriever.search.return_value = [
        SearchResult(
            chunk_id="chunk-1",
            chunk_text="Revenue grew 10% to $391B.",
            section="Item 7",
            document_id="doc-1",
            ticker="AAPL",
            company_name="Apple Inc.",
            year="2025",
            score=0.95,
        ),
    ]
    deps = MagicMock()
    deps.retriever = retriever
    deps.user_id = "user-1"
    deps.thread_id = "thread-1"
    return deps


def _collect_events(gen):
    """Consume an async generator and return all yielded strings."""
    import asyncio
    return asyncio.run(_collect(gen))


async def _collect(gen):
    return [e async for e in gen]


@patch("app.chat.pipeline.save_user_message")
@patch("app.chat.pipeline.set_thread_title")
@patch("app.chat.pipeline.save_assistant_message")
@patch("app.chat.pipeline.run_agent")
class TestChatPipeline:
    def test_happy_path(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user, mock_deps):
        mock_run_agent.return_value = GroundedAnswer(
            answer="Apple's revenue grew 10%.",
            citations=[
                Citation(
                    chunk_id="chunk-1",
                    excerpt="Revenue grew 10% to $391B.",
                    ticker="AAPL",
                    company_name="Apple Inc.",
                    year="2025",
                    section="Item 7",
                ),
            ],
        )
        mock_save_assistant.return_value = "assistant-msg-1"

        gen = chat_pipeline(mock_deps, "How did Apple perform?", "user-msg-1")
        events = _collect_events(gen)

        assert any("retrieving" in e for e in events)
        assert any("generating" in e for e in events)
        assert any("grounding" in e for e in events)
        assert any("text-start" in e for e in events)
        assert any("text-delta" in e for e in events)
        assert any("citations" in e for e in events)
        assert any("text-end" in e for e in events)
        assert any("complete" in e for e in events)

        mock_save_user.assert_called_once_with("thread-1", "How did Apple perform?", "user-msg-1")
        mock_run_agent.assert_awaited_once()

    def test_retrieval_failure_graceful(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user, mock_deps):
        mock_deps.retriever.search = MagicMock(side_effect=Exception("DB down"))
        mock_run_agent.return_value = GroundedAnswer(
            answer="No data available.",
            citations=[],
        )
        mock_save_assistant.return_value = "assistant-msg-err"

        gen = chat_pipeline(mock_deps, "Query?", "user-msg-2")
        events = _collect_events(gen)

        assert any("generating" in e for e in events)
        assert any("text-end" in e for e in events)
        mock_run_agent.assert_awaited_once()

    def test_generation_failure_yields_error(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user, mock_deps):
        mock_run_agent.side_effect = Exception("LLM timeout")

        gen = chat_pipeline(mock_deps, "Query?", "user-msg-3")
        events = _collect_events(gen)

        assert any("error" in e for e in events)

    def test_grounding_failure_yields_status(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user, mock_deps):
        mock_run_agent.return_value = GroundedAnswer(
            answer="Some answer.",
            citations=[
                Citation(
                    chunk_id="chunk-fake",
                    excerpt="Fake",
                    ticker="AAPL",
                    company_name="Apple Inc.",
                    year="2025",
                ),
            ],
        )
        mock_save_assistant.return_value = "assistant-msg-2"

        gen = chat_pipeline(mock_deps, "Query?", "user-msg-4")
        events = _collect_events(gen)

        assert any("grounding_failed" in e for e in events)
        # Should still stream the answer
        assert any("text-start" in e for e in events)
        assert any("text-end" in e for e in events)

    def test_empty_retrieval_results(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user, mock_deps):
        mock_deps.retriever.search = MagicMock(return_value=[])
        mock_run_agent.return_value = GroundedAnswer(
            answer="No information available.",
            citations=[],
        )
        mock_save_assistant.return_value = "assistant-msg-3"

        gen = chat_pipeline(mock_deps, "Unknown?", "user-msg-5")
        events = _collect_events(gen)

        assert any("text-start" in e for e in events)
        assert any("complete" in e for e in events)
