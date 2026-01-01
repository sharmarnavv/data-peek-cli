# Peek ⚡

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Engine](https://img.shields.io/badge/Engine-Polars_⚡-FF7F00?style=for-the-badge&logo=polars&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Dev-success?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

> **Stop spinning up Jupyter just to check a CSV.**

**Peek** is a blazing fast CLI for data inspection. It is built for developers who live in SSH sessions, hate waiting for heavy IDEs to load, and need to sanity-check a 5GB dataset *now*.

---

## 🚀 The Features

* **⚡ Zero-RAM Overhead:** Powered by **Polars LazyFrames** (Rust). Scan multi-gigabyte files instantly without crashing your terminal.
* **🧠 Heuristic Intelligence:** Automatically detects critical issues like high null rates, constant columns, and potential primary keys.
* **📊 ASCII Visuals:** Render Histograms and Scatter plots directly in the CLI.

---

## 🛠️ Usage

### 1. View Data
Instantly peek at the head or tail of your dataset.

```bash
# View top 10 rows
peek view data.csv

# View the last 5 rows
peek view data.csv --tail --rows 5
```

### 2. Health Check (`describe`)
Get a comprehensive health report with smart warnings (missing data, constants, unique counts).

```bash
peek describe data.csv
```
*Output includes: Missing value %, Type inference, and automated quality warnings.*

### 3. Visualizations (`plot`)
Visualize distributions and correlations without leaving the terminal.

**Histogram / Bar Chart (Single Column)**
```bash
peek plot data.csv --col category
```

**Scatter Plot (Two Columns)**
```bash
peek plot data.csv --col price --y-col rating --title "Price vs Rating"
```

---

## 🏗️ Tech Stack

*   **[Polars](https://pola.rs/)**: The high-performance Rust-based DataFrame engine.
*   **[Typer](https://typer.tiangolo.com/)**: For building the robust CLI interface.
*   **[Rich](https://rich.readthedocs.io/)**: For beautiful tables, panels, and terminal formatting.
*   **[Plotext](https://github.com/piccolomo/plotext)**: For rendering graphs directly in the terminal.
*   **[UV](https://github.com/astral-sh/uv)**: Blazing fast Python package management.
