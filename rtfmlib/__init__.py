"""rtfmlib - lightweight refactor of pydocgen components

This package provides:
- DocGenerator: simple AST-based parser for Python modules/packages
- parse_file: convenience for single-file parsing
- DocCache: thread-safe cache with mtime fingerprinting, inverted index and search
- utils: small helpers

This is a compact, library-oriented rewrite of the repository's docgen and live_web_server code.
"""

from .docgen import DocGenerator, parse_file
from .server import DocCache
from . import utils

__all__ = ["DocGenerator", "parse_file", "DocCache", "utils"]
__version__ = "0.1.0"
