pydocgen - Usage
===============

Overview
--------
pydocgen parses Python source code (without importing or running it) and produces documentation in several formats or serves a live web UI. It is designed to be safe (no code execution) and reasonably efficient for large codebases.

CLI
---

python3 pydocgen.py [options]

Options:
  --path PATH            Path to a file or package directory (defaults to current working dir)
  --format {web,json,md} Output format. 'web' starts a live server. Default is 'web'.
  --output DIR           Output directory for export formats. If omitted exports print to stdout.
  --include-private      Include single-leading-underscore members (dunders are always excluded).
  --style {auto,google,numpy,rest,plain}
  --host HOST            When running web server, host to bind to (default 127.0.0.1)
  --port PORT            Port for web server (default 5000)
  --interval FLOAT       Polling interval (seconds) for the server to detect changes (default 5.0)

Examples
--------

Export JSON for a package and print to stdout:

    python3 pydocgen.py --path ./mypkg --format json

Export markdown and write to a directory:

    python3 pydocgen.py --path ./mypkg --format md --output docs

Start the live web server for the current directory:

    python3 pydocgen.py --format web

Notes
-----
- The parser only extracts simple literal module-level constants (numbers, strings, tuples, lists, dicts of literals). Complex expressions are skipped for safety.
- Docstring parsing heuristic supports Google, NumPy and reST-like styles. Use --style to force a particular parser.
- The web server serves JSON and simple HTML templates from memory and does not write runtime files to disk.
