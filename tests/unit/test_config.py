from pathlib import Path

from paper_pipeline.config import load_settings


def test_env_expansion_and_relative_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("BASE", "https://provider.test/v1")
    config = tmp_path / "pipeline.toml"
    config.write_text(
        'database_url="sqlite:///db.sqlite"\npapers_dir="pdfs"\n[extraction.provider]\nbase_url="${BASE}"\n',
        encoding="utf-8",
    )
    settings = load_settings(config)
    assert settings.extraction.provider.base_url == "https://provider.test/v1"
    assert settings.papers_dir == tmp_path / "pdfs"
