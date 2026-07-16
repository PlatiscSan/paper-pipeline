"""Europe PMC cursor-based REST search provider."""

from typing import Any

import aiohttp
from paper_pipeline.models import PaperRecord


class EuropePMCProvider:
    name = "europe_pmc"
    endpoint = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, session: aiohttp.ClientSession, email: str = "") -> None:
        self.session, self.email = session, email

    async def search(
        self, keyword: str, limit: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]:
        query = keyword
        if years:
            query += f" AND FIRST_PDATE:[{years[0]}-01-01 TO {years[1]}-12-31]"
        results: list[PaperRecord] = []
        cursor = "*"
        while len(results) < limit:
            size = min(1000, limit - len(results))
            params = {
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": str(size),
                "cursorMark": cursor,
            }
            if self.email:
                params["email"] = self.email
            async with self.session.get(self.endpoint, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            items = data.get("resultList", {}).get("result", [])
            results.extend(_parse(item, keyword) for item in items)
            next_cursor = data.get("nextCursorMark")
            if len(items) < size or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return results[:limit]


def _parse(item: dict[str, Any], keyword: str) -> PaperRecord:
    authors = [
        author.get("fullName", "") for author in item.get("authorList", {}).get("author", [])
    ]
    pmcid = item.get("pmcid", "")
    pmid = item.get("pmid", "")
    identifier = pmcid or pmid or item.get("id", "")
    return PaperRecord(
        title=item.get("title", ""),
        authors=[author for author in authors if author],
        year=int(item["pubYear"]) if str(item.get("pubYear", "")).isdigit() else None,
        abstract=item.get("abstractText", ""),
        source="europe_pmc",
        source_record_id=identifier,
        url=f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}",
        doi=item.get("doi", ""),
        pmid=pmid,
        pmcid=pmcid,
        keywords=[keyword],
    )
