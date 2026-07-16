"""Local PDF text extraction with physical page markers."""

from pathlib import Path

from paper_pipeline.errors import ErrorCode, PipelineError


def extract_pdf_text(path: Path) -> list[str]:
    pages: list[str] = []
    try:
        import fitz

        with fitz.open(path) as document:
            pages = [page.get_text() for page in document]
    except Exception:
        from pypdf import PdfReader

        with path.open("rb") as handle:
            pages = [(page.extract_text() or "") for page in PdfReader(handle).pages]
    if not any(page.strip() for page in pages):
        raise PipelineError(
            ErrorCode.PDF_TEXT_EMPTY, "PDF contains no extractable text; OCR is not automatic"
        )
    return [f"[PDF_PAGE {index}]\n{text.strip()}" for index, text in enumerate(pages, 1)]
