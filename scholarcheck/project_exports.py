from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass

from scholarcheck.excel_export import (
    _content_types,
    _root_relationships,
    _worksheet_xml,
    _workbook_relationships,
    _workbook_xml,
)
from scholarcheck.manual_checks import load_manual_checks
from scholarcheck.models import DomesticManualCheck, PaperRecord, SearchQuery, SearchResult, UNKNOWN
from scholarcheck.projects import ResearchProject, load_project_sessions
from scholarcheck.reports import REPORT_NOTICE, _escape, _simple_table


PROJECT_EXPORT_NOTICE = (
    "Project exports combine linked saved sessions without changing the original session files. "
    "Duplicate papers are not deleted; they are marked only as duplicate candidates. "
    "Domestic manual check records remain separate from verified overseas API results."
)


@dataclass(slots=True)
class ProjectSessionSummary:
    session_id: str
    saved_at: str
    topic: str
    record_count: int
    domestic_link_count: int


@dataclass(slots=True)
class ProjectPaperRow:
    session_id: str
    topic: str
    paper: PaperRecord
    duplicate_candidate: str = "NO"
    duplicate_key: str = UNKNOWN


@dataclass(slots=True)
class ProjectExportData:
    project: ResearchProject
    sessions: list[ProjectSessionSummary]
    paper_rows: list[ProjectPaperRow]
    manual_checks: list[DomesticManualCheck]
    missing_session_ids: list[str]


def build_project_export_data(
    project: ResearchProject,
    manual_checks: list[DomesticManualCheck] | None = None,
) -> ProjectExportData:
    loaded_sessions = load_project_sessions(project)
    sessions: list[ProjectSessionSummary] = []
    paper_rows: list[ProjectPaperRow] = []

    for metadata, query, result in loaded_sessions:
        session_id = metadata.get("session_id", UNKNOWN)
        sessions.append(_session_summary(metadata, query, result))
        for paper in result.records:
            paper_rows.append(ProjectPaperRow(session_id=session_id, topic=query.topic, paper=paper))

    duplicate_keys = _duplicate_keys(paper_rows)
    for row in paper_rows:
        key = _paper_key(row.paper)
        row.duplicate_key = key
        if key in duplicate_keys:
            row.duplicate_candidate = "YES"

    loaded_ids = {item.session_id for item in sessions}
    missing_session_ids = [session_id for session_id in project.session_ids if session_id not in loaded_ids]

    return ProjectExportData(
        project=project,
        sessions=sessions,
        paper_rows=paper_rows,
        manual_checks=manual_checks if manual_checks is not None else load_manual_checks(),
        missing_session_ids=missing_session_ids,
    )


def render_project_html_report(data: ProjectExportData) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>ScholarCheck Project Report - {_escape(data.project.name)}</title>
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
  <h1>ScholarCheck Project Review Report</h1>
  <p class="meta">Project: {_escape(data.project.name)} | Project ID: {_escape(data.project.project_id)}</p>
  <p class="notice">{_escape(PROJECT_EXPORT_NOTICE)} {_escape(REPORT_NOTICE)}</p>
  <h2>Project Summary</h2>
  {_simple_table(["Field", "Value"], _project_summary_rows(data))}
  <h2>Linked Sessions</h2>
  {_sessions_table(data)}
  <h2>Integrated Verified Papers</h2>
  {_papers_table(data.paper_rows)}
  <h2>Duplicate Candidates</h2>
  {_duplicate_table(data)}
  <h2>Domestic Manual Check Records</h2>
  {_manual_checks_table(data.manual_checks)}
  <h2>Missing Sessions</h2>
  {_missing_sessions_table(data.missing_session_ids)}
