from __future__ import annotations

import re
from dataclasses import dataclass

from scholarcheck.http import JsonHttpClient
from scholarcheck.models import PaperRecord, SearchQuery, UNKNOWN


def _first_text(value: object) -> str:
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return UNKNOWN


def _clean_text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return UNKNOWN
    cleaned = value.strip()
    if cleaned.lower() in {"none", "null", "unknown", "n/a", "na"}:
        return UNKNOWN
    return cleaned


def _clean_abstract(value: object) -> str:
    text = _clean_text(value)
    if text == UNKNOWN:
        return UNKNOWN
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or UNKNOWN


def _abstract_from_inverted_index(value: object) -> str:
    if not isinstance(value, dict):
        return UNKNOWN

    positioned_words: list[tuple[int, str]] = []
    for word, positions in value.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            try:
                positioned_words.append((int(position), word))
            except (TypeError, ValueError):
                continue

    if not positioned_words:
        return UNKNOWN
    return " ".join(word for _, word in sorted(positioned_words))


def _year_from_parts(parts: object) -> int | None:
    if not isinstance(parts, dict):
        return None
    date_parts = parts.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts:
        return None
    first = date_parts[0]
    if not isinstance(first, list) or not first:
        return None
    try:
        return int(first[0])
    except (TypeError, ValueError):
        return None


