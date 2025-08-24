import os
import sys
import importlib.util

SKIP_DIR_NAMES = {
    ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".venv", "venv", "env", ".env", "build", "dist"
}
PY_EXTS = {".py"}


def is_python_file(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in PY_EXTS


def ensure_on_sys_path(path: str):
    if path not in sys.path:
        sys.path.insert(0, path)


def dotted_package_for_file(file_path: str):
    """Infer dotted package name for a given file, if inside a package."""
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


def resolve_relative_import(base_pkg: str, level: int, module: str | None) -> str | None:
    """Resolve relative imports to absolute dotted names."""
    if base_pkg is None:
        return None
    base_parts = base_pkg.split(".")
    if level > len(base_parts):
        return None
    target_base = ".".join(base_parts[:-level]) if level else base_pkg
    if module:
        return f"{target_base}.{module}" if target_base else module
    return target_base or None


def resolve_module_spec(module_name: str):
    """Wrapper around importlib to find a module spec."""
    try:
        return importlib.util.find_spec(module_name)
    except Exception:
        return None
