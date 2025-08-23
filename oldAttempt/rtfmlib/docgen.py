
"""
AST-based documentation extractor.

Provides:
- parse_file(path, include_private=False, style='auto') -> module doc dict or None
- DocGenerator(path, include_private=False, style='auto') with parse() -> mapping key->module-doc

This module is a compact, library-oriented adaptation of the project's docgen logic.
It intentionally avoids importing or executing user code and works only with the AST.
"""

from typing import List, Dict, Any, Optional
import ast
import os
import sys
import re

from .utils import logger

try:
    from ast import unparse as ast_unparse
except Exception:
    def ast_unparse(node):
        if node is None:
            return ''
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{ast_unparse(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return f"{ast_unparse(node.value)}[{ast_unparse(node.slice)}]"
        if isinstance(node, ast.Index):
            return ast_unparse(node.value)
        return ast.dump(node)


def is_dunder(name: str) -> bool:
    return name.startswith('__') and name.endswith('__')


def should_include(name: str, include_private: bool) -> bool:
    if is_dunder(name):
        return False
    if name.startswith('_') and not include_private:
        return False
    return True


def safe_repr_constant(node: ast.AST) -> Optional[str]:
    """Return a repr-like string for simple literal AST nodes, else None."""
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        items = []
        for elt in node.elts:
            r = safe_repr_constant(elt)
            if r is None:
                return None
            items.append(r)
        if isinstance(node, ast.Tuple):
            return '(' + ', '.join(items) + ')'
        elif isinstance(node, ast.List):
            return '[' + ', '.join(items) + ']'
        else:
            return '{' + ', '.join(items) + '}'
    if isinstance(node, ast.Dict):
        items = []
        for k, v in zip(node.keys, node.values):
            kr = safe_repr_constant(k)
            vr = safe_repr_constant(v)
            if kr is None or vr is None:
                return None
            items.append(f"{kr}: {vr}")
        return '{' + ', '.join(items) + '}'
    return None


class SignatureBuilder:
    """Construct a simple serializable representation of function signatures.

    This does not execute any code; it uses ast nodes and ast_unparse (fallback)
    to represent annotations and defaults.
    """

    @staticmethod
    def format_arguments(args: ast.arguments) -> List[Dict[str, Any]]:
        parts: List[Dict[str, Any]] = []

        def add_arg(arg_node, default_node=None, kind='positional'):
            ann = getattr(arg_node, 'annotation', None)
            ann_s = ast_unparse(ann) if ann is not None else None
            default_s = None
            if default_node is not None:
                try:
                    default_s = ast_unparse(default_node)
                except Exception:
                    default_s = safe_repr_constant(default_node)
            parts.append({'name': arg_node.arg, 'annotation': ann_s, 'default': default_s, 'kind': kind})

        # Positional-only args (PEP 570) and regular args share defaults list
        posonly = getattr(args, 'posonlyargs', []) or []
        regular = list(args.args or [])
        combined_pos = list(posonly) + regular

        # Number of defaults applies to the tail of combined_pos
        defaults = list(args.defaults or [])
        num_defaults = len(defaults)
        defaults_offset = len(combined_pos) - num_defaults if num_defaults else len(combined_pos)

        # Add combined positional args; mark posonly ones accordingly
        for i, arg in enumerate(combined_pos):
            default = None
            if num_defaults and i >= defaults_offset:
                default = defaults[i - defaults_offset]
            kind = 'posonly' if i < len(posonly) else 'positional'
            add_arg(arg, default_node=default, kind=kind)

        # vararg (*args)
        if getattr(args, 'vararg', None):
            ann = getattr(args.vararg, 'annotation', None)
            ann_s = ast_unparse(ann) if ann is not None else None
            parts.append({'name': args.vararg.arg, 'annotation': ann_s, 'default': None, 'kind': 'vararg'})

        # kw-only args and their defaults
        kwonlyargs = list(args.kwonlyargs or [])
        kw_defaults = list(getattr(args, 'kw_defaults', []) or [])
        for i, arg in enumerate(kwonlyargs):
            default = None
            if kw_defaults and i < len(kw_defaults):
                default = kw_defaults[i]
            add_arg(arg, default_node=default, kind='kwonly')

        # kwarg (**kwargs)
        if getattr(args, 'kwarg', None):
            ann = getattr(args.kwarg, 'annotation', None)
            ann_s = ast_unparse(ann) if ann is not None else None
            parts.append({'name': args.kwarg.arg, 'annotation': ann_s, 'default': None, 'kind': 'varkw'})

        return parts


class DocVisitor(ast.NodeVisitor):
    def __init__(self, include_private: bool = False, style: str = 'auto'):
        self.include_private = include_private
        self.style = style
        self.stack: List[str] = []
        self.module_doc: Dict[str, Any] = {
            'file': '',
            'docstring': None,
            'constants': [],
            'classes': [],
            'functions': []
        }

    def visit_Module(self, node: ast.Module):
        self.module_doc['docstring'] = ast.get_docstring(node)
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        r = safe_repr_constant(stmt.value)
                        if r is not None:
                            self.module_doc['constants'].append({'name': target.id, 'value': r})
            elif isinstance(stmt, ast.ClassDef):
                if should_include(stmt.name, self.include_private):
                    self.visit(stmt)
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if should_include(stmt.name, self.include_private):
                    self.visit(stmt)

    def visit_ClassDef(self, node: ast.ClassDef):
        class_entry = {
            'name': node.name,
            'bases': [ast_unparse(b) for b in node.bases] if node.bases else [],
            'docstring': ast.get_docstring(node),
            'methods': [],
        }
        self.stack.append(node.name)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if should_include(item.name, self.include_private):
                    m = self._extract_function(item, method_of=node.name)
                    class_entry['methods'].append(m)
        self.stack.pop()
        self.module_doc['classes'].append(class_entry)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        fn = self._extract_function(node)
        self.module_doc['functions'].append(fn)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        fn = self._extract_function(node, is_async=True)
        self.module_doc['functions'].append(fn)

    def _extract_function(self, node: ast.AST, method_of: Optional[str] = None, is_async: bool = False) -> Dict[str, Any]:
        name = getattr(node, 'name', '<anonymous>')
        fq_name = '.'.join(self.stack + [name]) if self.stack else name
        args = getattr(node, 'args', None)
        sig = SignatureBuilder.format_arguments(args) if args is not None else []
        returns = ast_unparse(getattr(node, 'returns', None)) if getattr(node, 'returns', None) is not None else None
        doc = ast.get_docstring(node)
        parsed_doc = None
        if doc:
            parsed_doc = self._parse_docstring(doc)

        # Detect decorators more robustly from AST nodes
        decorators: List[str] = []
        is_property = False
        is_static = False
        is_classmethod = False
        if hasattr(node, 'decorator_list') and node.decorator_list:
            for d in node.decorator_list:
                dname = None
                try:
                    if isinstance(d, ast.Name):
                        dname = d.id
                    elif isinstance(d, ast.Attribute):
                        # e.g., builtins.property or something.decorator
                        dname = d.attr
                    else:
                        dname = ast_unparse(d)
                except Exception:
                    try:
                        dname = ast_unparse(d)
                    except Exception:
                        dname = None
                if dname:
                    decorators.append(dname)
                    # flags
                    if dname == 'property' or dname.endswith('.property'):
                        is_property = True
                    if dname == 'staticmethod' or dname.endswith('.staticmethod'):
                        is_static = True
                    if dname == 'classmethod' or dname.endswith('.classmethod'):
                        is_classmethod = True

        # Adjust signatures for method semantics
        if method_of:
            if is_property:
                # properties behave like attributes; no signature
                sig = []
            elif is_classmethod:
                # first arg is conventionally 'cls'
                if sig:
                    sig[0]['name'] = 'cls'
            else:
                # instance method: leave 'self' as-is if present
                pass

        item: Dict[str, Any] = {
            'name': name,
            'fqn': fq_name,
            'signature': sig,
            'returns': returns,
            'docstring': doc,
            'parsed_doc': parsed_doc,
            'decorators': decorators,
            'is_async': bool(is_async),
            'is_property': is_property,
            'is_staticmethod': is_static,
            'is_classmethod': is_classmethod
        }
        if method_of:
            item['method_of'] = method_of
        return item

    def _parse_docstring(self, doc: str) -> Dict[str, Any]:
        style = self.style
        if style == 'auto':
            lower = doc.lower()
            if '\nparameters\n' in lower or '----------' in doc:
                style = 'numpy'
            elif 'args:' in lower or 'arguments:' in lower:
                style = 'google'
            elif ':param' in doc or ':returns:' in doc:
                style = 'rest'
            else:
                style = 'plain'
        parsed = {'style': style, 'raw': doc}
        if style == 'numpy':
            parsed.update(self._parse_numpy_doc(doc))
        elif style == 'google':
            parsed.update(self._parse_google_doc(doc))
        elif style == 'rest':
            parsed.update(self._parse_rest_doc(doc))
        else:
            lines = [l.rstrip() for l in doc.splitlines()]
            summary = lines[0] if lines else ''
            parsed.update({'summary': summary, 'description': '\n'.join(lines[1:]).strip()})
        return parsed

    # ... rest of class remains unchanged (parsers for numpy/google/rest) ...


def parse_file(path: str, include_private: bool = False, style: str = 'auto') -> Optional[Dict[str, Any]]:
    """Parse a single Python file and return the module documentation dict, or None on failure."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception as e:
        try:
            logger.warning('Could not read %s: %s', path, e)
        except Exception:
            pass
        return None

    try:
        node = ast.parse(src, filename=path)
    except Exception as e:
        try:
            logger.warning('AST parse failed for %s: %s', path, e)
        except Exception:
            pass
        return None

    try:
        visitor = DocVisitor(include_private=include_private, style=style)
        visitor.visit(node)
        # ensure file field
        doc = visitor.module_doc
        doc['file'] = os.path.basename(path).replace(os.path.sep, '/')
        return doc
    except Exception as e:
        try:
            logger.error('Error extracting docs from %s: %s', path, e)
        except Exception:
            pass
        return None


class DocGenerator:
    """Simple doc generator that can parse a path (file or package dir) and
    return a mapping of module_key -> module_doc using the parse_file helper.
    """

    def __init__(self, path: str, include_private: bool = False, style: str = 'auto'):
        self.path = path
        self.include_private = include_private
        self.style = style

    def parse(self) -> Dict[str, Dict[str, Any]]:
        docs: Dict[str, Dict[str, Any]] = {}
        if os.path.isfile(self.path):
            parsed = parse_file(self.path, include_private=self.include_private, style=self.style)
            if parsed is not None:
                key = os.path.basename(self.path).replace(os.path.sep, '/')
                if 'file' not in parsed:
                    parsed['file'] = key
                docs[key] = parsed
            return docs

        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
            for fn in files:
                if not fn.endswith('.py'):
                    continue
                p = os.path.join(root, fn)
                parsed = parse_file(p, include_private=self.include_private, style=self.style)
                if parsed is None:
                    continue
                rel = os.path.relpath(p, self.path).replace(os.path.sep, '/')
                if 'file' not in parsed:
                    parsed['file'] = rel
                docs[rel] = parsed
        return docs
