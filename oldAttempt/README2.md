# PyDocServer

Simple Python documentation web server.

This repository contains a single-file HTTP server (doc_server.py) that scans a directory for Python
files, extracts module/function/class docstrings and signatures using the `ast` module, and serves a
minimal HTML interface with a sidebar and a search bar.

Quick links
- Docs: docs/index.md
- Usage: docs/usage.md
- API / internals: docs/api.md
- Troubleshooting: docs/troubleshooting.md
- Contributing: docs/contributing.md

Getting started

1. Run the server in the project you want documented:

   python3 doc_server.py [path] [--port PORT]

2. Open http://localhost:8000 in your browser.

Project files
- doc_server.py — main server script (single-file) that builds docs and serves the UI.
- README.md — this file.
- docs/ — additional documentation (usage, API, troubleshooting, contributing).

Notes
- The server uses AST parsing only (it does not import or execute your code), so it is safe to run on
  untrusted code bases for documentation generation.
- No external Python packages are required; the server uses only stdlib modules.

If you want to improve the project, see docs/contributing.md for suggestions and guidelines.
