from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from scholarcheck.models import PaperRecord


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
    "region",
    "relevance_score",
    "recency_score",
    "usability_score",
    "total_score",
    "caution",
    "source_api",
    "verified_fields",
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
                _trim(record.title, 46),
                _trim(record.authors_display, 28),
                record.year_display,
                _trim(record.venue, 24),
                record.doi,
                "Y" if record.pdf_available else "N",
                record.region,
                f"{record.total_score:.2f}",
            ]
        )

    headers = ["#", "Title", "Authors", "Year", "Venue", "DOI", "PDF", "Region", "Score"]
    widths = [
        max(len(str(row[column])) for row in [headers, *rows])
        for column in range(len(headers))
    ]

    print(_format_row(headers, widths))
    print(_format_row(["-" * width for width in widths], widths))
    for row in rows:
        print(_format_row(row, widths))


def save_records(records: list[PaperRecord], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        _save_json(records, path)
        return path
    if path.suffix.lower() == ".csv":
        _save_csv(records, path)
        return path
    raise ValueError("Output path must end with .csv or .json")


def _save_csv(records: list[PaperRecord], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in records:
            writer.writerow(_record_to_row(record))


def _save_json(records: list[PaperRecord], path: Path) -> None:
    payload = []
    for record in records:
        data = asdict(record)
        data["authors"] = record.authors
        payload.append(data)

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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
        "region": record.region,
        "relevance_score": record.relevance_score,
        "recency_score": record.recency_score,
        "usability_score": record.usability_score,
        "total_score": record.total_score,
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
