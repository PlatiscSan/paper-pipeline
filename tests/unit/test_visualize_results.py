import json
from pathlib import Path

import pytest
from paper_pipeline.visualize_results import generate_report, load_jsonl


def test_generate_self_contained_report(tmp_path: Path) -> None:
    source = tmp_path / "results.jsonl"
    source.write_text(
        json.dumps(
            {
                "id": 1,
                "title": "Catalyst </script> study",
                "extraction_status": "success",
                "extraction_json": {"key_findings": [{"finding": "stable"}]},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "report.html"

    assert generate_report(source, output) == 1
    text = output.read_text(encoding="utf-8")
    assert "Catalyst <\\/script> study" in text
    assert "fetch(" not in text
    assert "key_findings" in text


def test_invalid_json_reports_line(tmp_path: Path) -> None:
    source = tmp_path / "bad.jsonl"
    source.write_text("{}\nnot-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        load_jsonl(source)
