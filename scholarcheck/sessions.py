from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from scholarcheck.models import DomesticSearchLink, PaperRecord, SearchQuery, SearchResult, UNKNOWN


DEFAULT_SESSION_DIR = Path("data") / "sessions"


def save_search_session(
    query: SearchQuery,
    result: SearchResult,
    session_dir: Path = DEFAULT_SESSION_DIR,
) -> Path:
    session_dir.mkdir(parents=True, exist_ok=True)
    saved_at = datetime.now(timezone.utc).isoformat()
    session_id = _build_session_id(query.topic, saved_at)
    path = session_dir / f"{session_id}.json"
    path.write_text(
        json.dumps(_session_payload(session_id, saved_at, query, result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_search_session(path: Path) -> tuple[dict[str, str], SearchQuery, SearchResult]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    query = _query_from_payload(payload.get("query", {}))
    result = SearchResult(
        records=[_paper_from_payload(item) for item in payload.get("records", []) if isinstance(item, dict)],
        domestic_links=[
            _domestic_link_from_payload(item)
            for item in payload.get("domestic_db_direct_check_required", [])
            if isinstance(item, dict)
        ],
        warnings=[str(item) for item in payload.get("warnings", [])],
        relaxation_suggestions=[str(item) for item in payload.get("relaxation_suggestions", [])],
    )
    metadata = {
        "schema_version": str(payload.get("schema_version", "1")),
        "session_id": str(payload.get("session_id", path.stem)),
        "saved_at": str(payload.get("saved_at", UNKNOWN)),
    }
    return metadata, query, result


def list_search_sessions(session_dir: Path = DEFAULT_SESSION_DIR) -> list[Path]:
    if not session_dir.exists():
        return []
    return sorted(session_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def resolve_session_path(session_id: str, session_dir: Path = DEFAULT_SESSION_DIR) -> Path:
    safe_id = re.sub(r"[^0-9A-Za-z_.-]", "", session_id)
    if not safe_id:
        raise ValueError("Session id is required.")
    path = session_dir / f"{safe_id}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _session_payload(
    session_id: str,
    saved_at: str,
    query: SearchQuery,
    result: SearchResult,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "session_id": session_id,
        "saved_at": saved_at,
        "query": asdict(query),
        "records": [asdict(record) for record in result.records],
        "domestic_db_direct_check_required": [asdict(link) for link in result.domestic_links],
        "warnings": result.warnings,
        "relaxation_suggestions": result.relaxation_suggestions,
    }


def _build_session_id(topic: str, saved_at: str) -> str:
    timestamp = saved_at.replace("-", "").replace(":", "").split(".")[0].replace("+", "Z")
    slug = re.sub(r"[^0-9A-Za-z]+", "-", topic.strip().lower()).strip("-")[:48]
    return f"{timestamp}-{slug or 'search'}"


def _query_from_payload(data: dict[str, object]) -> SearchQuery:
    return SearchQuery(
        topic=str(data.get("topic", UNKNOWN)),
        keywords=_list_of_strings(data.get("keywords")),
        required_keywords=_list_of_strings(data.get("required_keywords")),
        helpful_keywords=_list_of_strings(data.get("helpful_keywords")),
        excluded_keywords=_list_of_strings(data.get("excluded_keywords")),
        year_from=_optional_int(data.get("year_from")),
        year_to=_optional_int(data.get("year_to")),
        limit=_optional_int(data.get("limit")) or 10,
    )


def _paper_from_payload(data: dict[str, object]) -> PaperRecord:
    return PaperRecord(
        title=str(data.get("title", UNKNOWN)),
        authors=_list_of_strings(data.get("authors")),
        year=_optional_int(data.get("year")),
        venue=str(data.get("venue", UNKNOWN)),
        publisher_or_institution=str(data.get("publisher_or_institution", UNKNOWN)),
        doi=str(data.get("doi", UNKNOWN)),
        landing_page_url=str(data.get("landing_page_url", UNKNOWN)),
        pdf_url=str(data.get("pdf_url", UNKNOWN)),
        pdf_available=bool(data.get("pdf_available", False)),
        open_access=_optional_bool(data.get("open_access")),
        abstract=str(data.get("abstract", UNKNOWN)),
        citation_count=_optional_int(data.get("citation_count")),
        region=str(data.get("region", UNKNOWN)),
        relevance_score=float(data.get("relevance_score", 0.0) or 0.0),
        recency_score=float(data.get("recency_score", 0.0) or 0.0),
        usability_score=float(data.get("usability_score", 0.0) or 0.0),
        total_score=float(data.get("total_score", 0.0) or 0.0),
        classic_highly_cited=bool(data.get("classic_highly_cited", False)),
        ranking_notes=_list_of_strings(data.get("ranking_notes")),
        caution=str(data.get("caution", "")),
        source_api=str(data.get("source_api", UNKNOWN)),
        verified_fields=_list_of_strings(data.get("verified_fields")),
    )


def _domestic_link_from_payload(data: dict[str, object]) -> DomesticSearchLink:
    return DomesticSearchLink(
        database_name=str(data.get("database_name", UNKNOWN)),
        search_keywords=str(data.get("search_keywords", UNKNOWN)),
        search_url=str(data.get("search_url", UNKNOWN)),
        result_status=str(data.get("result_status", "국내 DB 직접 확인 필요")),
        download_status=str(data.get("download_status", "확인 불가 / 기관접속 필요 가능성 있음")),
        caution=str(data.get("caution", "")),
    )


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)
