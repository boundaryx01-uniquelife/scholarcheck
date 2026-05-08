from __future__ import annotations

import html

from scholarcheck.citations import build_reference_candidates
from scholarcheck.manual_checks import load_manual_checks
from scholarcheck.matrix import MATRIX_NOTICE, build_literature_matrix
from scholarcheck.models import DomesticManualCheck, SearchQuery, SearchResult, UNKNOWN


REPORT_NOTICE = (
    "ScholarCheck is an API-based metadata review aid. It does not finally guarantee paper existence, "
    "DOI correctness, or full-text access. Before citation, verify title, authors, venue, year, DOI, "
    "volume/issue, and pages on the original page."
)


def render_professor_report(
    metadata: dict[str, str],
    query: SearchQuery,
    result: SearchResult,
    manual_checks: list[DomesticManualCheck] | None = None,
) -> str:
    manual_checks = manual_checks if manual_checks is not None else load_manual_checks()
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>ScholarCheck Report - {_escape(query.topic)}</title>
  <style>
    body {{ margin:32px; color:#18212f; font-family:"Segoe UI","Malgun Gothic",Arial,sans-serif; line-height:1.5; }}
    h1 {{ margin:0 0 8px; font-size:30px; }}
    h2 {{ margin:28px 0 10px; font-size:20px; }}
    .meta,.notice {{ color:#526071; }}
    .notice {{ border:1px solid #8fc7bd; background:#edf7f5; padding:12px 14px; border-radius:6px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:13px; }}
    th,td {{ border:1px solid #d7dde8; padding:8px 10px; vertical-align:top; text-align:left; }}
    th {{ background:#eef2f6; }}
  </style>
</head>
<body>
  <h1>ScholarCheck Professor Review Report</h1>
  <p class="meta">Topic: {_escape(query.topic)} | Session: {_escape(metadata.get("session_id", UNKNOWN))} | Saved: {_escape(metadata.get("saved_at", UNKNOWN))}</p>
  <p class="notice">{_escape(REPORT_NOTICE)}</p>
  <h2>Search Conditions</h2>
  {_query_table(query)}
  <h2>Verified Overseas API Results</h2>
  {_records_table(result)}
  <h2>Reference Candidates</h2>
  {_citation_candidates_table(result)}
  <h2>Literature Review Matrix Draft</h2>
  <p class="notice">{_escape(MATRIX_NOTICE)}</p>
  {_literature_matrix_table(result)}
  <h2>Domestic DB Direct Check Required</h2>
  {_domestic_table(result)}
  <h2>Domestic Manual Check Records</h2>
  {_manual_checks_table(manual_checks)}
  <h2>Warnings And Relaxation Suggestions</h2>
  {_notes_list([*result.warnings, *result.relaxation_suggestions])}
</body>
</html>"""


def _query_table(query: SearchQuery) -> str:
    rows = [
        ("Required keywords", ", ".join(query.required_keywords) or UNKNOWN),
        ("Helpful keywords", ", ".join(query.helpful_keywords) or UNKNOWN),
        ("Excluded keywords", ", ".join(query.excluded_keywords) or UNKNOWN),
        ("Year range", f"{query.year_from or UNKNOWN} - {query.year_to or UNKNOWN}"),
        ("Limit", str(query.limit)),
    ]
    return _simple_table(["Field", "Value"], rows)


def _records_table(result: SearchResult) -> str:
    if not result.records:
        return "<p>No verified overseas API records were found. No fake records were generated.</p>"
    rows = []
    for record in result.records:
        rows.append(
            [
                record.title,
                record.authors_display,
                record.year_display,
                record.venue,
                record.doi,
                record.landing_page_url,
                "YES" if record.pdf_available else "확인 불가",
                record.pdf_url,
                record.open_access_display,
                record.citation_display,
                f"{record.total_score:.2f}",
                "YES" if record.classic_highly_cited else "NO",
            ]
        )
    return _simple_table(
        ["Title", "Authors", "Year", "Venue", "DOI", "Original URL", "PDF", "PDF URL", "OA", "Citations", "Score", "Classic"],
        rows,
    )


def _domestic_table(result: SearchResult) -> str:
    if not result.domestic_links:
        return "<p>No domestic DB links were generated.</p>"
    rows = [
        [link.database_name, link.search_keywords, link.result_status, link.download_status, link.search_url]
        for link in result.domestic_links
    ]
    return _simple_table(["DB", "Keywords", "Status", "Download", "Search URL"], rows)


def _citation_candidates_table(result: SearchResult) -> str:
    candidates = build_reference_candidates(result.records)
    if not candidates:
        return "<p>No reference candidates were generated. No fake citations were created.</p>"
    rows = [
        [candidate.title, candidate.reference, " | ".join(candidate.warnings)]
        for candidate in candidates
    ]
    return _simple_table(["Paper", "Reference Candidate", "Needs Review"], rows)


def _manual_checks_table(checks: list[DomesticManualCheck]) -> str:
    if not checks:
        return "<p>No domestic manual check records were saved.</p>"
    rows = [
        [check.database_name, check.search_keywords, check.title, check.doi, check.pdf_status, check.checked_at, check.notes]
        for check in checks
    ]
    return _simple_table(["DB", "Keywords", "Title", "DOI", "PDF", "Checked At", "Notes"], rows)


def _literature_matrix_table(result: SearchResult) -> str:
    rows = build_literature_matrix(result.records)
    if not rows:
        return "<p>No literature matrix rows were generated. No fake rows were created.</p>"
    return _simple_table(
        [
            "Title",
            "Authors",
            "Year",
            "Venue",
            "DOI",
            "Purpose",
            "Method",
            "Subjects",
            "Key Findings",
            "Relevance",
            "User Memo",
            "Verification",
        ],
        [
            [
                row.title,
                row.authors,
                row.year,
                row.venue,
                row.doi,
                row.research_purpose,
                row.research_method,
                row.research_subjects,
                row.key_findings,
                row.relevance_note,
                row.user_memo,
                row.verification_note,
            ]
            for row in rows
        ],
    )


def _notes_list(items: list[str]) -> str:
    if not items:
        return "<p>No warnings or relaxation suggestions.</p>"
    return f"<ul>{''.join(f'<li>{_escape(item)}</li>' for item in items)}</ul>"


def _simple_table(headers: list[str], rows: list[list[str] | tuple[str, ...]]) -> str:
    head = "".join(f"<th>{_escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_display(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _display(value: object) -> str:
    text = str(value).strip()
    if not text or text == UNKNOWN:
        return "확인 불가"
    if text.startswith("http://") or text.startswith("https://"):
        escaped = _escape(text)
        return f'<a href="{escaped}">{escaped}</a>'
    return _escape(text)


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
