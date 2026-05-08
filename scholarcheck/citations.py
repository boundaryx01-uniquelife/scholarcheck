from __future__ import annotations

from dataclasses import dataclass

from scholarcheck.models import PaperRecord, UNKNOWN


CITATION_NOTICE = (
    "참고문헌 후보안입니다. 최종 확정 인용이 아니며, 최종 인용 전 원문 페이지에서 "
    "제목, 저자, 학술지, 연도, DOI, 권호, 페이지를 직접 확인해야 합니다."
)


@dataclass(slots=True)
class CitationCandidate:
    title: str
    reference: str
    warnings: list[str]


def build_reference_candidates(records: list[PaperRecord]) -> list[CitationCandidate]:
    return [_candidate_from_record(record) for record in records]


def _candidate_from_record(record: PaperRecord) -> CitationCandidate:
    warnings = _warnings_for_record(record)
    reference = _format_candidate(record)
    return CitationCandidate(
        title=record.title,
        reference=reference,
        warnings=warnings,
    )


def _format_candidate(record: PaperRecord) -> str:
    authors = _authors_for_reference(record)
    year = record.year_display
    title = record.title
    venue = record.venue
    suffix = _reference_suffix(record)
    return f"{authors} ({year}). {title}. {venue}.{suffix}"


def _authors_for_reference(record: PaperRecord) -> str:
    if not record.authors:
        return UNKNOWN
    if len(record.authors) == 1:
        return record.authors[0]
    if len(record.authors) <= 20:
        return ", ".join(record.authors[:-1]) + f", & {record.authors[-1]}"
    return ", ".join(record.authors[:19]) + f", ... {record.authors[-1]}"


def _reference_suffix(record: PaperRecord) -> str:
    if record.doi != UNKNOWN:
        return f" https://doi.org/{record.doi}"
    if record.landing_page_url != UNKNOWN:
        return f" {record.landing_page_url}"
    return ""


def _warnings_for_record(record: PaperRecord) -> list[str]:
    warnings = [CITATION_NOTICE]
    if record.authors_display == UNKNOWN:
        warnings.append("저자 정보가 확인되지 않았습니다.")
    if record.year_display == UNKNOWN:
        warnings.append("출판연도가 확인되지 않았습니다.")
    if record.venue == UNKNOWN:
        warnings.append("학술지/학회/기관 정보가 확인되지 않았습니다.")
    if record.doi == UNKNOWN:
        warnings.append("DOI가 확인되지 않았습니다. 임의 DOI를 만들지 않았습니다.")
    if record.landing_page_url == UNKNOWN:
        warnings.append("원문 페이지 URL이 확인되지 않았습니다.")
    return warnings
