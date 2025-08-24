# rtfmlib — Python Doc Crawler and Docsite Generator

This repository contains a lightweight Python tool for crawling a Python codebase, extracting docstrings, inline comments, and function signatures, and producing a browsable documentation site or exportable Markdown/JSON. It is a refactor/continuation of an earlier pydoccrawler-like project.

Features

- Crawl a project directory and optionally follow the import dependency tree
- Extract module, class, function, and method docstrings
- Attach inline comments to surrounding code elements when possible
- Extract function signatures (arguments, types, defaults, return type)
- Export entire documentation as Markdown or JSON
- Simple Streamlit app for interactive browsing (main.py)
- CLI entrypoint (rtfmlib/cli.py)

Quick start

1. Install dependencies:

   python3 -m pip install -r requirements.txt

   If you only want the Streamlit app, install streamlit separately:

   python3 -m pip install streamlit

2. Run the Streamlit app:

   streamlit run main.py

3. Or use the CLI:

   python3 -m rtfmlib.cli /path/to/project

Project layout

- main.py — Streamlit web app to crawl and browse doc output
- rtfmlib/
  - crawler.py — project crawler that walks files and imports
  - parser.py — AST-based extractor for docstrings, comments, signatures
  - utils.py — utility helpers for path/package resolution
  - cli.py — command-line wrapper

Notes & Limitations

- Signature extraction uses ast.unparse and may fail on complex annotations in older Python versions.
- Inline comment attachment heuristics are simple: comments within a node's lineno..end_lineno are associated with that node.
- When following the dependency tree, extension modules and built-ins are recorded but not parsed.

Contributing

Contributions welcome. Please open issues or PRs. For local development, `pip install -e .` is recommended.
