from __future__ import annotations

import re

from scholarcheck.domestic import build_domestic_links
from scholarcheck.http import JsonHttpClient
from scholarcheck.keywords import extract_keywords
from scholarcheck.models import PaperRecord, SearchQuery, SearchResult, UNKNOWN
from scholarcheck.scoring import filter_and_score
from scholarcheck.sources import CrossrefSource, OpenAlexSource


def build_query(
    topic: str,
    *,
    required_keywords: list[str] | None = None,
    helpful_keywords: list[str] | None = None,
    excluded_keywords: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
) -> SearchQuery:
    extracted_keywords = extract_keywords(topic)
    required = _normalize_keywords(required_keywords) or extracted_keywords
    helpful = _normalize_keywords(helpful_keywords)
    excluded = _normalize_keywords(excluded_keywords)

    return SearchQuery(
        topic=topic.strip(),
        keywords=extracted_keywords,
        required_keywords=required,
        helpful_keywords=helpful,
        excluded_keywords=excluded,
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
    scored = filter_and_score(deduped, query)
    if errors:
        for record in scored:
            record.caution = f"{record.caution}; Source warning: {' | '.join(errors)}"

    selected = scored[: query.limit]
    return SearchResult(
        records=selected,
        domestic_links=build_domestic_links(query),
        warnings=errors,
        relaxation_suggestions=build_relaxation_suggestions(query, len(selected)),
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


def build_relaxation_suggestions(query: SearchQuery, result_count: int) -> list[str]:
    if result_count >= query.limit:
        return []

    suggestions = [
        f"현재 {result_count}건만 확인되었습니다. 가짜 결과는 생성하지 않았습니다.",
    ]
    if query.excluded_keywords:
        suggestions.append("제외 키워드를 줄이거나 잠시 비워서 다시 검색해 보세요.")
    if len(query.required_keywords) > 2:
        suggestions.append("필수 키워드를 1~2개 핵심어로 줄이고 나머지는 도움 키워드로 옮겨 보세요.")
    if query.year_from:
        suggestions.append("시작 연도를 더 이전으로 넓혀 보세요.")
    if not query.helpful_keywords and len(query.keywords) > 2:
        suggestions.append("주제 문장에서 핵심 필수 키워드와 보조 키워드를 분리해 보세요.")
    suggestions.append("국내 자료는 아래 국내 DB 직접 확인 링크에서 별도로 확인해 보세요.")
    return suggestions


def parse_keyword_argument(raw: str | None) -> list[str]:
    if not raw:
        return []
    return _normalize_keywords(re.split(r"[,;\n]", raw))


def _normalize_keywords(keywords: list[str] | None) -> list[str]:
    if not keywords:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        cleaned = re.sub(r"\s+", " ", keyword.strip())
        key = cleaned.lower()
        if cleaned and key not in seen:
            normalized.append(cleaned)
            seen.add(key)
    return normalized


def _dedupe_key(record: PaperRecord) -> str:
    if record.doi != UNKNOWN:
        return f"doi:{record.doi.lower()}"
    title = _normalize_title_for_dedupe(record.title)
    year = record.year or "unknown"
    return f"title:{title}:{year}"


def _normalize_title_for_dedupe(title: str) -> str:
    normalized = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", title.lower())
    return re.sub(r"\s+", " ", normalized).strip()
