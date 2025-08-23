# Usage

Requirements
- Python 3.7+ (recommended 3.9+ to get better signature rendering via `ast.unparse`)

Run the server

From the command line, in the project you want to document (or pass the path):

- Serve the current directory on the default port (8000):

  python3 doc_server.py

- Serve a specific directory on port 9000:

  python3 doc_server.py /path/to/project --port 9000

CLI options
- path (optional): Path to project root to scan (defaults to current directory).
- --port / -p: Port number to serve on (default 8000).

What the server provides
- Home page: shows README if present, or a brief intro.
- Sidebar: lists all discovered `.py` files grouped by directory. Click an item to view documentation.
- Documentation pages: show module docstring, top-level functions and classes with signatures and docstrings,
  and a short source excerpt.
- Source viewer: full source shown under /source/<path>
- Search: type in the search box; the client queries `/search?q=...` and shows results.

Examples
- View docs for a module: http://localhost:8000/doc/path/to/module.py
- View the raw source: http://localhost:8000/source/path/to/module.py
- Direct search example: http://localhost:8000/search?q=parse

Stopping the server
- Use Ctrl-C in the terminal where the server is running.

Notes
- The server is intended for local use. It binds to 0.0.0.0 by default so you can access from other hosts
  on your network — be mindful of exposing code on shared networks.
