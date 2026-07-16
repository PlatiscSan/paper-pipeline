from paper_pipeline.cli import app
from typer.testing import CliRunner


def test_import_csv_rejects_missing_file_without_traceback() -> None:
    result = CliRunner().invoke(app, ["import-csv", "--input", "missing.csv"])

    assert result.exit_code == 2
    assert "does not exist" in result.output
    assert "Traceback" not in result.output
