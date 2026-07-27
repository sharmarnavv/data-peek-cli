import typer
import polars as pl
import plotext as plt
import os
import time
import json
import difflib
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

def _validate_file_path(file_path: str) -> Path:
    """Resolves path, checks existence, and suggests close matches on typo error."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' not found.")
        parent = path.parent
        if parent.exists():
            filenames = [f.name for f in parent.iterdir() if f.is_file()]
            matches = difflib.get_close_matches(path.name, filenames, n=3, cutoff=0.3)
            if not matches:
                stem_prefix = path.stem.split("_")[0].lower()
                matches = [f for f in filenames if stem_prefix and stem_prefix in f.lower()][:3]
            if matches:
                suggestions = [str(parent / m) for m in matches]
                console.print(f"[yellow]Did you mean:[/yellow] {', '.join(suggestions)}?")
        raise typer.Exit(code=1)
    return path

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
    path = _validate_file_path(file_path)

    try:
        # Create a LazyFrame (doesn't read file yet)
        lf = pl.scan_csv(str(path), infer_schema_length=infer_schema_length)

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

def _format_stat_val(val, dtype) -> str:
    if val is None:
        return "-"
    if dtype.is_float():
        return f"{val:.2f}"
    return str(val)

@app.command()
def describe(
    file_path: str = typer.Argument(..., help="Path to the file (CSV, TSV, Parquet, JSONL)"),
    infer_schema_length: int = typer.Option(10000, help="Number of rows to scan for schema inference")
):
    """
    Health Report: Smart analysis with heuristics and Min/Max/Avg statistics.
    """
    path = _validate_file_path(file_path)

    console.print(f"[bold cyan]Peeking at:[/bold cyan] {file_path} ({get_file_size(str(path))})")
    
    try:
        fmt = _infer_format(file_path) or "csv"
        if fmt == "parquet":
            lf = pl.scan_parquet(str(path))
        elif fmt == "tsv":
            lf = pl.scan_csv(str(path), separator="\t", infer_schema_length=infer_schema_length)
        elif fmt == "jsonl":
            lf = pl.scan_ndjson(str(path), infer_schema_length=infer_schema_length)
        else:
            lf = pl.scan_csv(str(path), infer_schema_length=infer_schema_length)

        schema = lf.collect_schema()
        
        # 1. Parallel Stat Collection
        stat_exprs = [pl.len().alias("count")]
        for col, dtype in schema.items():
            stat_exprs.append(pl.col(col).null_count().alias(f"{col}_nulls"))
            stat_exprs.append(pl.col(col).n_unique().alias(f"{col}_unique"))
            if dtype.is_numeric() or dtype.is_temporal():
                stat_exprs.append(pl.col(col).min().alias(f"{col}_min"))
                stat_exprs.append(pl.col(col).max().alias(f"{col}_max"))
            if dtype.is_numeric():
                stat_exprs.append(pl.col(col).mean().alias(f"{col}_mean"))

        stats = lf.select(stat_exprs).collect()
        total_rows = stats["count"][0]
        
        # 2. Build Table & Run Heuristics
        table = Table(title=f"Health Report (Total Rows: {total_rows:,})")
        table.add_column("Column", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Unique", justify="right", style="blue")
        table.add_column("Missing", justify="right")
        table.add_column("Min", justify="right", style="green")
        table.add_column("Max", justify="right", style="green")
        table.add_column("Avg", justify="right", style="yellow")
        
        warnings = [] # Store insights here

        for col in schema.keys():
            col_type = str(schema[col])
            dtype = schema[col]
            
            n_unique = stats[f"{col}_unique"][0]
            n_missing = stats[f"{col}_nulls"][0]
            missing_pct = (n_missing / total_rows) * 100 if total_rows > 0 else 0
            
            # --- HEURISTICS ENGINE ---
            if missing_pct > 40:
                warnings.append(f"[red]CRITICAL:[/red] Column '{col}' is missing {missing_pct:.1f}% of data.")
                missing_render = f"[bold red]{n_missing} ({missing_pct:.0f}%)[/bold red]"
            elif missing_pct > 5:
                warnings.append(f"[yellow]Warning:[/yellow] Column '{col}' is missing {missing_pct:.1f}% of data.")
                missing_render = f"[yellow]{n_missing} ({missing_pct:.1f}%)[/yellow]"
            else:
                missing_render = f"[dim green]{n_missing} ({missing_pct:.1f}%)[/dim green]"

            if n_unique == 1:
                warnings.append(f"[blue]Info:[/blue] Column '{col}' is constant (only 1 unique value).")
                unique_render = f"[dim]{n_unique}[/dim]"
            elif n_unique == total_rows and total_rows > 0:
                unique_render = f"[bold blue]{n_unique}[/bold blue] (ID?)"
            else:
                unique_render = str(n_unique)

            min_val = stats[f"{col}_min"][0] if f"{col}_min" in stats.columns else None
            max_val = stats[f"{col}_max"][0] if f"{col}_max" in stats.columns else None
            mean_val = stats[f"{col}_mean"][0] if f"{col}_mean" in stats.columns else None

            min_render = _format_stat_val(min_val, dtype)
            max_render = _format_stat_val(max_val, dtype)
            avg_render = f"{mean_val:.2f}" if mean_val is not None else "-"

            table.add_row(col, col_type, unique_render, missing_render, min_render, max_render, avg_render)

        console.print(table)

        if warnings:
            panel_text = Text.from_markup("\n".join(warnings))
            console.print(Panel(panel_text, title="⚠️ Insights & Warnings", border_style="yellow", expand=False))
        else:
            console.print(Panel("[green]No data quality issues detected![/green]", title="Clean Data", border_style="green", expand=False))

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
    path = _validate_file_path(file_path)

    try:
        # We read just the columns we need to save memory
        required_cols = [col]
        if y_col:
            required_cols.append(y_col)
            
        df = pl.read_csv(str(path), columns=required_cols, infer_schema_length=infer_schema_length)
        
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
    path = _validate_file_path(file_path)

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
        df = pl.read_csv(str(path), columns=[col], n_rows=limit, infer_schema_length=infer_schema_length)
        
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
    in_file = _validate_file_path(input_path)

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
            f"[bold green]Converted[/bold green] [cyan]{input_path}[/cyan] ({in_size}) → "
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

FORMAT_LABELS = {
    "csv": "CSV",
    "tsv": "TSV",
    "parquet": "Parquet",
    "jsonl": "JSONL",
}

@app.command()
def schema(
    file_path: str = typer.Argument(..., help="Path to input dataset file"),
    from_format: Optional[str] = typer.Option(None, "--from", help="Override input format (csv, tsv, parquet, jsonl)"),
    json_output: bool = typer.Option(False, "--json", help="Output schema as raw JSON"),
    infer_schema_length: int = typer.Option(100, "--infer-schema-length", "-n", help="Number of rows to scan for schema inference in text formats"),
):
    """
    Reads dataset header/metadata and infers column types without scanning full rows.
    """
    in_file = _validate_file_path(file_path)

    in_fmt_raw = from_format.lower() if from_format else _infer_format(file_path)
    if not in_fmt_raw or in_fmt_raw not in SUPPORTED_FORMATS:
        console.print(
            f"[bold red]Error:[/bold red] Could not infer input format for '{file_path}'. "
            "Please specify --from (csv, tsv, parquet, jsonl)."
        )
        raise typer.Exit(code=1)
    in_fmt = SUPPORTED_FORMATS[in_fmt_raw]
    format_label = FORMAT_LABELS.get(in_fmt, in_fmt.upper())

    try:
        if in_fmt == "parquet":
            schema_dict = pl.read_parquet_schema(str(in_file))
            rows = pl.scan_parquet(str(in_file)).select(pl.len()).collect()["len"][0]
        elif in_fmt == "tsv":
            lf = pl.scan_csv(str(in_file), separator="\t", infer_schema_length=infer_schema_length)
            schema_dict = lf.collect_schema()
            rows = lf.select(pl.len()).collect()["len"][0]
        elif in_fmt == "jsonl":
            lf = pl.scan_ndjson(str(in_file), infer_schema_length=infer_schema_length)
            schema_dict = lf.collect_schema()
            rows = lf.select(pl.len()).collect()["len"][0]
        else:
            lf = pl.scan_csv(str(in_file), separator=",", infer_schema_length=infer_schema_length)
            schema_dict = lf.collect_schema()
            rows = lf.select(pl.len()).collect()["len"][0]

        if json_output:
            out_data = {
                "file": Path(file_path).name,
                "format": format_label,
                "columns": len(schema_dict),
                "rows": rows,
                "schema": {col: str(dtype) for col, dtype in schema_dict.items()},
            }
            console.print_json(json.dumps(out_data))
        else:
            console.print(f"[bold cyan]File:[/bold cyan] {Path(file_path).name}")
            console.print(f"[bold cyan]Format:[/bold cyan] {format_label}")
            console.print(f"[bold cyan]Columns:[/bold cyan] {len(schema_dict)}")
            console.print(f"[bold cyan]Rows:[/bold cyan] {rows:,}")
            console.print()

            table = Table(title=f"Schema of {Path(file_path).name}")
            table.add_column("#", style="dim", justify="right")
            table.add_column("Column", style="cyan")
            table.add_column("Type", style="magenta")

            for i, (col, dtype) in enumerate(schema_dict.items(), 1):
                table.add_row(str(i), col, str(dtype))

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error inspecting schema:[/bold red] {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()