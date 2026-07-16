"""Concurrent multi-provider search orchestration."""

import asyncio

import aiohttp
from paper_pipeline.db.repository import Repository
from paper_pipeline.search.arxiv import ArxivProvider
from paper_pipeline.search.base import SearchProvider, allocate
from paper_pipeline.search.pubmed import PubMedProvider


class SearchService:
    def __init__(self, repository: Repository, email: str = "") -> None:
        self.repository, self.email = repository, email

    async def run(
        self,
        keywords: list[str],
        sources: list[str],
        total: int,
        years: tuple[int, int] | None = None,
    ) -> dict[str, int]:
        counts = {source: 0 for source in sources}
        limits = allocate(total, sources)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
            available: dict[str, SearchProvider] = {
                "arxiv": ArxivProvider(session),
                "pubmed": PubMedProvider(session, self.email),
            }
            tasks = [
                (source, available[source].search(keyword, limits[source], years))
                for keyword in keywords
                for source in sources
            ]
            results = await asyncio.gather(*(task for _, task in tasks), return_exceptions=True)
            for (source, _), result in zip(tasks, results, strict=True):
                if isinstance(result, BaseException):
                    continue
                for record in result:
                    self.repository.upsert(record)
                    counts[source] += 1
        return counts
