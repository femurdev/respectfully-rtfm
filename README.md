pydocgen
=======

pydocgen is a lightweight, AST-based Python documentation generator and live web server. It parses Python source files using the standard library ast module (no imports or execution of user code) and exposes searchable, browsable documentation via a dynamic web UI that does not write web page files at runtime.

Key features
------------
- Single CLI entrypoint: pydocgen.py
- Web server mode (--format web): serves documentation dynamically without writing files
- Export modes: --format json or --format md to print or save exported docs
- AST-based parsing (no importing/executing user code)
- Extracts modules, classes, functions, methods with fully-qualified names and signatures (type hints + defaults where available)
- Captures module-level simple constants (literal values)
- Supports Google-style, NumPy-style and reST docstring heuristics (--style auto)
- Live updates: background scanner detects file changes and updates docs
- Simple search (inverted index) and pagination-ready endpoints

Security and performance
------------------------
- The parser never imports or executes user code; it relies on ast only to avoid side effects.
- Designed to handle large codebases (thousands of files) by keeping in-memory models compact and scanning incrementally.

Usage
-----

Basic CLI:

python3 pydocgen.py --path /path/to/project --format web

Common options:
- --path PATH      Project root to scan (defaults to current working directory)
- --format {web,json,md}
- --output DIR     When used with --format json/md to save files; otherwise printed to stdout
- --include-private Include single-leading-underscore members (dunders are always excluded)
- --style {auto,google,numpy,rest}

Run the web server (default to localhost:5000):

python3 pydocgen.py --path . --format web

Export JSON to stdout:

python3 pydocgen.py --path . --format json

Development notes
-----------------
- Key files:
  - docgen.py      AST parser and doc model builder
  - live_web_server.py  Flask-based (lazy import) server and DocCache
  - pydocgen.py    CLI entrypoint and exporters
  - utils.py       logging and helpers

- The web UI is simple and intentionally serves JSON metadata for module lists; details are fetched lazily via endpoints to keep initial payloads small.
- The DocCache implements a fingerprint strategy (sha1 of relative path + mtime pairs) to detect changes efficiently.

Limitations and roadmap
-----------------------
- Signature rendering: handles posonly/kwonly/varargs but some edge-cases remain (decorator semantics, exotic annotations). We'll incrementally improve the signature builder.
- Docstring parsing: heuristic parsers for Google/NumPy/reST are implemented but should be hardened with tests.
- Search: currently a simple inverted index; we will add better tokenization, ranking, and pagination for huge projects.
- Testing & CI: add unit tests for parser edge-cases and server endpoints in future iterations.

Contributing
------------
Contributions welcome. Please open issues or PRs with improvements or bug reports.

License
-------
MIT
