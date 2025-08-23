import ast
import os
import sys
import tokenize
from io import StringIO
import importlib.util
from collections import deque
from typing import Dict, Any, List, Optional, Tuple, Set


# ---------------------------- Utilities ----------------------------

SKIP_DIR_NAMES = {".git", "__pycache__", ".mypy_cache", ".pytest_cache", ".venv", "venv", "env", ".env", "build", "dist"}
PY_EXTS = {".py"}  # you can add .pyi if you want stubs too


def is_python_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in PY_EXTS


def ensure_on_sys_path(path: str):
    """Add a directory to sys.path if not present."""
    if path not in sys.path:
        sys.path.insert(0, path)


def find_package_root(dir_path: str) -> Tuple[str, Optional[str]]:
    """
    If dir_path is within a Python package (has __init__.py up the chain),
    return (root_dir_added_to_sys_path, dotted_package_name_of_dir).
    If not a package, returns (root_dir, None).
    """
    cur = os.path.abspath(dir_path)
    parts = []
    last_pkg_parent = None

    while True:
        if os.path.isfile(os.path.join(cur, "__init__.py")):
            parts.append(os.path.basename(cur))
            last_pkg_parent = os.path.dirname(cur)
            cur = os.path.dirname(cur)
        else:
            # we've reached the parent that should be on sys.path
            root_dir = cur
            pkg_name = ".".join(reversed(parts)) if parts else None
            return root_dir, pkg_name


def dotted_package_for_file(file_path: str) -> Optional[str]:
    """
    Try to infer dotted package for a file by walking up __init__.py.
    Returns something like 'pkg.subpkg.module' or None if not package.
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


def resolve_relative_import(base_pkg: Optional[str], level: int, module: Optional[str]) -> Optional[str]:
    """
    Resolve a from-import with relative 'level' based on base_pkg.
    Example: base_pkg='pkg.sub', level=1, module='utils' -> 'pkg.utils'
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


# ---------------------- Parsing a single file ----------------------

