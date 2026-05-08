from __future__ import annotations

import re

from scholarcheck.http import JsonHttpClient
from scholarcheck.domestic import build_domestic_links
from scholarcheck.keywords import extract_keywords
from scholarcheck.models import PaperRecord, SearchQuery, SearchResult, UNKNOWN
from scholarcheck.scoring import apply_scores
from scholarcheck.sources import CrossrefSource, OpenAlexSource


def build_query(
    topic: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
) -> SearchQuery:
    return SearchQuery(
        topic=topic.strip(),
        keywords=extract_keywords(topic),
        year_from=year_from,
        year_to=year_to,
        limit=limit,
    )


def search_papers(query: SearchQuery) -> SearchResult:
    client = JsonHttpClient()
    sources = [
        CrossrefSource(client),
        OpenAlexSource(client),
    ]

    records: list[PaperRecord] = []
    errors: list[str] = []
    for source in sources:
        try:
            records.extend(source.search(query))
        except RuntimeError as exc:
            errors.append(str(exc))

    deduped = deduplicate(records)
    scored = apply_scores(deduped, query)
    if errors:
        for record in scored:
            record.caution = f"{record.caution}; Source warning: {' | '.join(errors)}"
    return SearchResult(
        records=scored[: query.limit],
        domestic_links=build_domestic_links(query),
        warnings=errors,
    )


def deduplicate(records: list[PaperRecord]) -> list[PaperRecord]:
    seen: set[str] = set()
    deduped: list[PaperRecord] = []

    for record in records:
        key = _dedupe_key(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)

    return deduped


def _dedupe_key(record: PaperRecord) -> str:
    if record.doi != UNKNOWN:
        return f"doi:{record.doi.lower()}"
    title = re.sub(r"\s+", " ", record.title.lower()).strip()
    year = record.year or "unknown"
    return f"title:{title}:{year}"
