# API Reference

This file documents the public API of the rtfmlib package.

DocCrawler

- DocCrawler(max_modules=5000, max_file_size_bytes=2_000_000, follow_dependency_tree=True, skip_dirs=None)

  - crawl_directory(directory: str) -> dict
    Recursively traverse a directory, parse Python files, and (optionally) follow imports. Returns a dictionary structure described in docs/usage.md.

Parser functions

- extract_docstrings_and_comments_from_source(source: str) -> dict
  Parse a Python source string and return extracted docstrings, inline comments, and function signatures.

- extract_docstrings_and_comments_from_file(filepath: str) -> dict
  Read a file and call the above function.

Utilities

- is_python_file(path: str) -> bool
- ensure_on_sys_path(path: str)
- dotted_package_for_file(file_path: str) -> Optional[str]
- resolve_relative_import(base_pkg: str, level: int, module: str | None) -> Optional[str]
- resolve_module_spec(module_name: str) -> Optional[importlib.machinery.ModuleSpec]

