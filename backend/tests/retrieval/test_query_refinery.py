from __future__ import annotations

import pytest

from app.retrieval.query_refinery import RefinedQuery, refine_query


def r(text: str, **kw: str) -> RefinedQuery:
    """Shortcut — refine with no company map (ticker pattern matching only)."""
    cmap: dict[str, str] = {}
    if "apple" in text.lower():
        cmap["apple"] = "AAPL"
        cmap["apple inc."] = "AAPL"
    if "microsoft" in text.lower():
        cmap["microsoft"] = "MSFT"
        cmap["microsoft corporation"] = "MSFT"
    if "amazon" in text.lower():
        cmap["amazon"] = "AMZN"
        cmap["amazon.com inc."] = "AMZN"
    cmap.update(kw)
    return refine_query(text, company_map=cmap)


class TestCompanyNameToTicker:
    def test_apple_resolved(self) -> None:
        result = r("Apple revenue 2024")
        assert "AAPL" in result.tickers

    def test_microsoft_resolved(self) -> None:
        result = r("Microsoft cloud risks")
        assert "MSFT" in result.tickers

    def test_multiple_companies(self) -> None:
        result = r("Compare Apple and Microsoft operating margin")
        assert "AAPL" in result.tickers
        assert "MSFT" in result.tickers

    def test_unknown_company_not_matched(self) -> None:
        result = r("Acme Corp performance")
        assert result.tickers == []


class TestTickerPattern:
    def test_direct_ticker(self) -> None:
        result = r("What about AAPL?")
        assert "AAPL" in result.tickers

    def test_multiple_tickers(self) -> None:
        result = r("AAPL vs MSFT revenue")
        assert "AAPL" in result.tickers
        assert "MSFT" in result.tickers

    def test_false_positive_filtered(self) -> None:
        result = r("THE company's results")
        assert result.tickers == []


class TestYearExtraction:
    def test_four_digit_year(self) -> None:
        result = r("revenue in 2024")
        assert "2024" in result.years

    def test_fy_prefix(self) -> None:
        result = r("FY2024 results")
        assert "2024" in result.years

    def test_fy_space(self) -> None:
        result = r("FY 2024 results")
        assert "2024" in result.years

    def test_multiple_years(self) -> None:
        result = r("compare 2023 and 2024 revenue")
        assert "2023" in result.years
        assert "2024" in result.years


class TestNoiseFiltering:
    def test_show_tell_removed(self) -> None:
        result = r("Show me the risks")
        assert result.clean_query == "risks"

    def test_stopwords_removed(self) -> None:
        result = r("Tell me about the best quarter")
        assert result.clean_query == "quarter"

    def test_proper_nouns_kept(self) -> None:
        result = r("Microsoft Azure growth")
        assert "Microsoft" in result.clean_query
        assert "Azure" in result.clean_query


class TestEdgeCases:
    def test_no_entities(self) -> None:
        result = r("How did the company perform overall?")
        assert result.tickers == []
        assert result.years == []
        assert result.has_filters is False

    def test_all_noise_falls_back_to_original(self) -> None:
        result = r("How are you doing today in the world of things?")
        assert len(result.clean_query) > 0

    def test_mixed_entity_and_noise(self) -> None:
        result = r("Please show me AAPL revenue in 2024")
        assert "AAPL" in result.tickers
        assert "2024" in result.years
        assert result.clean_query == "AAPL revenue 2024"

    def test_empty_query(self) -> None:
        result = r("")
        assert result.clean_query == ""
        assert result.tickers == []
