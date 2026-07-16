from dataclasses import dataclass

import pytest
from paper_pipeline.models import PaperRecord
from paper_pipeline.search.crossref import _parse as parse_crossref
from paper_pipeline.search.europe_pmc import _parse as parse_europe_pmc
from paper_pipeline.search.openalex import _abstract
from paper_pipeline.search.openalex import _parse as parse_openalex
from paper_pipeline.search.semantic_scholar import _parse as parse_semantic_scholar
from paper_pipeline.search.service import SearchService


def test_new_source_parsers() -> None:
    crossref = parse_crossref(
        {"DOI": "10.1/x", "title": ["Title"], "published-online": {"date-parts": [[2024]]}},
        "key",
    )
    europe = parse_europe_pmc({"id": "1", "pmid": "1", "title": "Title", "pubYear": "2024"}, "key")
    semantic = parse_semantic_scholar(
        {"paperId": "s1", "title": "Title", "externalIds": {"DOI": "10.1/x"}}, "key"
    )
    openalex = parse_openalex(
        {
            "id": "https://openalex.org/W1",
            "display_name": "Title",
            "ids": {"doi": "https://doi.org/10.1/x"},
            "abstract_inverted_index": {"hello": [0], "world": [1]},
        },
        "key",
    )
    assert crossref.year == europe.year == 2024
    assert semantic.doi == "10.1/x"
    assert openalex.abstract == "hello world"
    assert _abstract(None) == ""


class FakeRepository:
    def __init__(self) -> None:
        self.ids: dict[str, int] = {}

    def upsert(self, record: PaperRecord):
        self.ids.setdefault(record.title, len(self.ids) + 1)
        return type("Paper", (), {"id": self.ids[record.title]})()


@dataclass
class FakeProvider:
    name: str
    capacity: int
    calls: list[int]

    async def search(self, keyword: str, limit: int, years):
        self.calls.append(limit)
        return [
            PaperRecord(title=f"{self.name}-{index}", source=self.name, keywords=[keyword])
            for index in range(min(limit, self.capacity))
        ]


@pytest.mark.asyncio
async def test_unused_quota_is_reclaimed_deterministically(monkeypatch) -> None:
    arxiv = FakeProvider("arxiv", 2, [])
    pubmed = FakeProvider("pubmed", 20, [])
    monkeypatch.setattr("paper_pipeline.search.service.ArxivProvider", lambda *args: arxiv)
    monkeypatch.setattr("paper_pipeline.search.service.PubMedProvider", lambda *args: pubmed)

    service = SearchService(FakeRepository())  # type: ignore[arg-type]
    counts = await service.run(["keyword"], ["arxiv", "pubmed"], 10)

    assert counts == {"arxiv": 2, "pubmed": 8}
    assert arxiv.calls == [5]
    assert pubmed.calls == [5, 8]
