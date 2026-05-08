from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from pathlib import Path

from scholarcheck.models import DomesticSearchLink, PaperRecord


FIELDNAMES = [
    "title",
    "authors",
    "year",
    "venue",
    "publisher_or_institution",
    "doi",
    "landing_page_url",
    "pdf_available",
    "pdf_url",
    "open_access",
    "region",
    "citation_count",
    "classic_highly_cited",
    "relevance_score",
    "recency_score",
    "usability_score",
    "total_score",
    "ranking_notes",
    "caution",
    "source_api",
    "verified_fields",
]

DOMESTIC_FIELDNAMES = [
    "database_name",
    "search_keywords",
    "search_url",
    "result_status",
    "download_status",
    "caution",
]


def print_table(records: list[PaperRecord]) -> None:
    if not records:
        print("No verified records found.")
        return

    rows = []
    for index, record in enumerate(records, start=1):
        rows.append(
            [
                str(index),
                _trim(record.title, 42),
                _trim(record.authors_display, 24),
                record.year_display,
                record.doi,
                "Y" if record.pdf_available else "N",
                record.citation_display,
                "Y" if record.classic_highly_cited else "N",
                f"{record.total_score:.2f}",
                _trim("; ".join(record.ranking_notes), 38),
            ]
        )

    headers = ["#", "Title", "Authors", "Year", "DOI", "PDF", "Cites", "Classic", "Score", "Why"]
    widths = [
        max(len(str(row[column])) for row in [headers, *rows])
        for column in range(len(headers))
    ]

    print(_format_row(headers, widths))
    print(_format_row(["-" * width for width in widths], widths))
    for row in rows:
        print(_format_row(row, widths))


def print_relaxation_suggestions(suggestions: list[str]) -> None:
    if not suggestions:
        return
    print("검색 조건 완화 제안")
    for suggestion in suggestions:
        print(f"- {suggestion}")


def print_domestic_links(links: list[DomesticSearchLink]) -> None:
    print("국내 DB 직접 확인 필요")
    if not links:
        print("No domestic database links generated.")
        return

    headers = ["DB", "Keywords", "Download", "URL"]
    rows = [
        [
            link.database_name,
            _trim(link.search_keywords, 30),
            link.download_status,
            link.search_url,
        ]
        for link in links
    ]
    widths = [
        max(len(str(row[column])) for row in [headers, *rows])
        for column in range(len(headers))
    ]

    print(_format_row(headers, widths))
    print(_format_row(["-" * width for width in widths], widths))
    for row in rows:
        print(_format_row(row, widths))


def save_records(
    records: list[PaperRecord],
    path: Path,
    domestic_links: list[DomesticSearchLink] | None = None,
    relaxation_suggestions: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(
            records_to_json(records, domestic_links or [], relaxation_suggestions or []),
            encoding="utf-8",
        )
        return path
    if path.suffix.lower() == ".csv":
        path.write_text(records_to_csv(records), encoding="utf-8-sig", newline="")
        if domestic_links is not None:
            _domestic_csv_path(path).write_text(
                domestic_links_to_csv(domestic_links),
                encoding="utf-8-sig",
                newline="",
            )
        if relaxation_suggestions:
            _save_suggestions_txt(relaxation_suggestions, _suggestions_txt_path(path))
        return path
    raise ValueError("Output path must end with .csv or .json")


def records_to_csv(records: list[PaperRecord]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDNAMES)
    writer.writeheader()
    for record in records:
        writer.writerow(_record_to_row(record))
    return output.getvalue()


def domestic_links_to_csv(links: list[DomesticSearchLink]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=DOMESTIC_FIELDNAMES)
    writer.writeheader()
    for link in links:
        writer.writerow(asdict(link))
    return output.getvalue()


def records_to_json(
    records: list[PaperRecord],
    domestic_links: list[DomesticSearchLink],
    relaxation_suggestions: list[str],
) -> str:
    verified_records = []
    for record in records:
        data = asdict(record)
        data["authors"] = record.authors
        verified_records.append(data)

    payload = {
        "verified_records": verified_records,
        "search_condition_relaxation_suggestions": relaxation_suggestions,
        "domestic_db_direct_check_required": [asdict(link) for link in domestic_links],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _save_suggestions_txt(suggestions: list[str], path: Path) -> None:
    path.write_text("\n".join(f"- {suggestion}" for suggestion in suggestions), encoding="utf-8")


def _record_to_row(record: PaperRecord) -> dict[str, str | float | bool]:
    return {
        "title": record.title,
        "authors": record.authors_display,
        "year": record.year_display,
        "venue": record.venue,
        "publisher_or_institution": record.publisher_or_institution,
        "doi": record.doi,
        "landing_page_url": record.landing_page_url,
        "pdf_available": record.pdf_available,
        "pdf_url": record.pdf_url,
        "open_access": record.open_access_display,
        "region": record.region,
        "citation_count": record.citation_display,
        "classic_highly_cited": record.classic_highly_cited,
        "relevance_score": record.relevance_score,
        "recency_score": record.recency_score,
        "usability_score": record.usability_score,
        "total_score": record.total_score,
        "ranking_notes": "; ".join(record.ranking_notes),
        "caution": record.caution,
        "source_api": record.source_api,
        "verified_fields": "; ".join(record.verified_fields),
    }


def _format_row(values: list[str], widths: list[int]) -> str:
    return " | ".join(value.ljust(width) for value, width in zip(values, widths, strict=True))


def _trim(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}..."


def _domestic_csv_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_domestic_links.csv")


def _suggestions_txt_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}_relaxation_suggestions.txt")
