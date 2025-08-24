# pydoccrawler/crawler.py

from __future__ import annotations

import ast
import os
import sys
import importlib.util
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

from .parser import extract_docstrings_and_comments_from_file

# Directories skipped when walking packages/projects
SKIP_DIR_NAMES: Set[str] = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "venv",
    "env",
    ".env",
    "build",
    "dist",
}

PY_EXTS = {".py"}


def _is_python_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in PY_EXTS


def _ensure_on_sys_path(path: str) -> None:
    if path not in sys.path:
        sys.path.insert(0, path)


def _dotted_package_for_file(file_path: str) -> Optional[str]:
    """
    Infer dotted package for a file by walking up __init__.py.
    Returns 'pkg.subpkg.module' or None if not inside a package.
    """
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        return None

    mod_name = os.path.splitext(os.path.basename(file_path))[0]
    cur_dir = os.path.dirname(file_path)

    segments = [mod_name]
    saw_pkg = False
    while True:
        if os.path.isfile(os.path.join(cur_dir, "__init__.py")):
            segments.append(os.path.basename(cur_dir))
            saw_pkg = True
            cur_dir = os.path.dirname(cur_dir)
        else:
            break

    if not saw_pkg:
        return None

    return ".".join(reversed(segments))


def _resolve_relative_import(base_pkg: Optional[str], level: int, module: Optional[str]) -> Optional[str]:
    """
    Resolve 'from .x import y' style imports to absolute dotted names.
    """
    if base_pkg is None:
        return None
    base_parts = base_pkg.split(".")
    if level > len(base_parts):
        return None
    target_base = ".".join(base_parts[:-level]) if level else base_pkg
    if module:
        return f"{target_base}.{module}" if target_base else module
    return target_base or None


