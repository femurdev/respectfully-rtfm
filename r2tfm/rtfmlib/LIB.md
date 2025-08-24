# pydoccrawler

`pydoccrawler` is a Python library and CLI tool for **deeply crawling Python projects and their dependencies**.
It extracts:

- **Docstrings** (module, class, function/method level)
- **Inline comments** (attached to code spans or floating)
- **Imports** (absolute and relative, recursively resolved through the dependency tree)

---

## Features

- Recursively parses Python source files (`.py`).
- Resolves **relative and absolute imports** to actual files/packages.
- Crawls **entire dependency trees**, including installed external libraries.
- Handles large projects safely with:
  - `--max-modules` limit
  - `--max-file-size` limit
- Skips virtualenvs, cache directories, and build artifacts by default.
- Usable as both a **Python API** and a **command-line tool**.

---

## Installation

```bash
pip install -e .
```

---

## Usage (CLI)

```bash
pydoccrawler ./my_project --max-modules 2000
```

Options:
- `--max-modules`: Maximum number of modules to crawl (default `5000`).
- `--max-file-size`: Skip files larger than this (default `2MB`).
- `--no-follow`: Disable dependency tree traversal.

---

## Usage (Library)

```python
from pydoccrawler import DocCrawler

crawler = DocCrawler(max_modules=1000)
docs = crawler.crawl_directory("./my_project")

print(docs.keys())  # file paths and module references
```

---

## Project Structure

```
pydoccrawler/
├── __init__.py     # exports main API
├── crawler.py      # DocCrawler class, BFS traversal of dependency tree
├── parser.py       # file-level parser (docstrings, comments, imports)
├── utils.py        # helper functions (import resolution, paths)
└── cli.py          # CLI entrypoint
```

---

## Example Output

```json
{
  "my_project/main.py": {
    "__module__": "Main entry point",
    "__comments__": ["TODO: refactor"],
    "function:run": {
      "__doc__": "Start the app",
      "__comments__": []
    }
  },
  "__import__:numpy": {
    "__package__": "/usr/local/lib/python3.11/site-packages/numpy/__init__.py"
  }
}
```

---
