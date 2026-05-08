from __future__ import annotations

from dataclasses import dataclass, field


UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class SearchQuery:
    topic: str
    keywords: list[str]
    year_from: int | None = None
    year_to: int | None = None
    limit: int = 10


@dataclass(slots=True)
class PaperRecord:
    title: str = UNKNOWN
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str = UNKNOWN
    publisher_or_institution: str = UNKNOWN
    doi: str = UNKNOWN
    landing_page_url: str = UNKNOWN
    pdf_url: str = UNKNOWN
    pdf_available: bool = False
    region: str = UNKNOWN
    relevance_score: float = 0.0
    recency_score: float = 0.0
    usability_score: float = 0.0
    total_score: float = 0.0
    caution: str = ""
    source_api: str = UNKNOWN
    verified_fields: list[str] = field(default_factory=list)

    @property
    def authors_display(self) -> str:
        if not self.authors:
            return UNKNOWN
        return "; ".join(self.authors)

    @property
    def year_display(self) -> str:
        if self.year is None:
            return UNKNOWN
        return str(self.year)


@dataclass(slots=True)
class SearchResult:
    records: list[PaperRecord]
    warnings: list[str] = field(default_factory=list)
