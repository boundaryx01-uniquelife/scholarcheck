from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from scholarcheck.models import DomesticManualCheck, UNKNOWN


DEFAULT_STORE_PATH = Path("data") / "domestic_manual_checks.json"


def load_manual_checks(path: Path = DEFAULT_STORE_PATH) -> list[DomesticManualCheck]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    checks: list[DomesticManualCheck] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        checks.append(
            DomesticManualCheck(
                database_name=str(item.get("database_name", "")).strip() or UNKNOWN,
                search_keywords=str(item.get("search_keywords", "")).strip() or UNKNOWN,
                title=str(item.get("title", "")).strip() or UNKNOWN,
                landing_page_url=str(item.get("landing_page_url", "")).strip() or UNKNOWN,
                doi=str(item.get("doi", "")).strip() or UNKNOWN,
                pdf_status=str(item.get("pdf_status", "")).strip()
                or "확인 불가 / 기관접속 필요 가능성 있음",
                notes=str(item.get("notes", "")).strip(),
                checked_at=str(item.get("checked_at", "")).strip(),
            )
        )
    return checks


def add_manual_check(
    check: DomesticManualCheck,
    path: Path = DEFAULT_STORE_PATH,
) -> DomesticManualCheck:
    path.parent.mkdir(parents=True, exist_ok=True)
    checks = load_manual_checks(path)
    if not check.checked_at:
        check.checked_at = datetime.now(timezone.utc).isoformat()
    checks.append(check)
    path.write_text(
        json.dumps([asdict(item) for item in checks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return check
