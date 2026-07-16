from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from paper_pipeline.db.models import Paper
from paper_pipeline.download.resolver import Resolver
from paper_pipeline.download.storage import is_pdf, safe_filename


def test_safe_filename() -> None:
    assert safe_filename("CON") == "_CON"
    assert safe_filename("a<b>:c/d") == "a_b__c_d"


def test_pdf_header(tmp_path: Path) -> None:
    good = tmp_path / "good.pdf"
    good.write_bytes(b"%PDF-1.7\n")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"<html>")
    assert is_pdf(good) and not is_pdf(bad)


@pytest.mark.asyncio
async def test_pmc_includes_europe_pmc_full_text_candidate() -> None:
    resolver = Resolver(None)  # type: ignore[arg-type]
    resolver._pmc = AsyncMock(return_value=[])  # type: ignore[method-assign]
    paper = Paper(pmcid="PMC123", title="Paper", canonical_key="pmcid:PMC123")

    candidates = await resolver.candidates(paper)

    assert candidates[0].method == "europe_pmc"
    assert candidates[0].url.endswith("/PMC123/fullTextPDF")
