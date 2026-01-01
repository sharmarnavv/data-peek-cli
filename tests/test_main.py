from typer.testing import CliRunner
from peek.main import app
import os

runner = CliRunner()

def test_app_help():
    """Verify help screen."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Peek: High-performance CLI" in result.stdout

def test_view_command(sample_csv):
    """Test view command execution."""
    # force wide terminal
    result = runner.invoke(app, ["view", sample_csv], env={"COLUMNS": "200"})
    
    assert result.exit_code == 0
    # check output matches data
    assert "Alice Smith" in result.stdout
    assert "Electronics" in result.stdout
    assert "cost" in result.stdout

def test_describe_command(sample_csv):
    """Test health report output."""
    result = runner.invoke(app, ["describe", sample_csv])
    
    assert result.exit_code == 0
    assert "Health Report" in result.stdout
    
    # check columns
    assert "rating" in result.stdout
    assert "category" in result.stdout
    
    # check polars types
    assert "Int64" in result.stdout or "Float64" in result.stdout
    
    # check missing data flags
    assert "Missing" in result.stdout

def test_missing_file():
    """Verify error on missing file."""
    result = runner.invoke(app, ["view", "ghost_file.csv"])
    
    # graceful exit
    assert result.exit_code == 1
    assert "Error" in result.stdout