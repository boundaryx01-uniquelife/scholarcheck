from __future__ import annotations

from dataclasses import dataclass, field


UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class SearchQuery:
    topic: str
    keywords: list[str]
    required_keywords: list[str] = field(default_factory=list)
    helpful_keywords: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
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
    abstract: str = UNKNOWN
    citation_count: int | None = None
    region: str = UNKNOWN
    relevance_score: float = 0.0
    recency_score: float = 0.0
    usability_score: float = 0.0
    total_score: float = 0.0
    classic_highly_cited: bool = False
    ranking_notes: list[str] = field(default_factory=list)
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

    @property
    def citation_display(self) -> str:
        if self.citation_count is None:
            return UNKNOWN
        return str(self.citation_count)


@dataclass(slots=True)
class DomesticSearchLink:
    database_name: str
    search_keywords: str
    search_url: str
    result_status: str = "국내 DB 직접 확인 필요"
    download_status: str = "확인 불가 / 기관접속 필요 가능성 있음"
    caution: str = "자동 크롤링하지 않음. 링크에서 사용자가 직접 논문 존재 여부와 원문 접근 권한을 확인해야 함."


@dataclass(slots=True)
class SearchResult:
    records: list[PaperRecord]
    domestic_links: list[DomesticSearchLink] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    relaxation_suggestions: list[str] = field(default_factory=list)
