import os
import logging

# Configure basic logging for the package
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def is_text_file(file_path, blocksize=4096):
    """Check if a file is a text file by reading a small block.

    This avoids loading entire files into memory for large files and
    is more efficient than reading the whole file.
    """
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(blocksize)
            # If we find a NULL byte it's very likely a binary file
            if b"\x00" in chunk:
                return False
            # Try to decode chunk as utf-8; if it fails, it's not a text file
            try:
                chunk.decode('utf-8')
                return True
            except UnicodeDecodeError:
                return False
    except (IOError, OSError) as e:
        logger.debug("is_text_file error for %s: %s", file_path, e)
        return False


def log_error(file_path, error):
    """Log errors with details to the configured logger.

    Accepts a file_path (or other identifier) and an exception or message.
    """
    logger.error("Error in %s: %s", file_path, error)


def generate_error_summary(errors):
    """Generate a summary for skipped files and errors.

    `errors` should be an iterable of (file_path, error_message) tuples.
    """
    if not errors:
        return "No errors encountered."

    summary_lines = ["Error Summary:\n"]
    for file_path, error in errors:
        summary_lines.append(f"File: {file_path}, Error: {error}\n")
    return ''.join(summary_lines)
