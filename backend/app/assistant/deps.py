from __future__ import annotations

from dataclasses import dataclass, field

from app.retrieval.retriever import DocumentRetriever


@dataclass
class DocumentAgentDeps:
    user_id: str
    thread_id: str
    retriever: DocumentRetriever
    retrieved_chunk_ids: set[str] = field(default_factory=set)