def parse_file_docs(filepath: str) -> Tuple[Dict[str, Any], List[Tuple[str, int]]]:
    """
    Return (docs_dict, imports_list).
    imports_list = list of (imported_name, lineno) with absolute module names when possible
    (relative handled later in crawl where we know the package context).
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return {"__error__": f"Cannot read {filepath}: {e}"}, []

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"__error__": f"SyntaxError in {filepath}: {e}"}, []

    docs: Dict[str, Any] = {"__module__": ast.get_docstring(tree), "__comments__": []}

    # Track class/function spans to attach comments
    spans: List[Tuple[int, int, str, ast.AST]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((node.lineno, node.end_lineno, f"function:{node.name}", node))
        elif isinstance(node, ast.ClassDef):
            spans.append((node.lineno, node.end_lineno, f"class:{node.name}", node))

    # Collect declared imports (absolute strings; relative handled at crawl-time)
    imports: List[Tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            # keep module, level; expansion is done later when base package is known
            mod = node.module  # can be None
            lvl = getattr(node, "level", 0) or 0
            if node.names:
                for alias in node.names:
                    # store as special token for later resolution
                    name = f"__REL__:{lvl}:{mod or ''}:{alias.name}" if lvl else (f"{mod}.{alias.name}" if mod else alias.name)
                    imports.append((name, node.lineno))
            else:
                # "from X import *"
                name = f"__REL__:{lvl}:{mod or ''}:* " if lvl else (f"{mod}.*" if mod else "*")
                imports.append((name, node.lineno))

    # Attach inline comments
    for tok_type, tok_string, start, _, _ in tokenize.generate_tokens(StringIO(source).readline):
        if tok_type == tokenize.COMMENT:
            line_no = start[0]
            text = tok_string.lstrip("# ").rstrip()
            attached = False
            for s, e, key, node in spans:
                if s <= line_no <= e:
                    if key not in docs:
                        if isinstance(node, ast.ClassDef):
                            docs[key] = {"__doc__": ast.get_docstring(node), "__comments__": []}
                            for item in node.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    docs[key][item.name] = {"__doc__": ast.get_docstring(item), "__comments__": []}
                        else:
                            docs[key] = {"__doc__": ast.get_docstring(node), "__comments__": []}
                    docs[key]["__comments__"].append(text)
                    attached = True
                    break
            if not attached:
                docs["__comments__"].append(text)

    # Also add docstrings for top-level defs/classes that might have no comments
    for s, e, key, node in spans:
        if key not in docs:
            if isinstance(node, ast.ClassDef):
                cls = {"__doc__": ast.get_docstring(node), "__comments__": []}
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        cls[item.name] = {"__doc__": ast.get_docstring(item), "__comments__": []}
                docs[key] = cls
            else:
                docs[key] = {"__doc__": ast.get_docstring(node), "__comments__": []}

    return docs, imports


# ----------------------------- Crawler -----------------------------

class DocCrawler:
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

    def _should_skip_dir(self, d: str) -> bool:
        return os.path.basename(d) in self.skip_dirs

    def _resolve_module(self, module_name: str) -> Optional[importlib.machinery.ModuleSpec]:
        try:
            return importlib.util.find_spec(module_name)
        except Exception:
            return None

    def _enqueue_package_root(self, package_spec: importlib.machinery.ModuleSpec, queue: deque):
        """
        Enqueue all .py files inside a package directory (just the entry points).
        Internal imports will fan out on their own during parsing.
        """
        if not package_spec or not package_spec.origin:
            return
        if not package_spec.origin.endswith("__init__.py"):
            return
        pkg_dir = os.path.dirname(package_spec.origin)
        for root, dirs, files in os.walk(pkg_dir):
            # prune
            dirs[:] = [d for d in dirs if not self._should_skip_dir(os.path.join(root, d))]
            for f in files:
                if is_python_file(f):
                    queue.append(("file", os.path.join(root, f), None))

    def _file_package_context(self, file_path: str) -> Optional[str]:
        return dotted_package_for_file(file_path)

    def crawl_directory(self, directory: str) -> Dict[str, Any]:
        """
        Crawl a project directory, then recursively crawl its entire import dependency tree.
        Returns a dict keyed by file path (and special keys for imports).
        """
        directory = os.path.abspath(directory)
        ensure_on_sys_path(directory)

        results: Dict[str, Any] = {}
        queue: deque = deque()

        # Seed queue with local project files
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not self._should_skip_dir(os.path.join(root, d))]
            for f in files:
                if is_python_file(f):
                    queue.append(("file", os.path.join(root, f), None))

        modules_count = 0

        while queue:
            kind, target, ctx = queue.popleft()

            if modules_count >= self.max_modules:
                results["__warning__"] = f"Max modules limit reached ({self.max_modules})."
                break

            if kind == "file":
                file_path = os.path.abspath(target)
                if file_path in self.visited_files:
                    continue

                try:
                    size = os.path.getsize(file_path)
                    if size > self.max_file_size_bytes:
                        results[file_path] = {"__error__": f"File too large ({size} bytes)"}
                        self.visited_files.add(file_path)
                        continue
                except Exception:
                    pass

                # Parse file
                docs, imports = parse_file_docs(file_path)
                results[file_path] = docs
                self.visited_files.add(file_path)
                modules_count += 1

                # Establish base package context for resolving relatives
                base_pkg = self._file_package_context(file_path)

                # Expand/import fan-out
                if self.follow_dependency_tree:
                    for imp_name, _lineno in imports:
                        resolved_abs = self._normalize_import_name(imp_name, base_pkg)
                        if not resolved_abs:
                            continue
                        self._queue_module_resolution(resolved_abs, results, queue)

            elif kind == "module":
                modname = target
                if modname in self.visited_modules:
                    continue
                self.visited_modules.add(modname)

                spec = self._resolve_module(modname)
                if not spec:
                    results[f"__import__:{modname}"] = "(unresolved)"
                    continue

                # Built-ins / extensions
                if spec.origin in (None, "built-in"):
                    results[f"__import__:{modname}"] = "(built-in)"
                    continue
                if spec.origin.endswith((".so", ".pyd", ".dll")):
                    results[f"__import__:{modname}"] = f"(binary or missing source: {spec.origin})"
                    continue

                if spec.origin.endswith("__init__.py"):
                    # package
                    results[f"__import__:{modname}"] = {"__package__": spec.origin}
                    self._enqueue_package_root(spec, queue)
                elif spec.origin.endswith(".py"):
                    # single file module
                    queue.append(("file", spec.origin, None))
                else:
                    results[f"__import__:{modname}"] = f"(unknown origin: {spec.origin})"

        return results

    def _normalize_import_name(self, raw: str, base_pkg: Optional[str]) -> Optional[str]:
        """
        Convert stored import tokens into absolute module names where possible.
        """
        if raw.startswith("__REL__:"):
            # __REL__:{level}:{module}:{name}
            _, level, module, name = raw.split(":", 3)
            level = int(level)
            module = module or None
            abs_name = resolve_relative_import(base_pkg, level, module)
            if abs_name:
                return f"{abs_name}.{name}" if name and name != "*" else abs_name
            return None
        else:
            # already absolute-ish (could still be subattr like 'pkg.mod.func')
            return raw.split(":")[0]  # strip any stray tokens

    def _queue_module_resolution(self, module_name: str, results: Dict[str, Any], queue: deque):
        """
        Given something like 'numpy.core' or 'os.path', schedule it for resolution.
        Try progressively shorter prefixes because importlib spec works at module/package boundaries.
        """
        # Try the longest → shortest prefix until a spec is found.
        parts = module_name.split(".")
        for i in range(len(parts), 0, -1):
            candidate = ".".join(parts[:i])
            spec = self._resolve_module(candidate)
            if spec:
                # enqueue module (which may enqueue its package files or itself as .py)
                queue.append(("module", candidate, None))
                return
        # If nothing resolved, record as unresolved
        results.setdefault("__unresolved__", set()).add(module_name)


# ----------------------------- Example -----------------------------

if __name__ == "__main__":
    """
    Example usage:
      python doc_crawler.py /path/to/your/project

    Tips:
      - Consider starting with smaller max_modules for huge trees.
      - If your project is a package, run from its parent so the package root is on sys.path.
    """
    import json
    import argparse

    parser = argparse.ArgumentParser(description="Deep documentation crawler (project + dependency tree).")
    parser.add_argument("path", help="Project directory (or a single .py file).")
    parser.add_argument("--max-modules", type=int, default=5000)
    parser.add_argument("--max-file-size", type=int, default=2_000_000, help="Bytes; skip giant files.")
    parser.add_argument("--no-follow", action="store_true", help="Do not follow imports (project only).")
    args = parser.parse_args()

    target = os.path.abspath(args.path)

    crawler = DocCrawler(
        max_modules=args.max_modules,
        max_file_size_bytes=args.max_file_size,
        follow_dependency_tree=not args.no_follow,
    )

    if os.path.isdir(target):
        root_dir, _ = find_package_root(target)
        ensure_on_sys_path(root_dir)
        results = crawler.crawl_directory(target)
    elif os.path.isfile(target) and is_python_file(target):
        root_dir, _ = find_package_root(os.path.dirname(target))
        ensure_on_sys_path(root_dir)
        # Crawl starting from the single file by treating its folder as project
        results = crawler.crawl_directory(os.path.dirname(target))
    else:
        print("Provide a directory or a .py file.")
        sys.exit(1)

    # Convert any sets to lists for JSON-ability
    def _coerce(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

    with open("output", "w") as f:
        json.dump(results, f, default=_coerce, indent=2)
