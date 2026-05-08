from __future__ import annotations

from pathlib import Path

from scholarcheck.checklist import build_citation_checklist
from scholarcheck.domestic import build_domestic_links
from scholarcheck.manual_checks import add_manual_check, load_manual_checks
from scholarcheck.models import DomesticManualCheck, PaperRecord, SearchQuery, UNKNOWN
from scholarcheck.output import records_to_csv, records_to_json, save_records
from scholarcheck.pipeline import build_query, deduplicate, search_papers
from scholarcheck.scoring import filter_and_score
from scholarcheck.sources import CrossrefSource
from scholarcheck.verification import verify_doi_with_crossref
from scholarcheck.web import SCREEN_UNKNOWN, _render_records_table, _screen, render_detail, render_home


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
