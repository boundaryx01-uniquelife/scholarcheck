from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from scholarcheck.models import DomesticSearchLink, SearchQuery


@dataclass(frozen=True, slots=True)
class DomesticDatabase:
    name: str
    url_template: str

    def build_link(self, keyword_text: str) -> DomesticSearchLink:
        encoded = quote_plus(keyword_text)
        return DomesticSearchLink(
            database_name=self.name,
            search_keywords=keyword_text,
            search_url=self.url_template.format(query=encoded),
        )


DOMESTIC_DATABASES = [
    DomesticDatabase(
        name="RISS",
        url_template="https://www.riss.kr/search/Search.do?queryText={query}&searchGubun=true&colName=re_a_kor",
    ),
    DomesticDatabase(
        name="KCI",
        url_template="https://www.kci.go.kr/kciportal/po/search/poArtiSear.kci?searchBean.searchText={query}",
    ),
    DomesticDatabase(
        name="DBpia",
        url_template="https://www.dbpia.co.kr/search/topSearch?searchOption=all&query={query}",
    ),
    DomesticDatabase(
        name="KISS",
        url_template="https://kiss.kstudy.com/Search/Result?field=0&query={query}",
    ),
    DomesticDatabase(
        name="e-Article",
        url_template="https://www.earticle.net/Search/Result?sf=3&q={query}",
    ),
]


def build_domestic_links(query: SearchQuery) -> list[DomesticSearchLink]:
    keyword_text = build_domestic_keyword_text(query)
    return [database.build_link(keyword_text) for database in DOMESTIC_DATABASES]


def build_domestic_keyword_text(query: SearchQuery) -> str:
    keywords = [*query.required_keywords, *query.helpful_keywords]
    if keywords:
        return " ".join(dict.fromkeys(keywords))
    if query.keywords:
        return " ".join(query.keywords)
    return query.topic
