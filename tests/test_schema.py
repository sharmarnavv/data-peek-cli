import json
from typer.testing import CliRunner
from peek.main import app

runner = CliRunner()

def test_schema_csv(sample_csv):
    """Test reading CSV schema."""
    result = runner.invoke(app, ["schema", sample_csv])
    assert result.exit_code == 0
    assert "File:" in result.stdout
    assert "Format: CSV" in result.stdout
    assert "Columns: 8" in result.stdout
    assert "Rows: 20" in result.stdout
    assert "customer_name" in result.stdout


def test_schema_json_output(sample_csv):
    """Test schema command --json flag."""
    result = runner.invoke(app, ["schema", sample_csv, "--json"])
    assert result.exit_code == 0
    
    data = json.loads(result.stdout)
    assert data["format"] == "CSV"
    assert data["columns"] == 8
    assert data["rows"] == 20
    assert "customer_name" in data["schema"]


def test_schema_parquet(tmp_path, sample_csv):
    """Test schema command on Parquet file."""
    out_parquet = tmp_path / "data.parquet"
    runner.invoke(app, ["convert", sample_csv, str(out_parquet)])

    result = runner.invoke(app, ["schema", str(out_parquet)])
    assert result.exit_code == 0
    assert "Format: Parquet" in result.stdout
    assert "Columns: 8" in result.stdout


def test_schema_tsv(tmp_path, sample_csv):
    """Test schema command on TSV file."""
    out_tsv = tmp_path / "data.tsv"
    runner.invoke(app, ["convert", sample_csv, str(out_tsv)])

    result = runner.invoke(app, ["schema", str(out_tsv)])
    assert result.exit_code == 0
    assert "Format: TSV" in result.stdout


def test_schema_jsonl(tmp_path, sample_csv):
    """Test schema command on JSONL file."""
    out_jsonl = tmp_path / "data.jsonl"
    runner.invoke(app, ["convert", sample_csv, str(out_jsonl)])

    result = runner.invoke(app, ["schema", str(out_jsonl)])
    assert result.exit_code == 0
    assert "Format: JSONL" in result.stdout


def test_schema_override_format(tmp_path, sample_csv):
    """Test --from flag on path with non-standard extension."""
    raw_path = tmp_path / "data.raw"
    raw_path.write_text(open(sample_csv).read())

    result = runner.invoke(app, ["schema", str(raw_path), "--from", "csv"])
    assert result.exit_code == 0
    assert "Format: CSV" in result.stdout


def test_schema_missing_file():
    """Test error handling for non-existent file."""
    result = runner.invoke(app, ["schema", "missing_file.csv"])
    assert result.exit_code == 1
    assert "Error" in result.stdout
