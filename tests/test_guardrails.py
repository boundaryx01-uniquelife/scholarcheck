from __future__ import annotations

from pathlib import Path

from scholarcheck.domestic import build_domestic_links
from scholarcheck.models import PaperRecord, SearchQuery, UNKNOWN
from scholarcheck.output import save_records
from scholarcheck.pipeline import build_query, deduplicate, search_papers
from scholarcheck.scoring import filter_and_score
from scholarcheck.sources import CrossrefSource


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
    query = build_query("인공지능 교육")
    domestic_links = build_domestic_links(query)
    record = PaperRecord(title="Verified overseas API result")

    assert domestic_links
    assert all(not isinstance(link, PaperRecord) for link in domestic_links)
    assert record not in domestic_links


def test_relaxation_suggestion_file_is_created_when_results_are_short(tmp_path: Path) -> None:
    output_path = tmp_path / "results.csv"
    suggestions = ["현재 0건만 확인되었습니다. 가짜 결과는 생성하지 않았습니다."]

    save_records([], output_path, [], suggestions)

    suggestions_path = tmp_path / "results_relaxation_suggestions.txt"
    assert suggestions_path.exists()
    assert "가짜 결과는 생성하지 않았습니다" in suggestions_path.read_text(encoding="utf-8")


def test_api_failure_does_not_create_fake_records(monkeypatch) -> None:
    def fail_search(self, query):
        raise RuntimeError("API unavailable")

    monkeypatch.setattr("scholarcheck.pipeline.CrossrefSource.search", fail_search)
    monkeypatch.setattr("scholarcheck.pipeline.OpenAlexSource.search", fail_search)

    result = search_papers(build_query("artificial intelligence education", limit=5))

    assert result.records == []
    assert result.warnings
    assert any("가짜 결과는 생성하지 않았습니다" in item for item in result.relaxation_suggestions)
