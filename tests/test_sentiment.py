import sys
from typer.testing import CliRunner
from peek.main import app

runner = CliRunner()

def test_sentiment_command_success(sample_csv):
    """Test sentiment command execution when vaderSentiment is installed."""
    result = runner.invoke(app, ["sentiment", sample_csv, "--col", "review"])
    assert result.exit_code == 0
    assert "Average Sentiment" in result.stdout
    assert "Positive" in result.stdout
    assert "Negative" in result.stdout

def test_sentiment_command_missing_dependency(sample_csv, monkeypatch):
    """Test sentiment command when vaderSentiment is missing."""
    # Simulate missing vaderSentiment module
    monkeypatch.setitem(sys.modules, "vaderSentiment", None)
    monkeypatch.setitem(sys.modules, "vaderSentiment.vaderSentiment", None)

    result = runner.invoke(app, ["sentiment", sample_csv, "--col", "review"])
    assert result.exit_code == 1
    assert "Sentiment analysis requires the 'nlp' extra" in result.stdout
    assert "peek-cli[nlp]" in result.stdout
