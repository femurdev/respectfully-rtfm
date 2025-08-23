# __init__.py

rtfmlib - lightweight refactor of pydocgen components

This package provides:
- DocGenerator: simple AST-based parser for Python modules/packages
- parse_file: convenience for single-file parsing
- DocCache: thread-safe cache with mtime fingerprinting, inverted index and search
- utils: small helpers

This is a compact, library-oriented rewrite of the repository's docgen and live_web_server code.