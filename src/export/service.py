"""CSV and JSON Lines exports."""

import csv
import json
from pathlib import Path
from typing import Any

from paper_pipeline.db.models import Paper
from paper_pipeline.db.repository import Repository

FIELDS = [
    "id",
    "title",
    "authors",
    "year",
    "abstract",
    "source",
    "doi",
    "pmid",
    "pmcid",
    "arxiv_id",
    "url",
    "pdf_url",
    "pdf_path",
    "download_status",
    "download_method",
    "download_error",
    "extraction_status",
    "extraction_provider",
    "extraction_model",
    "extraction_error",
    "extraction_json",
    "created_at",
    "updated_at",
]


def _row(p: Paper) -> dict[str, Any]:
    return {
        "id": p.id,
        "title": p.title,
        "authors": json.loads(p.authors_json),
        "year": p.year,
        "abstract": p.abstract,
        "source": p.source,
        "doi": p.doi,
        "pmid": p.pmid,
        "pmcid": p.pmcid,
        "arxiv_id": p.arxiv_id,
        "url": p.url,
        "pdf_url": p.pdf_url,
        "pdf_path": p.pdf_path,
        "download_status": p.download_status,
        "download_method": p.download_method,
        "download_error": p.download_error_message,
        "extraction_status": p.extraction_status,
        "extraction_provider": p.extraction_provider,
        "extraction_model": p.extraction_model,
        "extraction_error": p.extraction_error_message,
        "extraction_json": json.loads(p.extraction_json) if p.extraction_json else None,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def export(
    repository: Repository,
    path: Path,
    format: str,
    only_downloaded: bool = False,
    only_extracted: bool = False,
    source: str | None = None,
    year: int | None = None,
    keyword: str | None = None,
) -> int:
    papers = [
        p
        for p in repository.all_papers()
        if (not only_downloaded or p.download_status == "downloaded")
        and (not only_extracted or p.extraction_status == "success")
        and (source is None or p.source == source)
        and (year is None or p.year == year)
        and (keyword is None or keyword in {item.keyword for item in p.keywords})
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    if format == "jsonl":
        with path.open("w", encoding="utf-8") as handle:
            for paper in papers:
                handle.write(json.dumps(_row(paper), ensure_ascii=False) + "\n")
    else:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for paper in papers:
                row = _row(paper)
                row["authors"] = json.dumps(row["authors"], ensure_ascii=False)
                row["extraction_json"] = (
                    json.dumps(row["extraction_json"], ensure_ascii=False)
                    if row["extraction_json"]
                    else ""
                )
                writer.writerow(row)
    return len(papers)
