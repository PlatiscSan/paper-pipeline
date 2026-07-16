"""Crossref Works REST API search provider."""

import re
from typing import Any

import aiohttp
from paper_pipeline.models import PaperRecord


class CrossrefProvider:
    name = "crossref"
    endpoint = "https://api.crossref.org/works"

    def __init__(self, session: aiohttp.ClientSession, email: str = "") -> None:
        self.session, self.email = session, email

    async def search(
        self, keyword: str, limit: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]:
        results: list[PaperRecord] = []
        cursor = "*"
        while len(results) < limit:
            size = min(200, limit - len(results))
            params = {"query.bibliographic": keyword, "rows": str(size), "cursor": cursor}
            if self.email:
                params["mailto"] = self.email
            if years:
                params["filter"] = f"from-pub-date:{years[0]}-01-01,until-pub-date:{years[1]}-12-31"
            async with self.session.get(self.endpoint, params=params) as response:
                response.raise_for_status()
                message = (await response.json())["message"]
            items = message.get("items", [])
            results.extend(_parse(item, keyword) for item in items)
            if len(items) < size:
                break
            next_cursor = message.get("next-cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return results[:limit]


def _parse(item: dict[str, Any], keyword: str) -> PaperRecord:
    title = " ".join(item.get("title") or [])
    authors = [
        " ".join(filter(None, (author.get("given"), author.get("family"))))
        for author in item.get("author", [])
    ]
    parts = (item.get("published-print") or item.get("published-online") or {}).get(
        "date-parts", []
    )
    year = parts[0][0] if parts and parts[0] else None
    abstract = re.sub(r"<[^>]+>", " ", item.get("abstract", ""))
    links = item.get("link") or []
    pdf_url = next(
        (link.get("URL", "") for link in links if link.get("content-type") == "application/pdf"),
        "",
    )
    doi = item.get("DOI", "")
    return PaperRecord(
        title=title,
        authors=authors,
        year=year,
        abstract=" ".join(abstract.split()),
        source="crossref",
        source_record_id=doi,
        url=item.get("URL", ""),
        doi=doi,
        pdf_url=pdf_url,
        keywords=[keyword],
    )
