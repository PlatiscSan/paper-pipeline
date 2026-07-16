"""Semantic Scholar Academic Graph bulk search provider."""

from typing import Any

import aiohttp
from paper_pipeline.models import PaperRecord


class SemanticScholarProvider:
    name = "semantic_scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"

    def __init__(self, session: aiohttp.ClientSession, api_key: str = "") -> None:
        self.session, self.api_key = session, api_key

    async def search(
        self, keyword: str, limit: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]:
        results: list[PaperRecord] = []
        token = ""
        headers = {"x-api-key": self.api_key} if self.api_key else {}
        while len(results) < limit:
            params = {
                "query": keyword,
                "fields": "paperId,externalIds,url,title,abstract,year,authors,openAccessPdf",
            }
            if years:
                params["year"] = f"{years[0]}-{years[1]}"
            if token:
                params["token"] = token
            async with self.session.get(self.endpoint, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
            items = data.get("data", [])
            results.extend(_parse(item, keyword) for item in items)
            token = data.get("token", "")
            if not token or not items:
                break
        return results[:limit]


def _parse(item: dict[str, Any], keyword: str) -> PaperRecord:
    external = item.get("externalIds") or {}
    oa = item.get("openAccessPdf") or {}
    return PaperRecord(
        title=item.get("title") or "",
        authors=[author.get("name", "") for author in item.get("authors") or []],
        year=item.get("year"),
        abstract=item.get("abstract") or "",
        source="semantic_scholar",
        source_record_id=item.get("paperId", ""),
        url=item.get("url") or "",
        doi=external.get("DOI", ""),
        pmid=external.get("PubMed", ""),
        arxiv_id=external.get("ArXiv", ""),
        pdf_url=oa.get("url", ""),
        keywords=[keyword],
    )