</body>
</html>"""


def build_project_excel_workbook(data: ProjectExportData) -> bytes:
    sheets = [
        ("Summary", [["field", "value"], *_project_summary_rows(data)]),
        ("Sessions", _session_rows(data.sessions)),
        ("Integrated Papers", _integrated_paper_rows(data.paper_rows)),
        ("Duplicate Candidates", _duplicate_candidate_rows(data.paper_rows)),
        ("Manual Domestic Checks", _manual_check_rows(data.manual_checks)),
        ("Missing Sessions", _missing_session_rows(data.missing_session_ids)),
        ("Warnings", _warning_rows(data)),
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types(len(sheets)))
        package.writestr("_rels/.rels", _root_relationships())
        package.writestr("xl/workbook.xml", _workbook_xml(sheets))
        package.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships(len(sheets)))
        package.writestr("xl/styles.xml", _styles_xml())
        for index, (_, rows) in enumerate(sheets, start=1):
            package.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows))
    return buffer.getvalue()


def _session_summary(metadata: dict[str, str], query: SearchQuery, result: SearchResult) -> ProjectSessionSummary:
    return ProjectSessionSummary(
        session_id=metadata.get("session_id", UNKNOWN),
        saved_at=metadata.get("saved_at", UNKNOWN),
        topic=query.topic,
        record_count=len(result.records),
        domestic_link_count=len(result.domestic_links),
    )


def _project_summary_rows(data: ProjectExportData) -> list[list[object]]:
    return [
        ["Project Name", data.project.name],
        ["Project ID", data.project.project_id],
        ["Description", data.project.description or UNKNOWN],
        ["Linked Session References", len(data.project.session_ids)],
        ["Loaded Sessions", len(data.sessions)],
        ["Missing Session References", len(data.missing_session_ids)],
        ["Integrated Paper Rows", len(data.paper_rows)],
        ["Duplicate Candidate Rows", sum(1 for row in data.paper_rows if row.duplicate_candidate == "YES")],
        ["Manual Domestic Check Count", len(data.manual_checks)],
        ["Notice", PROJECT_EXPORT_NOTICE],
    ]


def _sessions_table(data: ProjectExportData) -> str:
    if not data.sessions:
        return "<p>No linked sessions were loaded. No fake sessions were generated.</p>"
    return _simple_table(["Session ID", "Saved At", "Topic", "Records", "Domestic DB Links"], _session_rows(data.sessions)[1:])


def _papers_table(rows: list[ProjectPaperRow]) -> str:
    if not rows:
        return "<p>No verified paper rows were found. No fake records were generated.</p>"
    return _simple_table(
        [
            "Session ID",
            "Topic",
            "Duplicate Candidate",
            "Title",
            "Authors",
            "Year",
            "Venue",
            "DOI",
            "Original URL",
            "PDF Available",
            "PDF URL",
            "Score",
        ],
        _integrated_paper_rows(rows)[1:],
    )


def _duplicate_table(data: ProjectExportData) -> str:
    rows = _duplicate_candidate_rows(data.paper_rows)[1:]
    if not rows:
        return "<p>No duplicate candidates were detected.</p>"
    return _simple_table(["Duplicate Key", "Session ID", "Topic", "Title", "Year", "DOI"], rows)


def _manual_checks_table(checks: list[DomesticManualCheck]) -> str:
    if not checks:
        return "<p>No domestic manual check records were saved.</p>"
    return _simple_table(
        ["DB", "Keywords", "Title", "DOI", "PDF", "Checked At", "Notes"],
        _manual_check_rows(checks)[1:],
    )


def _missing_sessions_table(session_ids: list[str]) -> str:
    if not session_ids:
        return "<p>No missing session references.</p>"
    return _simple_table(["Missing Session ID", "Status"], _missing_session_rows(session_ids)[1:])


def _session_rows(sessions: list[ProjectSessionSummary]) -> list[list[object]]:
    rows: list[list[object]] = [["session_id", "saved_at", "topic", "record_count", "domestic_link_count"]]
    for session in sessions:
        rows.append([session.session_id, session.saved_at, session.topic, session.record_count, session.domestic_link_count])
    return rows


def _integrated_paper_rows(rows: list[ProjectPaperRow]) -> list[list[object]]:
    output: list[list[object]] = [
        [
            "session_id",
            "topic",
            "duplicate_candidate",
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
            "citation_count",
            "total_score",
            "classic_highly_cited",
            "source_api",
            "caution",
        ]
    ]
    for row in rows:
        paper = row.paper
        output.append(
            [
                row.session_id,
                row.topic,
                row.duplicate_candidate,
                paper.title,
                paper.authors_display,
                paper.year_display,
                paper.venue,
                paper.publisher_or_institution,
                paper.doi,
                paper.landing_page_url,
                "YES" if paper.pdf_available else "NO",
                paper.pdf_url,
                paper.open_access_display,
                paper.citation_display,
                f"{paper.total_score:.2f}",
                "YES" if paper.classic_highly_cited else "NO",
                paper.source_api,
                paper.caution,
            ]
        )
    return output


def _duplicate_candidate_rows(rows: list[ProjectPaperRow]) -> list[list[object]]:
    output: list[list[object]] = [["duplicate_key", "session_id", "topic", "title", "year", "doi"]]
    for row in rows:
        if row.duplicate_candidate == "YES":
            output.append([row.duplicate_key, row.session_id, row.topic, row.paper.title, row.paper.year_display, row.paper.doi])
    return output


def _manual_check_rows(checks: list[DomesticManualCheck]) -> list[list[object]]:
    rows: list[list[object]] = [["database_name", "search_keywords", "title", "landing_page_url", "doi", "pdf_status", "notes", "checked_at"]]
    for check in checks:
        rows.append(
            [
                check.database_name,
                check.search_keywords,
                check.title,
                check.landing_page_url,
                check.doi,
                check.pdf_status,
                check.notes,
                check.checked_at,
            ]
        )
    return rows


def _missing_session_rows(session_ids: list[str]) -> list[list[object]]:
    rows: list[list[object]] = [["missing_session_id", "status"]]
    for session_id in session_ids:
        rows.append([session_id, "Missing session file; no fake session or paper was generated."])
    return rows


def _warning_rows(data: ProjectExportData) -> list[list[object]]:
    return [
        ["type", "message"],
        ["required_notice", "ScholarCheck is an external API metadata review aid."],
        ["required_notice", "Final citation requires checking the original source page."],
        ["required_notice", "Project exports do not modify original saved session files."],
        ["required_notice", "Duplicate papers are not deleted; they are marked only as duplicate candidates."],
        ["required_notice", "Domestic manual check records are user-entered notes, not automated verification results."],
        ["required_notice", "Missing session references do not create fake sessions or papers."],
        ["project_notice", PROJECT_EXPORT_NOTICE],
        ["project_id", data.project.project_id],
    ]


def _duplicate_keys(rows: list[ProjectPaperRow]) -> set[str]:
    counts: dict[str, int] = {}
    for row in rows:
        key = _paper_key(row.paper)
        if key == UNKNOWN:
            continue
        counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count > 1}


def _paper_key(paper: PaperRecord) -> str:
    doi = paper.doi.strip().lower()
    if doi and doi != UNKNOWN.lower():
        return f"doi:{doi}"
    title = _normalize_title(paper.title)
    if title and paper.year is not None:
        return f"title-year:{title}:{paper.year}"
    return UNKNOWN


def _normalize_title(title: str) -> str:
    if not title or title == UNKNOWN:
        return ""
    return re.sub(r"[^0-9a-z]+", "", title.lower())


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"><alignment wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
