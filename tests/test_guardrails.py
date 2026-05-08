from __future__ import annotations

from pathlib import Path

from scholarcheck.checklist import build_citation_checklist
from scholarcheck.citations import CITATION_NOTICE, build_reference_candidates
from scholarcheck.domestic import build_domestic_links
from scholarcheck.manual_checks import (
    add_manual_check,
    backup_manual_checks,
    load_manual_checks,
    manual_checks_to_csv,
    manual_checks_to_json,
)
from scholarcheck.matrix import MATRIX_NOTICE, NEEDS_REVIEW, build_literature_matrix
from scholarcheck.models import DomesticManualCheck, PaperRecord, SearchQuery, SearchResult, UNKNOWN
from scholarcheck.output import records_to_csv, records_to_json, save_records
from scholarcheck.pipeline import build_query, deduplicate, search_papers
from scholarcheck.scoring import filter_and_score
from scholarcheck.reports import render_professor_report
from scholarcheck.sessions import load_search_session, save_search_session
from scholarcheck.sources import CrossrefSource
from scholarcheck.verification import verify_doi_with_crossref
from scholarcheck.web import (
    SCREEN_UNKNOWN,
    _render_records_table,
    _screen,
    render_citations,
    render_detail,
    render_home,
    render_literature_matrix,
    render_results,
    render_session,
)


def test_missing_doi_is_not_generated() -> None:
    record = CrossrefSource(client=None)._from_item(
        {
            "title": ["Verified metadata only"],
            "URL": "https://example.org/paper",
        }
    )

    assert record.doi == UNKNOWN


def test_missing_pdf_url_is_not_marked_available() -> None:
    record = CrossrefSource(client=None)._from_item(
        {
            "title": ["No PDF here"],
            "DOI": "10.1234/example",
            "URL": "https://example.org/paper",
        }
    )

    assert record.pdf_url == UNKNOWN
    assert record.pdf_available is False


def test_excluded_keyword_in_title_or_abstract_removes_record() -> None:
    query = SearchQuery(
        topic="ai education",
        keywords=["ai", "education"],
        excluded_keywords=["patent"],
    )
    kept = PaperRecord(title="AI education curriculum", abstract="classroom study")
    excluded_by_title = PaperRecord(title="AI education patent", abstract="classroom study")
    excluded_by_abstract = PaperRecord(title="AI education", abstract="patent landscape")

    records = filter_and_score([kept, excluded_by_title, excluded_by_abstract], query)

    assert records == [kept]


def test_same_doi_is_deduplicated() -> None:
    records = deduplicate(
        [
            PaperRecord(title="First", doi="10.1000/example"),
            PaperRecord(title="Second", doi="10.1000/example"),
        ]
    )

    assert len(records) == 1
    assert records[0].title == "First"


def test_similar_title_and_same_year_without_doi_is_deduplicated() -> None:
    records = deduplicate(
        [
            PaperRecord(title="Artificial Intelligence Education", year=2024),
            PaperRecord(title="Artificial: Intelligence   Education!", year=2024),
        ]
    )

    assert len(records) == 1


def test_domestic_links_are_not_verified_records() -> None:
    query = build_query("ai education")
    domestic_links = build_domestic_links(query)
    record = PaperRecord(title="Verified overseas API result")

    assert domestic_links
    assert all(not isinstance(link, PaperRecord) for link in domestic_links)
    assert record not in domestic_links


def test_relaxation_suggestion_file_is_created_when_results_are_short(tmp_path: Path) -> None:
    output_path = tmp_path / "results.csv"
    suggestions = ["Try broader keywords."]

    save_records([], output_path, [], suggestions)

    suggestions_path = tmp_path / "results_relaxation_suggestions.txt"
    assert suggestions_path.exists()
    assert suggestions[0] in suggestions_path.read_text(encoding="utf-8")


def test_api_failure_does_not_create_fake_records(monkeypatch) -> None:
    def fail_search(self, query):
        raise RuntimeError("API unavailable")

    monkeypatch.setattr("scholarcheck.pipeline.CrossrefSource.search", fail_search)
    monkeypatch.setattr("scholarcheck.pipeline.OpenAlexSource.search", fail_search)

    result = search_papers(build_query("artificial intelligence education", limit=5))

    assert result.records == []
    assert result.warnings
    assert result.relaxation_suggestions


