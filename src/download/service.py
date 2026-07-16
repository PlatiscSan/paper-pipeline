"""Paper-level concurrent resolution and download orchestration."""

import asyncio
import os

import aiohttp
from paper_pipeline.config import Settings
from paper_pipeline.db.models import Paper
from paper_pipeline.db.repository import Repository
from paper_pipeline.download.client import DownloadClient
from paper_pipeline.download.models import DownloadResult
from paper_pipeline.download.resolver import Resolver
from paper_pipeline.download.storage import destination, is_pdf


class DownloadService:
    def __init__(self, repository: Repository, settings: Settings) -> None:
        self.repository, self.settings = repository, settings

    async def run(
        self, concurrency: int | None = None, include_failed: bool = False
    ) -> dict[str, int]:
        papers = self.repository.candidates("download", include_failed)
        sem = asyncio.Semaphore(concurrency or self.settings.downloader.concurrency)
        timeout = aiohttp.ClientTimeout(total=300, connect=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            resolver = Resolver(
                session,
                os.getenv(self.settings.downloader.email_env, ""),
                os.getenv(self.settings.downloader.semantic_scholar_api_key_env, ""),
            )
            client = DownloadClient(
                session,
                self.settings.downloader.retries,
                self.settings.downloader.delay_seconds,
                self.settings.downloader.max_size_mb,
            )

            async def one(paper: Paper) -> str:
                async with sem:
                    return await self._one(paper, resolver, client)

            statuses = await asyncio.gather(*(one(p) for p in papers))
        return {name: statuses.count(name) for name in set(statuses)}

    async def _one(self, paper: Paper, resolver: Resolver, client: DownloadClient) -> str:
        if paper.pdf_path and is_pdf(__import__("pathlib").Path(paper.pdf_path)):
            return "skipped"
        self.repository.update(
            paper.id, download_status="downloading", download_attempts=paper.download_attempts + 1
        )
        candidates = await resolver.candidates(paper)
        if not candidates:
            self.repository.update(
                paper.id,
                download_status="unavailable",
                download_error_code="NO_OPEN_ACCESS_PDF",
                download_error_message="no open candidate",
            )
            return "unavailable"
        last = DownloadResult()
        for candidate in candidates:
            last = await client.fetch(candidate, destination(self.settings.papers_dir, paper))
            if last.status == "downloaded":
                self.repository.update(
                    paper.id,
                    pdf_path=last.path,
                    resolved_pdf_url=last.url,
                    download_method=last.method,
                    downloaded_bytes=last.bytes,
                    download_status="downloaded",
                    download_error_code="",
                    download_error_message="",
                )
                return "downloaded"
        status = (
            "unavailable"
            if last.error_code in {"REMOTE_NOT_FOUND", "REMOTE_FORBIDDEN"}
            else "failed"
        )
        self.repository.update(
            paper.id,
            download_status=status,
            download_error_code=last.error_code,
            download_error_message=last.error_message,
        )
        return status
