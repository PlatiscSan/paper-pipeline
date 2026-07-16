from paper_pipeline.models import PaperRecord
from paper_pipeline.normalization import (
    canonical_key,
    merge_records,
    normalize_arxiv_id,
    normalize_doi,
    normalize_pmcid,
    normalize_pmid,
    normalize_title,
    normalize_url,
)


def test_identifiers() -> None:
    assert normalize_doi("https://doi.org/10.1/ABC.") == "10.1/abc"
    assert normalize_pmid("PMID: 12345") == "12345"
    assert normalize_pmcid("pmc 987") == "PMC987"
    assert normalize_arxiv_id("https://arxiv.org/pdf/2401.01234.pdf") == "2401.01234"


def test_url_and_title() -> None:
    assert normalize_url("HTTPS://Example.COM/a/?utm_source=x&b=2#x") == "https://example.com/a?b=2"
    assert normalize_title("  CO₂   Reforming ") == "co2 reforming"


def test_priority_and_merge() -> None:
    assert canonical_key(PaperRecord(title="x", doi="10.1/X", pmid="2")) == "doi:10.1/x"
    old = PaperRecord(title="Title...", abstract="short", doi="10.1/x")
    new = PaperRecord(title="Title complete", abstract="a much longer abstract", pmid="2")
    merged = merge_records(old, new)
    assert merged.title == "Title complete" and merged.pmid == "2"