def test_doi_verification_does_not_verify_missing_doi() -> None:
    result = verify_doi_with_crossref(PaperRecord(title="No DOI"))

    assert result.status == "missing"
    assert result.doi == UNKNOWN


def test_citation_checklist_marks_missing_pdf_as_needs_check() -> None:
    checklist = build_citation_checklist(
        PaperRecord(title="Checked title", doi="10.1000/example", pdf_available=False)
    )

    pdf_item = next(item for item in checklist if "PDF" in item.label)
    assert pdf_item.status != "OK"
    assert "확인 불가" in pdf_item.detail


def test_manual_domestic_check_is_saved_separately(tmp_path: Path) -> None:
    path = tmp_path / "manual_checks.json"

    add_manual_check(
        DomesticManualCheck(
            database_name="RISS",
            search_keywords="ai education",
            title="Manual checked paper",
        ),
        path=path,
    )
    checks = load_manual_checks(path)

    assert len(checks) == 1
    assert checks[0].database_name == "RISS"
    assert checks[0].title == "Manual checked paper"


def test_export_outputs_keep_unknown_for_missing_values() -> None:
    record = PaperRecord(title="Missing metadata sample")

    csv_output = records_to_csv([record])
    json_output = records_to_json([record], [], [])

    assert UNKNOWN in csv_output
    assert f'"doi": "{UNKNOWN}"' in json_output
    assert f'"pdf_url": "{UNKNOWN}"' in json_output


def test_web_screen_displays_missing_values_as_check_unavailable() -> None:
    record = PaperRecord(title=UNKNOWN, doi=UNKNOWN, pdf_available=False)

    html = _render_records_table([record], "topic=sample")

    assert _screen(UNKNOWN) == SCREEN_UNKNOWN
    assert SCREEN_UNKNOWN in html
    assert ">UNKNOWN<" not in html


def test_web_includes_professor_guidance_copy() -> None:
    home_html = render_home()
    detail_html = render_detail(
        build_query("artificial intelligence education"),
        PaperRecord(title="AI education sample"),
        0,
        "topic=artificial+intelligence+education",
    )

    assert "교수님용 사용 안내" in home_html
    assert "교수님용 인용 전 안내" in detail_html
    assert "최종 인용 전에는 원문 페이지에서" in home_html


def test_manual_domestic_checks_can_be_exported_and_backed_up(tmp_path: Path) -> None:
    path = tmp_path / "manual_checks.json"
    backup_dir = tmp_path / "backups"
    check = DomesticManualCheck(
        database_name="KCI",
        search_keywords="ai education",
        title="Manual paper",
        doi=UNKNOWN,
    )

    add_manual_check(check, path=path)
    checks = load_manual_checks(path)
    csv_output = manual_checks_to_csv(checks)
    json_output = manual_checks_to_json(checks)
    backup_path = backup_manual_checks(path=path, backup_dir=backup_dir)

    assert "database_name,search_keywords,title" in csv_output
    assert "Manual paper" in csv_output
    assert f'"doi": "{UNKNOWN}"' in json_output
    assert backup_path.exists()
    assert "Manual paper" in backup_path.read_text(encoding="utf-8")


def test_web_results_include_manual_export_links() -> None:
    html = render_results(
        query=build_query("ai education"),
        records=[],
        domestic_links=[],
        warnings=[],
        suggestions=[],
        raw_query="topic=ai+education",
        manual_checks=[
            DomesticManualCheck(
                database_name="RISS",
                search_keywords="ai education",
                title="Manual paper",
            )
        ],
    )

    assert "/manual-checks.csv" in html
    assert "/manual-checks.json" in html
    assert "/manual-checks-backup" in html


def test_search_session_can_be_saved_and_loaded(tmp_path: Path) -> None:
    query = build_query("ai education", required_keywords=["ai", "education"], limit=3)
    result = SearchResult(
        records=[PaperRecord(title="AI education sample", doi=UNKNOWN, pdf_url=UNKNOWN)],
        domestic_links=build_domestic_links(query),
        warnings=[],
        relaxation_suggestions=[],
    )

    path = save_search_session(query, result, session_dir=tmp_path)
    metadata, loaded_query, loaded_result = load_search_session(path)

    assert path.parent == tmp_path
    assert metadata["session_id"] == path.stem
    assert loaded_query.topic == "ai education"
    assert loaded_result.records[0].doi == UNKNOWN
    assert loaded_result.records[0].pdf_url == UNKNOWN
    assert loaded_result.domestic_links


