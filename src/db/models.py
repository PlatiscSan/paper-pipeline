"""Relational schema."""

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_key: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text, default="")
    title_normalized: Mapped[str] = mapped_column(Text, default="")
    authors_json: Mapped[str] = mapped_column(Text, default="[]")
    year: Mapped[int | None] = mapped_column(Integer)
    abstract: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(Text, default="")
    source_record_id: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    doi: Mapped[str] = mapped_column(Text, default="")
    pmid: Mapped[str] = mapped_column(Text, default="")
    pmcid: Mapped[str] = mapped_column(Text, default="")
    arxiv_id: Mapped[str] = mapped_column(Text, default="")
    pdf_url: Mapped[str] = mapped_column(Text, default="")
    pdf_path: Mapped[str] = mapped_column(Text, default="")
    resolved_pdf_url: Mapped[str] = mapped_column(Text, default="")
    download_status: Mapped[str] = mapped_column(Text, default="pending")
    download_method: Mapped[str] = mapped_column(Text, default="")
    download_error_code: Mapped[str] = mapped_column(Text, default="")
    download_error_message: Mapped[str] = mapped_column(Text, default="")
    downloaded_bytes: Mapped[int] = mapped_column(default=0)
    download_attempts: Mapped[int] = mapped_column(default=0)
    extraction_status: Mapped[str] = mapped_column(Text, default="pending")
    extraction_json: Mapped[str | None] = mapped_column(Text)
    extraction_provider: Mapped[str] = mapped_column(Text, default="")
    extraction_model: Mapped[str] = mapped_column(Text, default="")
    extraction_schema_hash: Mapped[str] = mapped_column(Text, default="")
    extraction_error_code: Mapped[str] = mapped_column(Text, default="")
    extraction_error_message: Mapped[str] = mapped_column(Text, default="")
    extraction_response_id: Mapped[str] = mapped_column(Text, default="")
    extraction_input_tokens: Mapped[int | None] = mapped_column()
    extraction_output_tokens: Mapped[int | None] = mapped_column()
    extraction_total_tokens: Mapped[int | None] = mapped_column()
    extraction_attempts: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[str] = mapped_column(Text, default=now)
    updated_at: Mapped[str] = mapped_column(Text, default=now, onupdate=now)
    keywords: Mapped[list["PaperKeyword"]] = relationship(cascade="all, delete-orphan")
    __table_args__ = (
        Index("ix_papers_download_status", "download_status"),
        Index("ix_papers_extraction_status", "extraction_status"),
        Index("ix_papers_doi", "doi"),
        Index("ix_papers_pmid", "pmid"),
        Index("ix_papers_pmcid", "pmcid"),
        Index("ix_papers_arxiv_id", "arxiv_id"),
    )


class PaperKeyword(Base):
    __tablename__ = "paper_keywords"
    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    keyword: Mapped[str] = mapped_column(Text, primary_key=True)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    command: Mapped[str] = mapped_column(Text)
    arguments_json: Mapped[str] = mapped_column(Text)
    started_at: Mapped[str] = mapped_column(Text, default=now)
    completed_at: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))
    stage: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(Text)
    code: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=now)
