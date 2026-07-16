import json
from pathlib import Path

from paper_pipeline.db.base import Database
from paper_pipeline.db.migrations import upgrade
from paper_pipeline.db.repository import Repository
from paper_pipeline.export.service import export
from paper_pipeline.models import PaperRecord


def test_migrate_upsert_retry_export(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    upgrade(url)
    repo = Repository(Database(url))
    first = repo.upsert(PaperRecord(title="Paper", doi="10.1/X", keywords=["a"]))
    second = repo.upsert(PaperRecord(title="Paper full", doi="https://doi.org/10.1/x", pmid="2"))
    assert first.id == second.id and len(repo.all_papers()) == 1
    repo.update(first.id, download_status="failed")
    assert repo.retry("download") == 1
    output = tmp_path / "result.jsonl"
    assert export(repo, output, "jsonl") == 1
    assert json.loads(output.read_text())["doi"] == "10.1/x"
