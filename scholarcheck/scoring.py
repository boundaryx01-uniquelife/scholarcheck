from __future__ import annotations

from datetime import datetime

from scholarcheck.models import PaperRecord, SearchQuery, UNKNOWN


CURRENT_YEAR = datetime.now().year


def apply_scores(records: list[PaperRecord], query: SearchQuery) -> list[PaperRecord]:
    for record in records:
        record.relevance_score = _relevance_score(record, query.keywords)
        record.recency_score = _recency_score(record.year)
        record.usability_score = _usability_score(record)
        record.total_score = round(
            record.relevance_score * 0.45
            + record.recency_score * 0.25
            + record.usability_score * 0.30,
            2,
        )
        record.caution = _caution(record)

    return sorted(
        records,
        key=lambda item: (item.total_score, item.year or 0, item.pdf_available),
        reverse=True,
    )


def _relevance_score(record: PaperRecord, keywords: list[str]) -> float:
    if not keywords:
        return 0.0

    haystack = " ".join([record.title, record.venue, record.publisher_or_institution]).lower()
    matched = sum(1 for keyword in keywords if keyword.lower() in haystack)
    return round((matched / len(keywords)) * 100, 2)


def _recency_score(year: int | None) -> float:
    if year is None:
        return 0.0
    age = max(CURRENT_YEAR - year, 0)
    if age <= 2:
        return 100.0
    if age <= 5:
        return 80.0
    if age <= 10:
        return 55.0
    return 25.0


def _usability_score(record: PaperRecord) -> float:
    score = 0.0
    if record.doi != UNKNOWN:
        score += 30
    if record.landing_page_url != UNKNOWN:
        score += 25
    if record.pdf_available:
        score += 30
    if record.authors:
        score += 10
    if record.venue != UNKNOWN:
        score += 5
    return min(score, 100.0)


def _caution(record: PaperRecord) -> str:
    cautions: list[str] = []
    if record.doi == UNKNOWN:
        cautions.append("DOI not verified")
    if record.landing_page_url == UNKNOWN:
        cautions.append("Landing page missing")
    if not record.pdf_available:
        cautions.append("PDF availability not confirmed")
    if not record.authors:
        cautions.append("Author metadata missing")
    if record.venue == UNKNOWN:
        cautions.append("Venue metadata missing")
    return "; ".join(cautions) if cautions else "No immediate metadata caution"