def test_professor_report_keeps_guardrail_notice_and_separates_domestic_records() -> None:
    query = build_query("ai education")
    result = SearchResult(
        records=[PaperRecord(title="AI education sample", doi=UNKNOWN)],
        domestic_links=build_domestic_links(query),
        warnings=[],
        relaxation_suggestions=["Try broader keywords."],
    )
    metadata = {"session_id": "session-1", "saved_at": "2026-05-08T00:00:00Z"}

    html = render_professor_report(
        metadata,
        query,
        result,
        manual_checks=[
            DomesticManualCheck(
                database_name="RISS",
                search_keywords="ai education",
                title="Manual domestic paper",
            )
        ],
    )

    assert "Before citation" in html
    assert "Verified Overseas API Results" in html
    assert "Domestic DB Direct Check Required" in html
    assert "Manual domestic paper" in html
    assert "확인 불가" in html


def test_web_session_page_links_to_professor_report() -> None:
    query = build_query("ai education")
    result = SearchResult(records=[PaperRecord(title="AI education sample")])
    html = render_session(
        {"session_id": "session-1", "saved_at": "2026-05-08T00:00:00Z"},
        query,
        result,
        manual_checks=[],
    )

    assert "/report.html?session=session-1" in html
    assert "저장된 자동 검증 논문 목록" in html


def test_reference_candidates_keep_missing_values_and_warning() -> None:
    candidates = build_reference_candidates(
        [
            PaperRecord(
                title="AI education sample",
                authors=[],
                year=None,
                venue=UNKNOWN,
                doi=UNKNOWN,
                landing_page_url=UNKNOWN,
            )
        ]
    )

    assert len(candidates) == 1
    assert candidates[0].reference.startswith(f"{UNKNOWN} ({UNKNOWN}). AI education sample. {UNKNOWN}.")
    assert CITATION_NOTICE in candidates[0].warnings
    assert any("임의 DOI" in item for item in candidates[0].warnings)


def test_reference_candidates_use_doi_link_without_inventing_missing_pages() -> None:
    candidates = build_reference_candidates(
        [
            PaperRecord(
                title="AI education sample",
                authors=["Kim A", "Lee B"],
                year=2024,
                venue="Journal of AI Education",
                doi="10.1000/example",
            )
        ]
    )

    assert candidates[0].reference == "Kim A, & Lee B (2024). AI education sample. Journal of AI Education. https://doi.org/10.1000/example"


def test_web_citation_candidate_view_is_marked_as_candidate_not_final() -> None:
    query = build_query("ai education")
    result = SearchResult(records=[PaperRecord(title="AI education sample", doi=UNKNOWN)])

    html = render_citations(query, result, session_id="session-1")

    assert "참고문헌 후보안" in html
    assert "최종 확정 인용이 아니며" in html
    assert UNKNOWN in html


def test_literature_matrix_does_not_infer_method_subjects_or_findings() -> None:
    rows = build_literature_matrix(
        [
            PaperRecord(
                title="AI education sample",
                authors=["Kim A"],
                year=2024,
                venue="Journal of AI Education",
                doi=UNKNOWN,
                abstract="This abstract mentions a classroom study but should not be summarized.",
            )
        ]
    )

    assert len(rows) == 1
    assert rows[0].research_purpose == NEEDS_REVIEW
    assert rows[0].research_method == NEEDS_REVIEW
    assert rows[0].research_subjects == NEEDS_REVIEW
    assert rows[0].key_findings == NEEDS_REVIEW
    assert rows[0].user_memo == ""
    assert "DOI" in rows[0].verification_note


def test_web_literature_matrix_view_keeps_review_notice_and_memo_column() -> None:
    query = build_query("ai education")
    result = SearchResult(records=[PaperRecord(title="AI education sample", doi=UNKNOWN)])

    html = render_literature_matrix(query, result, session_id="session-1")

    assert "선행연구 매트릭스 초안" in html
    assert MATRIX_NOTICE in html
    assert NEEDS_REVIEW in html
    assert "사용자 메모" in html
