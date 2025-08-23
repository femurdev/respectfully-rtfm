# API / Internals

This document describes the main parts of `doc_server.py` so you can extend or modify the server.

Main components

- parse_file(path)
  - Parses a Python file using `ast.parse` and returns a dict containing:
    - module_doc: module-level docstring
    - entries: list of top-level entries (functions, classes, variables) with signatures and docstrings
    - source: full source text
  - Returns `{'_error': <message>}` on file read or parse errors.

- get_signature_from_args(node)
  - Builds a readable signature string from an `ast.FunctionDef` or `ast.AsyncFunctionDef` node.
  - Uses `ast.unparse` when available to render default values; falls back to a placeholder otherwise.

- build_docs(root)
  - Walks the project tree under `root`, parses all `.py` files with `parse_file`, and builds two things:
    - docs_map: mapping from relative posix path (e.g. `package/module.py`) to parsed dict
    - search_index: simple list of searchable items {title, path, snippet}

- DocHandler (http.server.BaseHTTPRequestHandler)
  - Serves endpoints:
    - `/` : index / README
    - `/doc/<path>` : generated documentation page for a file
    - `/source/<path>` : raw source view
    - `/search?q=...` : JSON search API (substring match across titles/snippets)

Templates and assets
- The HTML, CSS and JavaScript are embedded as strings in the server; there are no external assets.
- The client-side search box calls `/search?q=...` and renders results below the content area.

Extending the server
- Add markdown rendering: integrate a markdown renderer (e.g., `markdown` package) and render README and
  docstrings as HTML before embedding into the templates.
- Syntax highlighting: integrate `pygments` (server-side) or serve a client-side highlighter such as
  highlight.js and add appropriate classes to code blocks.
- Live reloading: implement a file watcher (watchdog) that rebuilds `docs_map` and `search_index` when files change.

Security considerations
- The current server does not execute project code. Avoid adding features that import or run project modules
  unless you explicitly sandbox or otherwise limit execution.

