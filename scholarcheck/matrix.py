from __future__ import annotations

from dataclasses import dataclass

from scholarcheck.models import PaperRecord, UNKNOWN


NEEDS_REVIEW = "[확인 필요]"
MATRIX_NOTICE = (
    "선행연구 매트릭스 초안입니다. ScholarCheck는 논문 내용을 임의로 요약하지 않으며, "
    "연구방법, 연구대상, 주요결과는 원문 확인 후 사용자가 직접 보완해야 합니다."
)


@dataclass(slots=True)
class LiteratureMatrixRow:
    title: str
    authors: str
    year: str
    venue: str
    doi: str
    source_url: str
    research_purpose: str
    research_method: str
    research_subjects: str
    key_findings: str
    relevance_note: str
    user_memo: str
    verification_note: str


def build_literature_matrix(records: list[PaperRecord]) -> list[LiteratureMatrixRow]:
    return [_row_from_record(record) for record in records]


def _row_from_record(record: PaperRecord) -> LiteratureMatrixRow:
    return LiteratureMatrixRow(
        title=record.title,
        authors=record.authors_display,
        year=record.year_display,
        venue=record.venue,
        doi=record.doi,
        source_url=record.landing_page_url,
        research_purpose=NEEDS_REVIEW,
        research_method=NEEDS_REVIEW,
        research_subjects=NEEDS_REVIEW,
        key_findings=NEEDS_REVIEW,
        relevance_note=_relevance_note(record),
        user_memo="",
        verification_note=_verification_note(record),
    )


def _relevance_note(record: PaperRecord) -> str:
    notes = "; ".join(record.ranking_notes)
    if notes:
        return notes
    if record.total_score:
        return f"자동 관련성 점수 {record.total_score:.2f}"
    return NEEDS_REVIEW


def _verification_note(record: PaperRecord) -> str:
    missing = []
    if record.title == UNKNOWN:
        missing.append("제목")
    if record.authors_display == UNKNOWN:
        missing.append("저자")
    if record.year_display == UNKNOWN:
        missing.append("연도")
    if record.venue == UNKNOWN:
        missing.append("학술지/기관")
    if record.doi == UNKNOWN:
        missing.append("DOI")
    if record.landing_page_url == UNKNOWN:
        missing.append("원문 URL")
    if not missing:
        return "메타데이터 후보 확인됨. 최종 인용 전 원문 대조 필요."
    return f"{', '.join(missing)} {NEEDS_REVIEW}"
