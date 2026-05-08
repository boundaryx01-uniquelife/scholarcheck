from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from scholarcheck.citations import CITATION_NOTICE, build_reference_candidates
from scholarcheck.matrix import MATRIX_NOTICE, build_literature_matrix
from scholarcheck.models import DomesticManualCheck, SearchQuery, SearchResult, UNKNOWN


EXCEL_NOTICE = (
    "교수님 검토용 Excel 통합 파일입니다. 참고문헌은 후보안이며, 선행연구 매트릭스는 초안입니다. "
    "최종 논문 작성 전 원문 페이지에서 서지정보와 논문 내용을 직접 확인해야 합니다."
)


def save_excel_workbook(
    metadata: dict[str, str],
    query: SearchQuery,
    result: SearchResult,
    manual_checks: list[DomesticManualCheck],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_excel_workbook(metadata, query, result, manual_checks))
    return path


def build_excel_workbook(
    metadata: dict[str, str],
    query: SearchQuery,
    result: SearchResult,
    manual_checks: list[DomesticManualCheck],
) -> bytes:
    sheets = _workbook_sheets(metadata, query, result, manual_checks)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as package:
        _write_package(package, sheets)
    return buffer.getvalue()


def _workbook_sheets(
    metadata: dict[str, str],
    query: SearchQuery,
    result: SearchResult,
    manual_checks: list[DomesticManualCheck],
) -> list[tuple[str, list[list[object]]]]:
    return [
        ("Summary", _summary_rows(metadata, query, result, manual_checks)),
        ("Verified Papers", _verified_paper_rows(result)),
        ("Reference Candidates", _reference_candidate_rows(result)),
        ("Literature Matrix", _matrix_rows(result)),
        ("Domestic DB Links", _domestic_link_rows(result)),
        ("Manual Domestic Checks", _manual_check_rows(manual_checks)),
        ("Warnings", _warning_rows(result)),
    ]


def _summary_rows(
    metadata: dict[str, str],
    query: SearchQuery,
    result: SearchResult,
    manual_checks: list[DomesticManualCheck],
) -> list[list[object]]:
    return [
        ["ScholarCheck Excel Review Workbook"],
        ["Notice", EXCEL_NOTICE],
        ["Session ID", metadata.get("session_id", UNKNOWN)],
        ["Saved At", metadata.get("saved_at", UNKNOWN)],
        ["Topic", query.topic],
        ["Required Keywords", ", ".join(query.required_keywords) or UNKNOWN],
        ["Helpful Keywords", ", ".join(query.helpful_keywords) or UNKNOWN],
        ["Excluded Keywords", ", ".join(query.excluded_keywords) or UNKNOWN],
        ["Verified Paper Count", len(result.records)],
        ["Domestic DB Link Count", len(result.domestic_links)],
        ["Manual Domestic Check Count", len(manual_checks)],
    ]


def _verified_paper_rows(result: SearchResult) -> list[list[object]]:
    rows = [
        [
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
    for record in result.records:
        rows.append(
            [
                record.title,
                record.authors_display,
                record.year_display,
                record.venue,
                record.publisher_or_institution,
                record.doi,
                record.landing_page_url,
                "YES" if record.pdf_available else "확인 불가",
                record.pdf_url,
                record.open_access_display,
                record.citation_display,
                f"{record.total_score:.2f}",
                "YES" if record.classic_highly_cited else "NO",
                record.source_api,
                record.caution,
            ]
        )
    return rows


def _reference_candidate_rows(result: SearchResult) -> list[list[object]]:
    rows = [["title", "reference_candidate", "candidate_notice", "warnings"]]
    for candidate in build_reference_candidates(result.records):
        rows.append(
            [
                candidate.title,
                candidate.reference,
                CITATION_NOTICE,
                " | ".join(candidate.warnings),
            ]
        )
    return rows


def _matrix_rows(result: SearchResult) -> list[list[object]]:
    rows = [
        [
            "title",
            "authors",
            "year",
            "venue",
            "doi",
            "source_url",
            "research_purpose",
            "research_method",
            "research_subjects",
            "key_findings",
            "relevance_note",
            "user_memo",
            "verification_note",
        ]
    ]
    for row in build_literature_matrix(result.records):
        rows.append(
            [
                row.title,
                row.authors,
                row.year,
                row.venue,
                row.doi,
                row.source_url,
                row.research_purpose,
                row.research_method,
                row.research_subjects,
                row.key_findings,
                row.relevance_note,
                row.user_memo,
                row.verification_note,
            ]
        )
    rows.append([])
    rows.append(["Notice", MATRIX_NOTICE])
    return rows


def _domestic_link_rows(result: SearchResult) -> list[list[object]]:
    rows = [["database_name", "search_keywords", "search_url", "result_status", "download_status", "caution"]]
    for link in result.domestic_links:
        rows.append(
            [
                link.database_name,
                link.search_keywords,
                link.search_url,
                link.result_status,
                link.download_status,
                link.caution,
            ]
        )
    return rows


def _manual_check_rows(checks: list[DomesticManualCheck]) -> list[list[object]]:
    rows = [["database_name", "search_keywords", "title", "landing_page_url", "doi", "pdf_status", "notes", "checked_at"]]
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


def _warning_rows(result: SearchResult) -> list[list[object]]:
    rows = [["type", "message"]]
    for warning in result.warnings:
        rows.append(["api_warning", warning])
    for suggestion in result.relaxation_suggestions:
        rows.append(["relaxation_suggestion", suggestion])
    rows.append(["notice", EXCEL_NOTICE])
    return rows


def _write_package(package: zipfile.ZipFile, sheets: list[tuple[str, list[list[object]]]]) -> None:
    package.writestr("[Content_Types].xml", _content_types(len(sheets)))
    package.writestr("_rels/.rels", _root_relationships())
    package.writestr("xl/workbook.xml", _workbook_xml(sheets))
    package.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships(len(sheets)))
    package.writestr("xl/styles.xml", _styles_xml())
    for index, (_, rows) in enumerate(sheets, start=1):
        package.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows))


def _content_types(sheet_count: int) -> str:
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
{sheet_overrides}
</Types>'''


def _root_relationships() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''


def _workbook_xml(sheets: list[tuple[str, list[list[object]]]]) -> str:
    sheet_entries = "".join(
        f'<sheet name="{_xml(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (sheet_name, _) in enumerate(sheets, start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets>{sheet_entries}</sheets>
</workbook>'''


def _workbook_relationships(sheet_count: int) -> str:
    sheet_relationships = "".join(
        f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{sheet_relationships}
<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def _worksheet_xml(rows: list[list[object]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(_cell_xml(row_index, col_index, value, row_index == 1) for col_index, value in enumerate(row, start=1))
        row_xml.append(f'<row r="{row_index}">{cells}</row>')
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
<sheetData>{''.join(row_xml)}</sheetData>
</worksheet>'''


def _cell_xml(row_index: int, col_index: int, value: object, header: bool) -> str:
    cell_ref = f"{_column_name(col_index)}{row_index}"
    style = ' s="1"' if header else ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"{style}><v>{value}</v></c>'
    text = _xml("" if value is None else str(value))
    return f'<c r="{cell_ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>'


def _column_name(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _xml(value: str) -> str:
    return escape(value, {'"': "&quot;"})
