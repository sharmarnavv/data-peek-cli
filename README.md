# Peek ⚡

![Status](https://img.shields.io/badge/Status-Work_in_Progress-yellow) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue)

**Stop spinning up Jupyter just to check a CSV.**

**Peek** is a blazing fast command-line interface (CLI) tool that generates comprehensive health reports and statistical summaries for your datasets directly in the terminal. Designed for developers working on remote servers, SSH connections, or anyone who hates waiting for IDEs to load.

> 🚧 **Under Construction:** This project is currently in active development.

## 🚀 Why Peek?

* **Instant Analysis:** Check columns, data types, and null values in milliseconds.
* **Remote Ready:** Perfect for SSH workflows where GUI tools (Excel/VS Code) aren't an option.
* **Memory Safe:** Smart chunking logic handles multi-gigabyte files without crashing your RAM.
* **Beautiful UI:** Powered by [Rich](https://github.com/Textualize/rich) for readable, formatted terminal output.

## 🛠 Roadmap

- [x] **Core:** Project structure & CLI scaffolding (`typer`)
- [ ] **Health Check:** `peek describe` for missing values and type inference.
- [ ] **Quick View:** `peek view` to inspect head/tail of data.
- [ ] **Visuals:** `peek plot` for terminal-based histograms (`plotext`).
- [ ] **Packaging:** Release to PyPI.

## 📦 Installation (Coming Soon)

```bash
pip install data-peek-cli