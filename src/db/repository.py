"""All transactional persistence operations."""

import json
from collections import Counter
from typing import Any

from paper_pipeline.db.base import Database
from paper_pipeline.db.models import Event, Paper, PaperKeyword, Run, now
from paper_pipeline.models import PaperRecord
from paper_pipeline.normalization import (
    canonical_key,
    normalize_arxiv_id,
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    normalize_title,
    normalize_url,
)
from sqlalchemy import func, or_, select, true
from sqlalchemy.orm import Session, selectinload


class Repository:
    def __init__(self, database: Database) -> None:
        self.db = database

    def _find(self, session: Session, record: PaperRecord) -> Paper | None:
        terms = []
        for column, value in (
            (Paper.doi, normalize_doi(record.doi)),
            (Paper.pmcid, normalize_pmcid(record.pmcid)),
            (Paper.pmid, normalize_pmid(record.pmid)),
            (Paper.arxiv_id, normalize_arxiv_id(record.arxiv_id)),
        ):
            if value:
                terms.append(column == value)
        if normalize_url(record.url):
            terms.append(Paper.url == normalize_url(record.url))
        normalized_title = normalize_title(record.title)
        if normalized_title:
            terms.append(Paper.title_normalized == normalized_title)
        return session.scalar(select(Paper).where(or_(*terms)))

    def upsert(self, record: PaperRecord) -> Paper:
        with self.db.session() as session:
            paper = self._find(session, record)
            if paper is None:
                paper = Paper(
                    canonical_key=canonical_key(record),
                    title=record.title,
                    title_normalized=normalize_title(record.title),
                )
                session.add(paper)
                session.flush()
            values = {
                "doi": normalize_doi(record.doi),
                "pmid": normalize_pmid(record.pmid),
                "pmcid": normalize_pmcid(record.pmcid),
                "arxiv_id": normalize_arxiv_id(record.arxiv_id),
                "url": normalize_url(record.url),
                "pdf_url": record.pdf_url,
                "source": record.source,
                "source_record_id": record.source_record_id,
            }
            for name, value in values.items():
                if value and not getattr(paper, name):
                    setattr(paper, name, value)
            if record.title and (not paper.title or paper.title.endswith("...")):
                paper.title, paper.title_normalized = record.title, normalize_title(record.title)
            if len(record.abstract) > len(paper.abstract):
                paper.abstract = record.abstract
            paper.year = paper.year or record.year
            old_authors = json.loads(paper.authors_json)
            paper.authors_json = json.dumps(
                list(dict.fromkeys([*old_authors, *record.authors])), ensure_ascii=False
            )
            session.flush()
            existing = {item.keyword for item in paper.keywords}
            paper.keywords.extend(
                PaperKeyword(keyword=k) for k in record.keywords if k not in existing
            )
            session.flush()
            session.expunge(paper)
            return paper

    def candidates(self, stage: str, include_failed: bool = False) -> list[Paper]:
        column = Paper.download_status if stage == "download" else Paper.extraction_status
        states = ["pending"] + (["failed"] if include_failed else [])
        extra = Paper.pdf_path != "" if stage == "extract" else true()
        with self.db.session() as session:
            items = list(session.scalars(select(Paper).where(column.in_(states), extra)))
            for item in items:
                session.expunge(item)
            return items

    def update(self, paper_id: int, **values: Any) -> None:
        with self.db.session() as session:
            paper = session.get(Paper, paper_id)
            if paper:
                for name, value in values.items():
                    setattr(paper, name, value)
                paper.updated_at = now()

    def retry(self, stage: str, include_unavailable: bool = False, force: bool = False) -> int:
        column = Paper.download_status if stage == "download" else Paper.extraction_status
        states = ["failed"] + (
            ["unavailable"] if include_unavailable and stage == "download" else []
        )
        with self.db.session() as session:
            papers = list(session.scalars(select(Paper).where(column.in_(states))))
            if stage == "extract" and force:
                papers += list(session.scalars(select(Paper).where(column == "success")))
            for paper in set(papers):
                setattr(paper, column.key, "pending")
            return len(set(papers))

    def all_papers(self) -> list[Paper]:
        with self.db.session() as session:
            query = select(Paper).options(selectinload(Paper.keywords)).order_by(Paper.id)
            result = list(session.scalars(query))
            for item in result:
                session.expunge(item)
            return result

    def status(self) -> dict[str, Any]:
        with self.db.session() as session:
            papers = list(session.scalars(select(Paper)))
            return {
                "total": len(papers),
                "sources": dict(Counter(p.source for p in papers)),
                "downloads": dict(Counter(p.download_status for p in papers)),
                "extractions": dict(Counter(p.extraction_status for p in papers)),
                "pdf_bytes": sum(p.downloaded_bytes for p in papers),
                "input_tokens": sum(p.extraction_input_tokens or 0 for p in papers),
                "output_tokens": sum(p.extraction_output_tokens or 0 for p in papers),
                "keywords": session.scalar(select(func.count()).select_from(PaperKeyword)) or 0,
            }

    def create_run(self, command: str, arguments: dict[str, Any]) -> int:
        with self.db.session() as session:
            run = Run(command=command, arguments_json=json.dumps(arguments), status="running")
            session.add(run)
            session.flush()
            return run.id

    def event(
        self,
        stage: str,
        level: str,
        code: str,
        message: str,
        paper_id: int | None = None,
        run_id: int | None = None,
    ) -> None:
        with self.db.session() as session:
            session.add(
                Event(
                    stage=stage,
                    level=level,
                    code=code,
                    message=message,
                    paper_id=paper_id,
                    run_id=run_id,
                )
            )
