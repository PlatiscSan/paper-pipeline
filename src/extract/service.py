"""Concurrent paper extraction; chunks within one paper remain serial."""

import asyncio
import json
from pathlib import Path

from paper_pipeline.config import Settings
from paper_pipeline.db.models import Paper
from paper_pipeline.db.repository import Repository
from paper_pipeline.errors import PipelineError
from paper_pipeline.extract.chunking import chunk_pages
from paper_pipeline.extract.openai_compatible import OpenAICompatibleProvider
from paper_pipeline.extract.pdf_text import extract_pdf_text
from paper_pipeline.extract.provider import AIProvider, AIResult
from paper_pipeline.extract.schema import load_schema


class ExtractionService:
    def __init__(
        self, repository: Repository, settings: Settings, provider: AIProvider | None = None
    ) -> None:
        self.repository, self.settings = repository, settings
        self.schema, self.schema_hash = load_schema(settings.extraction.schema_path)
        self.provider = provider or OpenAICompatibleProvider(
            settings.extraction.provider, settings.extraction
        )

    async def run(
        self, concurrency: int | None = None, include_failed: bool = False
    ) -> dict[str, int]:
        papers = self.repository.candidates("extract", include_failed)
        sem = asyncio.Semaphore(concurrency or self.settings.extraction.concurrency)

        async def one(paper: Paper) -> str:
            async with sem:
                return await self._one(paper)

        statuses = await asyncio.gather(*(one(p) for p in papers))
        return {name: statuses.count(name) for name in set(statuses)}

    async def _one(self, paper: Paper) -> str:
        self.repository.update(
            paper.id,
            extraction_status="extracting",
            extraction_attempts=paper.extraction_attempts + 1,
        )
        try:
            if self.settings.extraction.provider.pdf_mode == "file":
                final = await self.provider.extract_file(Path(paper.pdf_path), self.schema)
            else:
                chunks = chunk_pages(
                    extract_pdf_text(Path(paper.pdf_path)),
                    self.settings.extraction.provider.text_chunk_chars,
                )
                maximum = self.settings.extraction.provider.max_text_chunks
                if maximum:
                    chunks = chunks[:maximum]
                partials: list[AIResult] = []
                for chunk in chunks:
                    partials.append(await self.provider.extract_text(chunk, self.schema))
                final = (
                    partials[0]
                    if len(partials) == 1
                    else await self.provider.extract_text(
                        json.dumps([x.data for x in partials], ensure_ascii=False),
                        self.schema,
                        merge=True,
                    )
                )
                final.input_tokens += sum(x.input_tokens for x in partials)
                final.output_tokens += sum(x.output_tokens for x in partials)
            self.repository.update(
                paper.id,
                extraction_status="success",
                extraction_json=json.dumps(final.data, ensure_ascii=False),
                extraction_provider=self.settings.extraction.provider.name,
                extraction_model=self.settings.extraction.provider.model,
                extraction_schema_hash=self.schema_hash,
                extraction_response_id=final.response_id,
                extraction_input_tokens=final.input_tokens,
                extraction_output_tokens=final.output_tokens,
                extraction_total_tokens=final.input_tokens + final.output_tokens,
                extraction_error_code="",
                extraction_error_message="",
            )
            return "success"
        except PipelineError as exc:
            self.repository.update(
                paper.id,
                extraction_status="failed",
                extraction_error_code=exc.code,
                extraction_error_message=str(exc)[:1000],
            )
            return "failed"
        except Exception as exc:
            self.repository.update(
                paper.id,
                extraction_status="failed",
                extraction_error_code="AI_ERROR",
                extraction_error_message=str(exc)[:1000],
            )
            return "failed"
