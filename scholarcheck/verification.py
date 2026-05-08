from __future__ import annotations

from urllib.parse import quote

from scholarcheck.http import JsonHttpClient
from scholarcheck.models import DoiVerificationResult, PaperRecord, UNKNOWN
from scholarcheck.sources import _first_text


def verify_doi_with_crossref(
    paper: PaperRecord,
    client: JsonHttpClient | None = None,
) -> DoiVerificationResult:
    if paper.doi == UNKNOWN or not paper.doi.strip():
        return DoiVerificationResult(
            status="missing",
            message="DOI가 없어 Crossref 재검증을 수행하지 않았습니다.",
        )

    http_client = client or JsonHttpClient()
    try:
        data = http_client.get_json(f"https://api.crossref.org/works/{quote(paper.doi)}")
    except RuntimeError as exc:
        return DoiVerificationResult(
            status="error",
            message=f"Crossref DOI 재검증 실패: {exc}",
            doi=paper.doi,
        )

    message = data.get("message", {})
    if not isinstance(message, dict):
        return DoiVerificationResult(
            status="not_found",
            message="Crossref 응답에서 DOI 메타데이터를 확인하지 못했습니다.",
            doi=paper.doi,
        )

    verified_doi = str(message.get("DOI", "")).strip().lower() or UNKNOWN
    if verified_doi == UNKNOWN:
        return DoiVerificationResult(
            status="not_found",
            message="Crossref 응답에 DOI 값이 없습니다.",
            doi=paper.doi,
        )

    return DoiVerificationResult(
        status="verified" if verified_doi == paper.doi.lower() else "mismatch",
        message="Crossref에서 DOI 메타데이터를 확인했습니다."
        if verified_doi == paper.doi.lower()
        else "Crossref DOI가 현재 논문 DOI와 다릅니다.",
        doi=verified_doi,
        title=_first_text(message.get("title")),
        publisher=str(message.get("publisher", "")).strip() or UNKNOWN,
        landing_page_url=str(message.get("URL", "")).strip() or UNKNOWN,
    )