class DocCrawler:
    """
    Crawl a project directory and its entire import dependency tree.
    Each parsed file returns a dict of:
      - "__module__": module docstring
      - "__comments__": module-level inline comments
      - "class:Name" / "function:name": nested dicts each with:
          - "__doc__", "__comments__", and (for functions/methods) "signature"
            where signature = {"args": [...], "returns": "..."} from parser

    Additionally records entries like:
      - "__import__:modname": info for packages/modules encountered
      - "__unresolved__": set of import names we couldn't resolve
    """

    def __init__(
        self,
        max_modules: int = 5000,
        max_file_size_bytes: int = 2_000_000,
        follow_dependency_tree: bool = True,
        skip_dirs: Optional[Set[str]] = None,
    ):
        self.max_modules = max_modules
        self.max_file_size_bytes = max_file_size_bytes
        self.follow_dependency_tree = follow_dependency_tree
        self.skip_dirs = set(skip_dirs or set()).union(SKIP_DIR_NAMES)

        self.visited_files: Set[str] = set()
        self.visited_modules: Set[str] = set()

    # ------------------------- Public API -------------------------

    def crawl_directory(self, directory: str) -> Dict[str, Any]:
        """
        Crawl a project directory; if follow_dependency_tree=True,
        recursively explores imported packages and their imports.
        """
        directory = os.path.abspath(directory)
        _ensure_on_sys_path(directory)

        results: Dict[str, Any] = {}
        queue: Deque[Tuple[str, str]] = deque()

        # Seed with local project .py files
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if os.path.basename(d) not in self.skip_dirs]
            for f in files:
                if _is_python_file(f):
                    queue.append(("file", os.path.join(root, f)))

        modules_count = 0

        while queue:
            kind, target = queue.popleft()

            if modules_count >= self.max_modules:
                results.setdefault("__warning__", f"Max modules limit reached ({self.max_modules}).")
                break

            if kind == "file":
                file_path = os.path.abspath(target)
                if file_path in self.visited_files:
                    continue

                try:
                    if os.path.getsize(file_path) > self.max_file_size_bytes:
                        results[file_path] = {"__error__": f"File too large (> {self.max_file_size_bytes} bytes)"}
                        self.visited_files.add(file_path)
                        continue
                except OSError:
                    # Still try to read
                    pass

                # Parse docs/comments/signatures via parser
                try:
                    docs = extract_docstrings_and_comments_from_file(file_path)
                except Exception as e:
                    docs = {"__error__": f"Parse error: {e}"}

                results[file_path] = docs
                self.visited_files.add(file_path)
                modules_count += 1

                # Expand imports from this file if following the dependency tree
                if self.follow_dependency_tree:
                    base_pkg = _dotted_package_for_file(file_path)
                    for imp_token in self._collect_imports(file_path):
                        abs_name = self._normalize_import_name(imp_token, base_pkg)
                        if not abs_name:
                            continue
                        self._enqueue_module(abs_name, results, queue)

            elif kind == "module":
                modname = target
                if modname in self.visited_modules:
                    continue
                self.visited_modules.add(modname)

                spec = self._resolve_module_spec(modname)
                if not spec:
                    results[f"__import__:{modname}"] = "(unresolved)"
                    continue

                origin = spec.origin

                # Built-ins / namespace pkgs / extensions without .py
                if origin in (None, "built-in"):
                    results[f"__import__:{modname}"] = "(built-in)"
                    continue
                if origin.endswith((".so", ".pyd", ".dll")):
                    results[f"__import__:{modname}"] = f"(binary or missing source: {origin})"
                    continue

                # Package
                if spec.submodule_search_locations:
                    pkg_dir = list(spec.submodule_search_locations)[0]
                    results[f"__import__:{modname}"] = {"__package__": os.path.join(pkg_dir, "__init__.py")}
                    for root, dirs, files in os.walk(pkg_dir):
                        dirs[:] = [d for d in dirs if os.path.basename(d) not in self.skip_dirs]
                        for f in files:
                            if _is_python_file(f):
                                queue.append(("file", os.path.join(root, f)))
                    continue

                # Single-file module
                if origin.endswith(".py"):
                    queue.append(("file", origin))
                    continue

                # Fallback
                results[f"__import__:{modname}"] = f"(unknown origin: {origin})"

        return results

    # ----------------------- Internal helpers -----------------------

    def _resolve_module_spec(self, module_name: str):
        try:
            return importlib.util.find_spec(module_name)
        except Exception:
            return None

    def _collect_imports(self, file_path: str) -> List[str]:
        """
        Return list of import tokens for a file.
        - Absolute: 'package.subpackage.module'
        - Relative tokenized: '__REL__:<level>:<module or empty>:<name or *>'
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return []

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)  # e.g., 'os', 'numpy.linalg'
            elif isinstance(node, ast.ImportFrom):
                lvl = getattr(node, "level", 0) or 0
                mod = node.module or ""
                if node.names:
                    for alias in node.names:
                        if lvl:
                            imports.append(f"__REL__:{lvl}:{mod}:{alias.name}")
                        else:
                            imports.append(f"{mod}.{alias.name}" if mod else alias.name)
                else:
                    # from X import *  (rare, but handle)
                    if lvl:
                        imports.append(f"__REL__:{lvl}:{mod}:*")
                    else:
                        imports.append(f"{mod}.*" if mod else "*")
        return imports

    def _normalize_import_name(self, raw: str, base_pkg: Optional[str]) -> Optional[str]:
        """
        Normalize stored import tokens into absolute module names where possible.
        """
        if raw.startswith("__REL__:"):
            # Structure: '__REL__:<level>:<module or empty>:<name>'
            try:
                _, level_s, module, name = raw.split(":", 3)
                level = int(level_s)
            except Exception:
                return None
            module = module or None
            abs_name = _resolve_relative_import(base_pkg, level, module)
            if not abs_name:
                return None
            return f"{abs_name}.{name}" if name and name != "*" else abs_name
        else:
            # Absolute-ish: may include attributes; take the module-ish prefix
            return raw.split(":")[0]

    def _enqueue_module(self, module_name: str, results: Dict[str, Any], queue: Deque[Tuple[str, str]]) -> None:
        """
        Try longest→shortest dotted prefixes to find a real module/package to enqueue.
        """
        parts = module_name.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            spec = self._resolve_module_spec(candidate)
            if spec:
                queue.append(("module", candidate))
                return
        results.setdefault("__unresolved__", set()).add(module_name)
