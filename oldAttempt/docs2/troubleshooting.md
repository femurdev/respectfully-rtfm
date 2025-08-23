# Troubleshooting

Problems you may encounter and how to investigate them.

1) "Port already in use" or server won't bind
- Another process may be listening on the port. Start on a different port, e.g.: `python3 doc_server.py --port 9000`.
- On Unix, run `ss -ltnp` or `lsof -i :8000` to find the process.

2) Empty sidebar / no Python files found
- Ensure you ran the server in the correct directory. If necessary, pass the project path explicitly:
  `python3 doc_server.py /path/to/project`.
- Hidden directories (starting with `.`) and `__pycache__` are skipped by design.

3) Signatures show `<default>` or defaults look incorrect
- `ast.unparse` (used to render default values) is available on Python 3.9+. On older versions the server
  will fall back to a placeholder for complex defaults. Upgrade to Python 3.9+ to improve fidelity.

4) Large projects cause slow startup
- The server parses all `.py` files at startup. For very large repositories this can take time. Consider
  running the server in a subdirectory or adding filtering to `build_docs`.

5) Non-UTF8 files cause read errors
- The server opens files with `encoding='utf-8'`. If your project contains files in other encodings, convert
  them to UTF-8 or handle them in a fork of the parser that detects encoding.

6) Search returns limited or unexpected results
- Search is a simple substring match against recorded titles and the first line of docstrings. It is not
  fuzzy and is not a full-text index.

7) Exposing server on public networks
- By default the server binds to all interfaces. If you intend to run it on a multi-user machine or expose it,
  consider binding to localhost only or using firewall rules.

8) AST parse errors
- If `parse_file` reports an AST parse error, the file may contain syntax invalid for the Python version of the
  running interpreter. Try running `python3 -m py_compile path/to/file.py` to see syntax errors.

If you hit an issue not covered here, open an issue or contribute a fix via the CONTRIBUTING notes.
