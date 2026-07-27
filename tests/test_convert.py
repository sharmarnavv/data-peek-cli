from typer.testing import CliRunner
import polars as pl
from peek.main import app

runner = CliRunner()

def test_convert_csv_to_parquet(tmp_path, sample_csv):
    """Test converting CSV to Parquet and verify contents."""
    out_parquet = tmp_path / "output.parquet"
    result = runner.invoke(app, ["convert", sample_csv, str(out_parquet)])
    
    assert result.exit_code == 0
    assert "Converted" in result.stdout
    assert out_parquet.exists()

    df = pl.read_parquet(out_parquet)
    assert len(df) == 20
    assert "Alice Smith" in df["customer_name"].to_list()


def test_convert_parquet_to_jsonl(tmp_path, sample_csv):
    """Test converting Parquet to JSONL."""
    out_parquet = tmp_path / "output.parquet"
    runner.invoke(app, ["convert", sample_csv, str(out_parquet)])

    out_jsonl = tmp_path / "output.jsonl"
    result = runner.invoke(app, ["convert", str(out_parquet), str(out_jsonl)])

    assert result.exit_code == 0
    assert "Converted" in result.stdout
    assert out_jsonl.exists()

    df = pl.read_ndjson(out_jsonl)
    assert len(df) == 20


def test_convert_jsonl_to_tsv(tmp_path, sample_csv):
    """Test converting JSONL to TSV."""
    out_jsonl = tmp_path / "data.jsonl"
    runner.invoke(app, ["convert", sample_csv, str(out_jsonl)])

    out_tsv = tmp_path / "data.tsv"
    result = runner.invoke(app, ["convert", str(out_jsonl), str(out_tsv)])

    assert result.exit_code == 0
    assert out_tsv.exists()

    df = pl.read_csv(out_tsv, separator="\t")
    assert len(df) == 20


def test_convert_tsv_to_csv(tmp_path, sample_csv):
    """Test converting TSV to CSV."""
    out_tsv = tmp_path / "data.tsv"
    runner.invoke(app, ["convert", sample_csv, str(out_tsv)])

    out_csv = tmp_path / "data_final.csv"
    result = runner.invoke(app, ["convert", str(out_tsv), str(out_csv)])

    assert result.exit_code == 0
    assert out_csv.exists()

    df = pl.read_csv(out_csv)
    assert len(df) == 20


def test_convert_missing_output_path_with_to_flag(tmp_path, sample_csv):
    """Test converting with omitted output path but explicit --to flag."""
    input_copy = tmp_path / "input.csv"
    input_copy.write_text(open(sample_csv).read())

    result = runner.invoke(app, ["convert", str(input_copy), "--to", "parquet"])
    assert result.exit_code == 0

    expected_out = tmp_path / "input.parquet"
    assert expected_out.exists()


def test_convert_from_and_to_format_overrides(tmp_path, sample_csv):
    """Test converting files without standard extensions using --from and --to flags."""
    no_ext_input = tmp_path / "raw_data"
    no_ext_input.write_text(open(sample_csv).read())

    no_ext_output = tmp_path / "out_data"
    result = runner.invoke(app, ["convert", str(no_ext_input), str(no_ext_output), "--from", "csv", "--to", "parquet"])

    assert result.exit_code == 0
    assert no_ext_output.exists()

    df = pl.read_parquet(no_ext_output)
    assert len(df) == 20


def test_convert_overwrite_protection(tmp_path, sample_csv):
    """Test that convert fails if target file exists unless --force is passed."""
    out_file = tmp_path / "out.parquet"
    out_file.write_text("existing content")

    # Without --force -> error
    result_err = runner.invoke(app, ["convert", sample_csv, str(out_file)])
    assert result_err.exit_code == 1
    assert "already exists" in result_err.stdout

    # With --force -> success
    result_ok = runner.invoke(app, ["convert", sample_csv, str(out_file), "--force"])
    assert result_ok.exit_code == 0
    assert "Converted" in result_ok.stdout


def test_convert_missing_file():
    """Verify clean error on missing input file."""
    result = runner.invoke(app, ["convert", "nonexistent.csv", "out.parquet"])
    assert result.exit_code == 1
    assert "Error" in result.stdout
