import typer
import polars as pl
import plotext as plt
import os
import time
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


app = typer.Typer(help="Peek: High-performance CLI for data inspection.")
console = Console()

def get_file_size(path: str) -> str:
    """Returns file size in human readable format."""
    size_bytes = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

@app.command()
def view(
    file_path: str = typer.Argument(..., help="Path to the CSV file"),
    rows: int = typer.Option(10, help="Number of rows to view"),
    tail: bool = typer.Option(False, help="View the end of the file instead of the start"),
    infer_schema_length: int = typer.Option(10000, help="Number of rows to scan for schema inference")
):
    """
    Instantly view the top N rows (or tail) using Polars Lazy loading.
    """
    path=Path(file_path).expanduser().resolve()
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' not found.")
        raise typer.Exit(code=1)

    try:
        # Create a LazyFrame (doesn't read file yet)
        lf = pl.scan_csv(file_path, infer_schema_length=infer_schema_length)

        if tail:
            # Polars optimizes 'tail' without reading the whole file into RAM
            df = lf.tail(rows).collect()
            title = f"Tail ({rows} rows)"
        else:
            # Head is extremely fast
            df = lf.head(rows).collect()
            title = f"Head ({rows} rows)"

        table = Table(title=f"{title} of {file_path}", show_header=True, header_style="bold magenta")

        # Add columns
        for col in df.columns:
            table.add_column(str(col), style="dim")

        # Add rows (Polars rows are tuples)
        for row in df.iter_rows():
            # Convert values to string for Rich
            row_values = [str(val) for val in row]
            table.add_row(*row_values)

        console.print(table)
        console.print(f"[dim]Showing {len(df)} rows • {len(df.columns)} columns[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def describe(
    file_path: str = typer.Argument(..., help="Path to the CSV file"),
    infer_schema_length: int = typer.Option(10000, help="Number of rows to scan for schema inference")
):
    """
    Health Report: Smart analysis with heuristics for data quality issues.
    """
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' not found.")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Peeking at:[/bold cyan] {file_path} ({get_file_size(file_path)})")
    
    try:
        lf = pl.scan_csv(file_path, infer_schema_length=infer_schema_length)
        
        # 1. Parallel Stat Collection
        # We need Total Rows, Null Counts, and N_Unique for every column.
        # Polars makes this efficient by chaining operations.
        stats = lf.select([
            pl.len().alias("count"),
            pl.all().null_count().name.suffix("_nulls"),
            pl.all().n_unique().name.suffix("_unique")
        ]).collect()

        # Extract total rows
        total_rows = stats["count"][0]
        
        # 2. Build Table & Run Heuristics
        table = Table(title=f"Health Report (Total Rows: {total_rows:,})")
        table.add_column("Column", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Unique", justify="right", style="blue")
        table.add_column("Missing", justify="right")
        
        warnings = [] # Store insights here
        schema = lf.collect_schema()

        # Identify columns from the schema
        for col in schema.keys():
            col_type = str(schema[col])
            
            # Retrieve calculated stats
            n_unique = stats[f"{col}_unique"][0]
            n_missing = stats[f"{col}_nulls"][0]
            missing_pct = (n_missing / total_rows) * 100
            
            # --- HEURISTICS ENGINE ---
            
            # 1. Missing Data Logic
            if missing_pct > 40:
                warnings.append(f"[red]CRITICAL:[/red] Column '{col}' is missing {missing_pct:.1f}% of data.")
                missing_render = f"[bold red]{n_missing} ({missing_pct:.0f}%)[/bold red]"
            elif missing_pct > 5:
                warnings.append(f"[yellow]Warning:[/yellow] Column '{col}' is missing {missing_pct:.1f}% of data.")
                missing_render = f"[yellow]{n_missing} ({missing_pct:.1f}%)[/yellow]"
            else:
                missing_render = f"[dim green]{n_missing} ({missing_pct:.1f}%)[/dim green]"

            # 2. Constant Column Logic
            if n_unique == 1:
                warnings.append(f"[blue]Info:[/blue] Column '{col}' is constant (only 1 unique value).")
                unique_render = f"[dim]{n_unique}[/dim]"
            
            # 3. ID Column Logic
            elif n_unique == total_rows:
                unique_render = f"[bold blue]{n_unique}[/bold blue] (ID?)"
            else:
                unique_render = str(n_unique)

            table.add_row(col, col_type, unique_render, missing_render)

        console.print(table)

        # 3. Print Warnings Panel
        if warnings:
            panel_text = Text.from_markup("\n".join(warnings))
            console.print(Panel(panel_text, title="⚠️  Insights & Warnings", border_style="yellow", expand=False))
        else:
            console.print(Panel("[green]No data quality issues detected![/green]", title="✅ Clean Data", border_style="green", expand=False))

    except Exception as e:
        console.print(f"[bold red]Error reading file:[/bold red] {e}")
        raise typer.Exit(code=1)

@app.command()
def plot(
    file_path: str = typer.Argument(..., help="Path to the CSV file"),
    col: str = typer.Option(..., help="Column to plot (X-axis)"),
    y_col: str = typer.Option(None, help="Column for Y-axis (optional, for scatter plots)"),
    bins: int = typer.Option(10, help="Number of bins for histograms"),
    title: str = typer.Option(None, help="Custom title"),
    infer_schema_length: int = typer.Option(10000, help="Number of rows to scan for schema inference")
):
    """
    Visuals: Plots using Polars data.
    """
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' not found.")
        raise typer.Exit(code=1)

    try:
        # We read just the columns we need to save memory
        required_cols = [col]
        if y_col:
            required_cols.append(y_col)
            
        df = pl.read_csv(file_path, columns=required_cols, infer_schema_length=infer_schema_length)
        
        if col not in df.columns:
             console.print(f"[bold red]Error:[/bold red] Column '{col}' not found.")
             return

        plt.clear_figure()
        plt.theme("pro")

        if y_col:
            # Scatter
            plt.scatter(df[col].to_list(), df[y_col].to_list())
            plt.title(title or f"Scatter: {col} vs {y_col}")
            plt.xlabel(col)
            plt.ylabel(y_col)
        else:
            # Histogram or Bar
            data = df[col]
            if data.dtype in [pl.Int64, pl.Float64, pl.Int32, pl.Float32]:
                plt.hist(data.drop_nulls().to_list(), bins=bins)
                plt.title(title or f"Distribution of {col}")
            else:
                # Categorical Count
                counts = data.value_counts().sort("count", descending=True).head(15)
                # value_counts in Polars returns struct or DF, we unpack
                plt.bar(counts[col].to_list(), counts["count"].to_list())
                plt.title(title or f"Counts of {col}")

        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error plotting:[/bold red] {e}")

@app.command()
def sentiment(
    file_path: str = typer.Argument(..., help="Path to the CSV file"),
    col: str = typer.Option(..., help="Text column to analyze"),
    limit: int = typer.Option(2000, help="Max rows to analyze (VADER is slow on CPU)"),
    infer_schema_length: int = typer.Option(10000, help="Number of rows to scan for schema inference")
):
    """
    NLP: Scans a text column and plots sentiment distribution (Positive/Neutral/Negative).
    """
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' not found.")
        raise typer.Exit(code=1)

    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    except ImportError:
        console.print(
            "[bold red]Error:[/bold red] Sentiment analysis requires the 'nlp' extra.\n"
            "Please install it using: [bold cyan]uv pip install 'peek-cli\\[nlp]'[/bold cyan] (or [bold cyan]pip install 'peek-cli\\[nlp]'[/bold cyan])"
        )
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Scanning sentiment for column:[/bold cyan] '{col}' (Limit: {limit} rows)...")
    
    try:
        # 1. Load Data (Limit rows for performance)
        df = pl.read_csv(file_path, columns=[col], n_rows=limit, infer_schema_length=infer_schema_length)
        
        analyzer = SentimentIntensityAnalyzer()
        scores = []
        categories = {"Positive": 0, "Neutral": 0, "Negative": 0}
        
        from rich.progress import track
        
        texts = df[col].drop_nulls().to_list()

        for text in track(texts, description="Analyzing text..."):
            score = analyzer.polarity_scores(str(text))["compound"]
            scores.append(score)
            
            if score >= 0.05:
                categories["Positive"] += 1
            elif score <= -0.05:
                categories["Negative"] += 1
            else:
                categories["Neutral"] += 1

        avg_sentiment = sum(scores) / len(scores) if scores else 0
        
        # Color-code the average
        if avg_sentiment > 0.05:
            sent_str = f"[green]Positive ({avg_sentiment:.2f})[/green]"
        elif avg_sentiment < -0.05:
            sent_str = f"[red]Negative ({avg_sentiment:.2f})[/red]"
        else:
            sent_str = f"[yellow]Neutral ({avg_sentiment:.2f})[/yellow]"

        console.print(f"\n[bold]Average Sentiment:[/bold] {sent_str}")
        console.print(f"[dim]Based on sample of {len(texts)} rows[/dim]\n")

        # bar chart
        plt.clear_figure()
        plt.theme("pro")
        plt.simple_bar(list(categories.keys()), list(categories.values()), width=60)
        plt.title(f"Sentiment Distribution: {col}")
        plt.show()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

SUPPORTED_FORMATS = {
    "csv": "csv",
    "tsv": "tsv",
    "parquet": "parquet",
    "pq": "parquet",
    "jsonl": "jsonl",
    "ndjson": "jsonl",
}

def _infer_format(file_path: str) -> Optional[str]:
    ext = Path(file_path).suffix.lstrip(".").lower()
    return SUPPORTED_FORMATS.get(ext)

@app.command()
def convert(
    input_path: str = typer.Argument(..., help="Path to input dataset file"),
    output_path: Optional[str] = typer.Argument(None, help="Path to output dataset file"),
    from_format: Optional[str] = typer.Option(None, "--from", help="Override input format (csv, tsv, parquet, jsonl)"),
    to_format: Optional[str] = typer.Option(None, "--to", help="Override output format (csv, tsv, parquet, jsonl)"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite output file if it exists"),
):
    """
    Instantly convert dataset between CSV, TSV, Parquet, and JSONL using Polars streaming.
    """
    in_file = Path(input_path).expanduser().resolve()
    if not in_file.exists():
        console.print(f"[bold red]Error:[/bold red] Input file '{input_path}' not found.")
        raise typer.Exit(code=1)

    # 1. Determine input format
    in_fmt_raw = from_format.lower() if from_format else _infer_format(input_path)
    if not in_fmt_raw or in_fmt_raw not in SUPPORTED_FORMATS:
        console.print(
            f"[bold red]Error:[/bold red] Could not infer input format for '{input_path}'. "
            "Please specify --from (csv, tsv, parquet, jsonl)."
        )
        raise typer.Exit(code=1)
    in_fmt = SUPPORTED_FORMATS[in_fmt_raw]

    # 2. Determine output path and format
    if output_path is None:
        if not to_format:
            console.print("[bold red]Error:[/bold red] Output file path or target format (--to) must be specified.")
            raise typer.Exit(code=1)
        out_fmt_raw = to_format.lower()
        if out_fmt_raw not in SUPPORTED_FORMATS:
            console.print(f"[bold red]Error:[/bold red] Unsupported target format '{to_format}'. Supported: csv, tsv, parquet, jsonl.")
            raise typer.Exit(code=1)
        out_fmt = SUPPORTED_FORMATS[out_fmt_raw]
        base_stem = Path(input_path).stem
        out_file = in_file.parent / f"{base_stem}.{out_fmt}"
        out_display = str(out_file)
    else:
        if to_format:
            out_fmt_raw = to_format.lower()
        else:
            out_fmt_raw = _infer_format(output_path)

        if not out_fmt_raw or out_fmt_raw not in SUPPORTED_FORMATS:
            console.print(
                f"[bold red]Error:[/bold red] Could not infer output format for '{output_path}'. "
                "Please specify --to (csv, tsv, parquet, jsonl)."
            )
            raise typer.Exit(code=1)
        out_fmt = SUPPORTED_FORMATS[out_fmt_raw]
        out_file = Path(output_path).expanduser().resolve()
        out_display = output_path

    # 3. Check overwrite condition
    if out_file.exists() and not force:
        console.print(f"[bold red]Error:[/bold red] Output file '{out_display}' already exists. Use --force / -f to overwrite.")
        raise typer.Exit(code=1)

    # 4. Stream input lazyframe to output sink
    try:
        if in_fmt == "csv":
            lf = pl.scan_csv(str(in_file), separator=",")
        elif in_fmt == "tsv":
            lf = pl.scan_csv(str(in_file), separator="\t")
        elif in_fmt == "parquet":
            lf = pl.scan_parquet(str(in_file))
        elif in_fmt == "jsonl":
            lf = pl.scan_ndjson(str(in_file))
        else:
            raise ValueError(f"Unsupported input format: {in_fmt}")

        start_time = time.perf_counter()

        if out_fmt == "csv":
            lf.sink_csv(str(out_file), separator=",")
        elif out_fmt == "tsv":
            lf.sink_csv(str(out_file), separator="\t")
        elif out_fmt == "parquet":
            lf.sink_parquet(str(out_file), compression="zstd")
        elif out_fmt == "jsonl":
            lf.sink_ndjson(str(out_file))
        else:
            raise ValueError(f"Unsupported output format: {out_fmt}")

        duration = time.perf_counter() - start_time
        in_size = get_file_size(str(in_file))
        out_size = get_file_size(str(out_file))

        console.print(
            f"[bold green]✓ Converted[/bold green] [cyan]{input_path}[/cyan] ({in_size}) → "
            f"[cyan]{out_display}[/cyan] ({out_size}) in [bold]{duration:.2f}s[/bold]"
        )

    except Exception as e:
        if out_file.exists() and not force:
            try:
                out_file.unlink()
            except OSError:
                pass
        console.print(f"[bold red]Error during conversion:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()