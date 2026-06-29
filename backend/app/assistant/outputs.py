from __future__ import annotations

from pydantic import BaseModel


class SourcePassage(BaseModel):
    id: str
    chunk_text: str
    section: str | None = None
    document_id: str
    ticker: str
    company_name: str
    year: str


class Citation(BaseModel):
    chunk_id: str
    excerpt: str
    ticker: str
    company_name: str
    year: str
    section: str | None = None


class GroundedAnswer(BaseModel):
    answer: str
    citations: list[Citation]
