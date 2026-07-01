from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.assistant.deps import DocumentAgentDeps
from app.assistant.outputs import Citation, GroundedAnswer
from app.chat.pipeline import chat_pipeline
from app.retrieval.retriever import DocumentRetriever


def _collect_events(gen):
    import asyncio
    return asyncio.run(_collect(gen))


async def _collect(gen):
    return [e async for e in gen]


@patch("app.chat.pipeline.save_user_message")
@patch("app.chat.pipeline.set_thread_title")
@patch("app.chat.pipeline.save_assistant_message")
@patch("app.chat.pipeline.run_agent")
class TestChatPipeline:
    def _make_deps(self, chunk_ids: set[str] | None = None) -> DocumentAgentDeps:
        retriever = MagicMock(spec=DocumentRetriever)
        return DocumentAgentDeps(
            user_id="user-1",
            thread_id="thread-1",
            retriever=retriever,
            retrieved_chunk_ids=chunk_ids or set(),
        )

    def test_happy_path(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user):
        deps = self._make_deps(chunk_ids={"chunk-1"})
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

        gen = chat_pipeline(deps, "How did Apple perform?", "user-msg-1")
        events = _collect_events(gen)

        assert any("generating" in e for e in events)
        assert any("grounding" in e for e in events)
        assert any("text-start" in e for e in events)
        assert any("text-delta" in e for e in events)
        assert any("citations" in e for e in events)
        assert any("text-end" in e for e in events)
        assert any("complete" in e for e in events)

        mock_save_user.assert_called_once_with("thread-1", "How did Apple perform?", "user-msg-1")
        mock_run_agent.assert_awaited_once()

    def test_missing_chunk_ids_grounding_failure(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user):
        deps = self._make_deps(chunk_ids={"chunk-other"})
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

        gen = chat_pipeline(deps, "Query?", "user-msg-4")
        events = _collect_events(gen)

        assert any("grounding_failed" in e for e in events)
        assert any("text-start" in e for e in events)
        assert any("text-end" in e for e in events)

    def test_generation_failure_yields_error(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user):
        deps = self._make_deps()
        mock_run_agent.side_effect = Exception("LLM timeout")

        gen = chat_pipeline(deps, "Query?", "user-msg-3")
        events = _collect_events(gen)

        assert any("error" in e for e in events)

    def test_empty_chunk_ids_no_citations(self, mock_run_agent, mock_save_assistant, mock_set_title, mock_save_user):
        deps = self._make_deps(chunk_ids=set())
        mock_run_agent.return_value = GroundedAnswer(
            answer="No information available.",
            citations=[],
        )
        mock_save_assistant.return_value = "assistant-msg-3"

        gen = chat_pipeline(deps, "Unknown?", "user-msg-5")
        events = _collect_events(gen)

        assert any("text-start" in e for e in events)
        assert any("complete" in e for e in events)
