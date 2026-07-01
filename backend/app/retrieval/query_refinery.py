from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

import psycopg

logger = structlog.get_logger(__name__)

# --- NLTK stopwords (lazy-loaded) ---

_STOPWORDS: set[str] | None = None


def _load_stopwords() -> set[str]:
    global _STOPWORDS
    if _STOPWORDS is not None:
        return _STOPWORDS
    try:
        import nltk

        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            nltk.download("stopwords", quiet=True)
        _STOPWORDS = set(nltk.corpus.stopwords.words("english"))
    except Exception:
        logger.warning("nltk stopwords unavailable, using minimal fallback")
        _STOPWORDS = {
            "a", "an", "the", "in", "on", "at", "for", "of", "to", "is",
            "it", "as", "by", "or", "and", "not", "be", "are", "was",
            "were", "been", "being", "do", "does", "did", "but", "if",
            "so", "up", "no", "we", "he", "she", "they", "you",
            "this", "that", "these", "those", "with", "from", "about",
        }
    return _STOPWORDS


_DOMAIN_NOISE: frozenset[str] = frozenset({
    "show", "tell", "describe", "explain", "list", "give", "find",
    "provide", "share", "detail", "summarize", "highlight", "compare",
    "analyze", "review", "look", "check", "need", "want", "like",
    "please", "help", "know", "think", "best", "worst", "top",
    "highest", "lowest", "biggest", "largest", "smallest", "greatest",
    "better", "worse", "regarding", "including", "various", "certain",
    "overall", "specific", "related", "various",
    "regarding", "regarding",
})

# --- Company name → ticker map (lazy-loaded from DB) ---

_COMPANY_MAP: dict[str, str] | None = None


def _load_company_map(db_url: str) -> dict[str, str]:
    global _COMPANY_MAP
    if _COMPANY_MAP is not None:
        return _COMPANY_MAP
    try:
        dsn = db_url.replace("+psycopg", "")
        with psycopg.connect(dsn, autocommit=True) as conn:
            rows = conn.execute(
                "SELECT DISTINCT ticker, company_name FROM source_documents"
            ).fetchall()
        result: dict[str, str] = {}
        for ticker, company_name in rows:
            result[company_name.lower().strip()] = ticker
            short = company_name.split()[0].lower().strip("., ")
            result[short] = ticker
            result[ticker.lower()] = ticker
        _COMPANY_MAP = result
        logger.info("loaded %d company name mappings", len(result))
    except Exception:
        logger.warning("failed to load company map from DB", exc_info=True)
        _COMPANY_MAP = {}
    return _COMPANY_MAP


# --- Regex patterns ---

_TICKER_PATTERN = re.compile(r"\b([A-Z]{1,5})\b")

_TICKER_FALSE_POSITIVES: frozenset[str] = frozenset({
    "THE", "FOR", "AND", "ARE", "NOT", "YOU", "ALL", "CAN", "HAS", "HAD",
    "ITS", "OUR", "NEW", "ONE", "TWO", "SIX", "TEN", "ANY", "BUT", "HOW",
    "NOW", "PER", "GET", "SEE", "USE", "WAY", "WAS", "WHO", "WHY", "MAY",
    "INC", "LTD", "CORP", "LLC", "GPS", "USA", "CEO", "CFO", "SMB",
    "FAQ", "ETA", "FYI", "ASAP", "ROI", "KPI",
})

_YEAR_PATTERN = re.compile(r"\b(?:FY\s*)?(20\d{2})\b", re.IGNORECASE)


# --- Public types ---


@dataclass
class RefinedQuery:
    tickers: list[str] = field(default_factory=list)
    years: list[str] = field(default_factory=list)
    clean_query: str = ""
    has_filters: bool = False


# --- Extraction logic ---


def _extract_tickers(text: str, company_map: dict[str, str]) -> list[str]:
    found: list[str] = []

    lower = text.lower()
    for name, ticker in sorted(company_map.items(), key=lambda x: -len(x[0])):
        if name in lower:
            if ticker not in found:
                found.append(ticker)

    for match in _TICKER_PATTERN.finditer(text):
        candidate = match.group(1)
        if candidate not in _TICKER_FALSE_POSITIVES:
            if candidate not in found:
                found.append(candidate)

    return found


def _extract_years(text: str) -> list[str]:
    return list({m.group(1) for m in _YEAR_PATTERN.finditer(text)})


def _filter_noise(text: str, stopwords: set[str]) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?", text)
    kept: list[str] = []
    for token in tokens:
        lower = token.lower().strip("'’")
        if not lower:
            continue
        if lower in stopwords or lower in _DOMAIN_NOISE:
            continue
        kept.append(token)
    return " ".join(kept)


# --- Public API ---


def load_company_map(db_url: str) -> dict[str, str]:
    return _load_company_map(db_url)


def refine_query(text: str, company_map: dict[str, str] | None = None) -> RefinedQuery:
    if not text.strip():
        return RefinedQuery(clean_query=text)

    cmap = company_map or {}
    stopwords = _load_stopwords()

    tickers = _extract_tickers(text, cmap)
    years = _extract_years(text)
    clean = _filter_noise(text, stopwords)

    if not clean:
        clean = text

    return RefinedQuery(
        tickers=tickers,
        years=years,
        clean_query=clean,
        has_filters=bool(tickers or years),
    )
