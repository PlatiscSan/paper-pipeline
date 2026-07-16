"""OpenAlex Works cursor search provider."""

from typing import Any

import aiohttp
from paper_pipeline.models import PaperRecord


class OpenAlexProvider:
    name = "openalex"
    endpoint = "https://api.openalex.org/works"

    def __init__(self, session: aiohttp.ClientSession, api_key: str = "") -> None:
        self.session, self.api_key = session, api_key

    async def search(
        self, keyword: str, limit: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]:
        if not self.api_key:
            return []
        results: list[PaperRecord] = []
        cursor = "*"
        while len(results) < limit:
            size = min(100, limit - len(results))
            params = {
                "api_key": self.api_key,
                "search": keyword,
                "per_page": str(size),
                "cursor": cursor,
            }
            if years:
                params["filter"] = (
                    f"from_publication_date:{years[0]}-01-01,to_publication_date:{years[1]}-12-31"
                )
            async with self.session.get(self.endpoint, params=params) as response:
                response.raise_for_status()
                data = await response.json()
            items = data.get("results", [])
            results.extend(_parse(item, keyword) for item in items)
            next_cursor = data.get("meta", {}).get("next_cursor")
            if len(items) < size or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return results[:limit]


def _abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    words = sorted(
        ((position, word) for word, positions in index.items() for position in positions),
        key=lambda pair: pair[0],
    )
    return " ".join(word for _, word in words)


def _parse(item: dict[str, Any], keyword: str) -> PaperRecord:
    ids = item.get("ids") or {}
    best = item.get("best_oa_location") or {}
    return PaperRecord(
        title=item.get("display_name") or item.get("title") or "",
        authors=[
            authorship.get("author", {}).get("display_name", "")
            for authorship in item.get("authorships") or []
        ],
        year=item.get("publication_year"),
        abstract=_abstract(item.get("abstract_inverted_index")),
        source="openalex",
        source_record_id=str(item.get("id", "")).rsplit("/", 1)[-1],
        url=(item.get("primary_location") or {}).get("landing_page_url") or item.get("id", ""),
        doi=ids.get("doi", ""),
        pmid=str(ids.get("pmid", "")).rsplit("/", 1)[-1],
        pmcid=str(ids.get("pmcid", "")).rsplit("/", 1)[-1],
        pdf_url=best.get("pdf_url") or "",
        keywords=[keyword],
    )
