from pathlib import Path

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
