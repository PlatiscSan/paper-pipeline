"""arXiv Atom API provider."""

import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import aiohttp
from paper_pipeline.models import PaperRecord

NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class ArxivProvider:
    name = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"

    def __init__(self, session: aiohttp.ClientSession, page_size: int = 100) -> None:
        self.session, self.page_size = session, page_size

    async def search(
        self, keyword: str, limit: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]:
        tasks = [
            self._page(keyword, start, min(self.page_size, limit - start), years)
            for start in range(0, limit, self.page_size)
        ]
        pages = await asyncio.gather(*tasks)
        return [paper for page in pages for paper in page][:limit]

    async def _page(
        self, keyword: str, start: int, size: int, years: tuple[int, int] | None
    ) -> list[PaperRecord]:
        terms = [term for term in keyword.split() if len(term) > 2]
        query = " AND ".join(f'all:"{term}"' for term in terms) or f'all:"{keyword}"'
        if years:
            query += f" AND submittedDate:[{years[0]}01010000 TO {years[1]}12312359]"
        params = {"search_query": query, "start": start, "max_results": size}
        url = f"{self.endpoint}?{urlencode(params)}"
        async with self.session.get(url) as response:
            response.raise_for_status()
            body = await response.text()
        root = ET.fromstring(body)
        result = []
        for entry in root.findall("a:entry", NS):
            abs_url = _text(entry, "a:id")
            arxiv_id = abs_url.rsplit("/", 1)[-1]
            pdf = next(
                (
                    x.get("href", "")
                    for x in entry.findall("a:link", NS)
                    if x.get("type") == "application/pdf"
                ),
                "",
            )
            result.append(
                PaperRecord(
                    title=_text(entry, "a:title"),
                    authors=[_text(a, "a:name") for a in entry.findall("a:author", NS)],
                    year=int(_text(entry, "a:published")[:4]),
                    abstract=_text(entry, "a:summary"),
                    source="arxiv",
                    source_record_id=arxiv_id,
                    url=abs_url,
                    arxiv_id=arxiv_id,
                    doi=_text(entry, "arxiv:doi"),
                    pdf_url=pdf,
                    keywords=[keyword],
                )
            )
        return result


def _text(node: ET.Element, path: str) -> str:
    item = node.find(path, NS)
    return " ".join("".join(item.itertext()).split()) if item is not None else ""
