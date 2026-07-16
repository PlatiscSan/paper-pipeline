"""CSV compatibility importer."""

import csv
import json
from pathlib import Path

from paper_pipeline.db.repository import Repository
from paper_pipeline.download.storage import is_pdf
from paper_pipeline.models import PaperRecord


def import_csv(repository: Repository, path: Path) -> dict[str, int]:
    created = updated = imported_pdf = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            authors_raw = row.get("authors", "")
            try:
                authors = (
                    json.loads(authors_raw)
                    if authors_raw.startswith("[")
                    else [x.strip() for x in authors_raw.split(";") if x.strip()]
                )
            except json.JSONDecodeError:
                authors = [authors_raw]
            record = PaperRecord(
                title=row.get("title", ""),
                authors=authors,
                year=int(row["year"]) if row.get("year", "").isdigit() else None,
                abstract=row.get("abstract", ""),
                url=row.get("url", ""),
                source=row.get("source", "import"),
                doi=row.get("doi", ""),
                pmid=row.get("pmid", ""),
                pmcid=row.get("pmcid", ""),
                arxiv_id=row.get("arxiv_id", ""),
                pdf_url=row.get("pdf_url", ""),
            )
            paper = repository.upsert(record)
            updated += 1
            file_value = row.get("file", "")
            if file_value:
                pdf = Path(file_value).expanduser().resolve()
                if is_pdf(pdf):
                    repository.update(
                        paper.id,
                        pdf_path=str(pdf),
                        download_status="downloaded",
                        downloaded_bytes=pdf.stat().st_size,
                        download_method="csv_import",
                    )
                    imported_pdf += 1
    return {"processed": updated, "pdf_imported": imported_pdf, "created": created}
