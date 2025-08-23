# PyDocServer documentation

Overview

PyDocServer is a lightweight documentation web server for Python projects. It walks a project tree,
parses `.py` files using Python's `ast` module, extracts module/class/function docstrings and
signatures, and serves browsable HTML including a sidebar and a search bar.

Key features
- Safe parsing via `ast` (no code execution)
- Sidebar listing files grouped by directory
- Server-side search endpoint (`/search`) with a simple substring match
- View generated documentation and raw source files in the browser

See the other docs for details and usage examples:
- Usage: docs/usage.md
- API / internals: docs/api.md
- Troubleshooting: docs/troubleshooting.md
- Contributing: docs/contributing.md
