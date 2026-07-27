# Peek ⚡

[![PyPI](https://img.shields.io/pypi/v/peek-cli?style=for-the-badge&color=blue)](https://pypi.org/project/peek-cli/)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Engine](https://img.shields.io/badge/Engine-Polars_⚡-FF7F00?style=for-the-badge&logo=polars&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Dev-success?style=for-the-badge)

> **Stop spinning up Jupyter just to check a dataset.**

**Peek** is a lightning-fast CLI for dataset inspection, schema inference, format conversion, and quality profiling. It is built for developers and data engineers who live in the terminal and need to sanity-check multi-gigabyte datasets instantly.

---

## 🚀 Key Features

* **⚡ Zero-RAM Overhead:** Powered by **Polars LazyFrames** (Rust). Process multi-gigabyte datasets instantly out-of-core.
* **🔄 Fast Native Conversion:** Convert seamlessly between **CSV**, **TSV**, **Parquet**, and **JSONL** using Polars streaming.
* **📋 Instant Schema Inspection:** Read metadata and column types in $O(1)$ time without scanning full data pages.
* **🧠 Heuristic Intelligence:** Automatically detects data quality issues like high null rates, constant columns, and primary key candidates alongside `Min`, `Max`, and `Avg` stats.
* **📊 Terminal Visuals:** Render histograms, bar charts, and scatter plots directly in your terminal.

---

## 📥 Installation

```bash
# Default lightweight installation
pip install peek-cli
# or with uv
uv pip install peek-cli

# With optional NLP sentiment analysis support
pip install "peek-cli[nlp]"
# or with uv
uv pip install "peek-cli[nlp]"
```

---

## 🛠️ Usage

### 1. View Data (`view`)
Peek at the head or tail of your dataset.

```bash
# View top 10 rows
peek view data.csv

# View the last 5 rows
peek view data.parquet --tail --rows 5
```

### 2. Instant Schema Inspection (`schema`)
Read header metadata and infer column data types without reading full data rows.

```bash
# Inspect schema (CSV, TSV, Parquet, JSONL)
peek schema data.parquet

# Output raw JSON schema for shell scripts & jq
peek schema data.csv --json

# Override format on files without standard extensions
peek schema raw_data --from csv
```

### 3. Health Check & Profiling (`describe`)
Generate a comprehensive health report with summary statistics (`Min`, `Max`, `Avg`, `Missing %`, `Unique Count`) and automated quality warnings.

```bash
peek describe dataset.parquet
```

### 4. Fast Dataset Conversion (`convert`)
Instantly convert between **CSV**, **TSV**, **Parquet** (with `zstd` compression), and **JSONL** using Polars streaming sinks.

```bash
# Convert CSV to Parquet
peek convert data.csv data.parquet

# Convert Parquet to JSONL
peek convert data.parquet data.jsonl

# Omit output path (automatically outputs input.parquet)
peek convert data.csv --to parquet

# Overwrite existing files with --force
peek convert data.tsv data.csv -f
```

### 5. Visualizations (`plot`)
Visualize distributions and correlations directly in the terminal.

**Histogram / Bar Chart (Single Column)**
```bash
peek plot data.csv --col category
```

**Scatter Plot (Two Columns)**
```bash
peek plot data.csv --col price --y-col rating --title "Price vs Rating"
```

### 6. Sentiment Analysis (`sentiment`)
Analyze sentiment distribution (Positive / Neutral / Negative) on a text column using VADER *(requires `peek-cli[nlp]`)*.

```bash
peek sentiment reviews.csv --col review_text
```

---

## 🏗️ Tech Stack

* **[Polars](https://pola.rs/)**: High-performance Rust DataFrame engine.
* **[Typer](https://typer.tiangolo.com/)**: Fast, intuitive CLI argument parser.
* **[Rich](https://rich.readthedocs.io/)**: Modern terminal tables, panels, and formatting.
* **[Plotext](https://github.com/piccolomo/plotext)**: ASCII graph rendering directly in the CLI.
* **[UV](https://github.com/astral-sh/uv)**: Ultra-fast Python package management.