def _normalize_doi(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return UNKNOWN
    normalized = value.strip().lower()
    if normalized in {"none", "null", "unknown", "n/a", "na"}:
        return UNKNOWN
    return normalized


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _author_names_crossref(authors: object) -> list[str]:
    if not isinstance(authors, list):
        return []

    names: list[str] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        given = str(author.get("given", "")).strip()
        family = str(author.get("family", "")).strip()
        name = " ".join(part for part in [given, family] if part)
        if not name:
            name = str(author.get("name", "")).strip()
        if name:
            names.append(name)
    return names


def _author_names_openalex(authorships: object) -> list[str]:
    if not isinstance(authorships, list):
        return []

    names: list[str] = []
    for authorship in authorships:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author")
        if not isinstance(author, dict):
            continue
        name = str(author.get("display_name", "")).strip()
        if name:
            names.append(name)
    return names


def classify_region(record: PaperRecord) -> str:
    text = " ".join(
        [
            record.title,
            record.venue,
            record.publisher_or_institution,
            record.landing_page_url,
        ]
    ).lower()

    domestic_markers = [
        ".kr",
        "korea",
        "korean",
        "대한",
        "한국",
        "학회",
        "대학교",
        "riss",
        "kci",
        "dbpia",
        "kiss",
    ]
    if any(marker in text for marker in domestic_markers):
        return "domestic"
    return "international"


@dataclass(slots=True)
class CrossrefSource:
    client: JsonHttpClient

    def search(self, query: SearchQuery) -> list[PaperRecord]:
        params: dict[str, str | int] = {
            "query.bibliographic": query.topic,
            "rows": min(query.limit * 4, 100),
            "select": "title,author,published-print,published-online,published,container-title,publisher,DOI,URL,link,type,abstract,is-referenced-by-count",
        }
        filters: list[str] = ["type:journal-article"]
        if query.year_from:
            filters.append(f"from-pub-date:{query.year_from}")
        if query.year_to:
            filters.append(f"until-pub-date:{query.year_to}")
        params["filter"] = ",".join(filters)

        data = self.client.get_json("https://api.crossref.org/works", params)
        items = data.get("message", {}).get("items", [])
        if not isinstance(items, list):
            return []

        records: list[PaperRecord] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            record = self._from_item(item)
            record.region = classify_region(record)
            records.append(record)
        return records

    def _from_item(self, item: dict) -> PaperRecord:
        year = (
            _year_from_parts(item.get("published-print"))
            or _year_from_parts(item.get("published-online"))
            or _year_from_parts(item.get("published"))
        )
        doi = _normalize_doi(item.get("DOI"))
        landing_page_url = _clean_text(item.get("URL"))
        abstract = _clean_abstract(item.get("abstract"))
        citation_count = _int_or_none(item.get("is-referenced-by-count"))

        pdf_url = UNKNOWN
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if not isinstance(link, dict):
                    continue
                content_type = str(link.get("content-type", "")).lower()
                url = _clean_text(link.get("URL"))
                if url != UNKNOWN and "pdf" in content_type:
                    pdf_url = url
                    break

        verified_fields = ["title", "source_api"]
        for field_name, value in [
            ("authors", item.get("author")),
            ("year", year),
            ("venue", item.get("container-title")),
            ("publisher_or_institution", item.get("publisher")),
            ("doi", doi),
            ("landing_page_url", landing_page_url),
            ("abstract", abstract),
            ("citation_count", citation_count),
        ]:
            if value and value != UNKNOWN:
                verified_fields.append(field_name)

        return PaperRecord(
            title=_first_text(item.get("title")),
            authors=_author_names_crossref(item.get("author")),
            year=year,
            venue=_first_text(item.get("container-title")),
            publisher_or_institution=_clean_text(item.get("publisher")),
            doi=doi,
            landing_page_url=landing_page_url,
            pdf_url=pdf_url,
            pdf_available=pdf_url != UNKNOWN,
            abstract=abstract,
            citation_count=citation_count,
            source_api="Crossref",
            verified_fields=verified_fields,
        )


@dataclass(slots=True)
class OpenAlexSource:
    client: JsonHttpClient

    def search(self, query: SearchQuery) -> list[PaperRecord]:
        params: dict[str, str | int] = {
            "search": query.topic,
            "per-page": min(query.limit * 4, 100),
            "mailto": "foruniquelife@gmail.com",
        }
        filters: list[str] = ["type:article"]
        if query.year_from:
            filters.append(f"from_publication_date:{query.year_from}-01-01")
        if query.year_to:
            filters.append(f"to_publication_date:{query.year_to}-12-31")
        params["filter"] = ",".join(filters)

        data = self.client.get_json("https://api.openalex.org/works", params)
        results = data.get("results", [])
        if not isinstance(results, list):
            return []

        records: list[PaperRecord] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            record = self._from_item(item)
            record.region = classify_region(record)
            records.append(record)
        return records

    def _from_item(self, item: dict) -> PaperRecord:
        doi = _clean_text(item.get("doi"))
        if doi.startswith("https://doi.org/"):
            doi = doi.removeprefix("https://doi.org/")
        doi = _normalize_doi(doi)

        primary_location = item.get("primary_location")
        landing_page_url = UNKNOWN
        pdf_url = UNKNOWN
        venue = UNKNOWN
        publisher = UNKNOWN

        if isinstance(primary_location, dict):
            landing_page_url = _clean_text(primary_location.get("landing_page_url"))
            pdf_url = _clean_text(primary_location.get("pdf_url"))
            source = primary_location.get("source")
            if isinstance(source, dict):
                venue = _clean_text(source.get("display_name"))
                publisher = _clean_text(source.get("host_organization_name"))

        abstract = _abstract_from_inverted_index(item.get("abstract_inverted_index"))
        citation_count = _int_or_none(item.get("cited_by_count"))

        verified_fields = ["title", "source_api"]
        for field_name, value in [
            ("authors", item.get("authorships")),
            ("year", item.get("publication_year")),
            ("venue", venue),
            ("publisher_or_institution", publisher),
            ("doi", doi),
            ("landing_page_url", landing_page_url),
            ("abstract", abstract),
            ("citation_count", citation_count),
        ]:
            if value and value != UNKNOWN:
                verified_fields.append(field_name)

        year = _int_or_none(item.get("publication_year"))

        return PaperRecord(
            title=_clean_text(item.get("title")),
            authors=_author_names_openalex(item.get("authorships")),
            year=year,
            venue=venue,
            publisher_or_institution=publisher,
            doi=doi,
            landing_page_url=landing_page_url,
            pdf_url=pdf_url,
            pdf_available=pdf_url != UNKNOWN,
            abstract=abstract,
            citation_count=citation_count,
            source_api="OpenAlex",
            verified_fields=verified_fields,
        )
