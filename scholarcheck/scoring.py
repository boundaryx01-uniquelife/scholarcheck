from __future__ import annotations

from datetime import datetime

from scholarcheck.models import PaperRecord, SearchQuery, UNKNOWN


CURRENT_YEAR = datetime.now().year
RECENT_YEAR_WINDOW = 5
CLASSIC_MIN_AGE = 10
CLASSIC_CITATION_THRESHOLD = 250


def filter_and_score(records: list[PaperRecord], query: SearchQuery) -> list[PaperRecord]:
    filtered = [
        record
        for record in records
        if not _contains_any(_title_and_abstract(record), query.excluded_keywords)
    ]
    return apply_scores(filtered, query)


def apply_scores(records: list[PaperRecord], query: SearchQuery) -> list[PaperRecord]:
    for record in records:
        record.relevance_score = _relevance_score(record, query)
        record.recency_score = _recency_score(record.year)
        record.usability_score = _usability_score(record)
        record.classic_highly_cited = _is_classic_highly_cited(record)
        record.ranking_notes = _ranking_notes(record, query)
        record.total_score = round(
            record.relevance_score * 0.52
            + record.usability_score * 0.28
            + record.recency_score * 0.20
            + _citation_bonus(record),
            2,
        )
        record.caution = _caution(record)

    return sorted(
        records,
        key=lambda item: (
            item.total_score,
            item.doi != UNKNOWN,
            item.pdf_available,
            _is_recent(item.year),
            item.citation_count or 0,
            item.year or 0,
        ),
        reverse=True,
    )


def _relevance_score(record: PaperRecord, query: SearchQuery) -> float:
    required = query.required_keywords or query.keywords
    helpful = query.helpful_keywords
    if not required and not helpful:
        return 0.0

    score = 0.0
    max_score = max(len(required) * 70 + len(helpful) * 18, 1)
    title = record.title.lower()
    abstract = record.abstract.lower() if record.abstract != UNKNOWN else ""

    for keyword in required:
        keyword_lower = keyword.lower()
        if keyword_lower in title:
            score += 70
        elif keyword_lower in abstract:
            score += 42

    for keyword in helpful:
        keyword_lower = keyword.lower()
        if keyword_lower in title:
            score += 18
        elif keyword_lower in abstract:
            score += 11
        elif keyword_lower in _metadata_text(record):
            score += 6

    return round(min((score / max_score) * 100, 100.0), 2)


def _recency_score(year: int | None) -> float:
    if year is None:
        return 0.0
    age = max(CURRENT_YEAR - year, 0)
    if age <= RECENT_YEAR_WINDOW:
        return 100.0
    if age <= 10:
        return 60.0
    if age <= 20:
        return 35.0
    return 20.0


def _usability_score(record: PaperRecord) -> float:
    score = 0.0
    if record.doi != UNKNOWN:
        score += 34
    if record.pdf_available:
        score += 30
    if record.landing_page_url != UNKNOWN:
        score += 18
    if record.authors:
        score += 8
    if record.venue != UNKNOWN:
        score += 6
    if record.abstract != UNKNOWN:
        score += 4
    return min(score, 100.0)


def _citation_bonus(record: PaperRecord) -> float:
    if record.citation_count is None:
        return 0.0
    if _is_classic_highly_cited(record):
        return 8.0
    if record.citation_count >= 100:
        return 4.0
    if record.citation_count >= 30:
        return 2.0
    return 0.0


def _is_classic_highly_cited(record: PaperRecord) -> bool:
    if record.year is None or record.citation_count is None:
        return False
    return CURRENT_YEAR - record.year >= CLASSIC_MIN_AGE and record.citation_count >= CLASSIC_CITATION_THRESHOLD


def _is_recent(year: int | None) -> bool:
    if year is None:
        return False
    return CURRENT_YEAR - year <= RECENT_YEAR_WINDOW


def _ranking_notes(record: PaperRecord, query: SearchQuery) -> list[str]:
    notes: list[str] = []
    required = query.required_keywords or query.keywords
    title = record.title.lower()
    abstract = record.abstract.lower() if record.abstract != UNKNOWN else ""

    title_hits = [keyword for keyword in required if keyword.lower() in title]
    abstract_hits = [keyword for keyword in required if keyword.lower() in abstract]
    helpful_hits = [
        keyword
        for keyword in query.helpful_keywords
        if keyword.lower() in title or keyword.lower() in abstract or keyword.lower() in _metadata_text(record)
    ]

    if title_hits:
        notes.append(f"required title hit: {', '.join(title_hits)}")
    if abstract_hits:
        notes.append(f"required abstract hit: {', '.join(abstract_hits)}")
    if helpful_hits:
        notes.append(f"helpful keyword hit: {', '.join(helpful_hits)}")
    if record.doi != UNKNOWN:
        notes.append("DOI verified")
    if record.pdf_available:
        notes.append("direct PDF available")
    if _is_recent(record.year):
        notes.append("recent within 5 years")
    if record.classic_highly_cited:
        notes.append("highly cited classic")
    return notes


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
    if record.abstract == UNKNOWN:
        cautions.append("Abstract not available from source API")
    return "; ".join(cautions) if cautions else "No immediate metadata caution"


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _title_and_abstract(record: PaperRecord) -> str:
    return " ".join([record.title, "" if record.abstract == UNKNOWN else record.abstract])


def _metadata_text(record: PaperRecord) -> str:
    return " ".join([record.title, record.venue, record.publisher_or_institution]).lower()
