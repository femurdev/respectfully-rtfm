"""Small utility helpers used by rtfmlib.

This module provides light-weight logging and file helpers that are safe
for library consumption (no global side-effects beyond setting up a
module logger).
"""

import logging
from typing import Iterable, Tuple

logger = logging.getLogger("rtfmlib")
if not logger.handlers:
    # configure only if not configured by the application
    h = logging.StreamHandler()
    fmt = logging.Formatter('%(levelname)s: %(message)s')
    h.setFormatter(fmt)
    logger.addHandler(h)
    logger.setLevel(logging.WARNING)


def is_text_file(file_path: str, blocksize: int = 4096) -> bool:
    """Heuristically check whether a file is text by sampling a small block.

    Returns False for binary-like files (contains NUL) or when the sample
    cannot be decoded as UTF-8.
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(blocksize)
            if b"\x00" in chunk:
                return False
            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
    except (OSError, IOError):
        return False


def generate_error_summary(errors: Iterable[Tuple[str, str]]) -> str:
    """Return a short string summary for an iterable of (path, message).

    Useful for reporting skipped files.
    """
    errors = list(errors)
    if not errors:
        return "No errors encountered."
    lines = ["Error Summary:\n"]
    for p, e in errors:
        lines.append(f"File: {p}, Error: {e}\n")
    return ''.join(lines)
