from __future__ import annotations

from scholarcheck.models import CitationChecklistItem, PaperRecord, UNKNOWN


def build_citation_checklist(paper: PaperRecord) -> list[CitationChecklistItem]:
    return [
        _item("제목 확인", paper.title != UNKNOWN, paper.title),
        _item("저자 확인", bool(paper.authors), paper.authors_display),
        _item("출판연도 확인", paper.year is not None, paper.year_display),
        _item("학술지/기관 확인", paper.venue != UNKNOWN, paper.venue),
        _item("DOI 확인", paper.doi != UNKNOWN, paper.doi),
        _item("원문 페이지 확인", paper.landing_page_url != UNKNOWN, paper.landing_page_url),
        _item(
            "PDF 직접 가능 여부",
            paper.pdf_available,
            paper.pdf_url if paper.pdf_available else "확인 불가 / 기관접속 필요 가능성 있음",
        ),
        _item("초록 확인", paper.abstract != UNKNOWN, paper.abstract),
        _item("최종 인용 전 원문 대조", False, "사용자가 원문 페이지에서 서지정보를 직접 대조해야 함"),
    ]


def _item(label: str, ok: bool, detail: str) -> CitationChecklistItem:
    return CitationChecklistItem(
        label=label,
        status="확인됨" if ok else "확인 필요",
        detail=detail,
    )
