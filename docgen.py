# structured representation of modules, classes, functions, methods and simple
# module-level constants. It never imports or executes user code.
#
# Key features implemented:
# - NodeVisitor-based traversal preserving nesting scope to compute FQNs
# - Signature formatting (annotations + defaults) using ast.unparse where available
# - Simple module-level constant extraction for literal values
# - Docstring capture and heuristic docstring style detection (google/numpy/rest)
# - Respect --include-private flag (single leading underscore allowed when enabled)
# - Graceful handling of syntax/parsing errors (warnings, no crash)
#
# The parser is intentionally conservative and avoids evaluating or importing
# user code to prevent side-effects.
"""
"""

import ast
import os
import sys
import json
import traceback
import re
from typing import List, Dict, Any, Optional

try:
    from ast import unparse as ast_unparse
except Exception:
    # Fallback for Python versions <3.9; provide minimal unparse support
    def ast_unparse(node):
        # Very small fallback: for Constants, Names and simple containers
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
        # Last resort: fallback to generic dump
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
    """Construct a simple serializable representation of function signatures

    Does NOT evaluate defaults/annotations; represents them using ast_unparse.
    """

    @staticmethod
    def format_arguments(args: ast.arguments) -> List[Dict[str, Any]]:
        parts = []

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

        # positional-only args (PEP 570)
        posonly = getattr(args, 'posonlyargs', [])
        for i, arg in enumerate(posonly):
            default = None
            # posonly defaults mapping is tricky; for now we attempt to align from the end
            # (best-effort); this is conservative but avoids executing code.
            add_arg(arg, default_node=default, kind='posonly')

        # regular args
        for i, arg in enumerate(args.args):
            default = None
            num_defaults = len(args.defaults)
            if num_defaults:
                offset = len(args.args) - num_defaults
                if i >= offset:
                    default = args.defaults[i - offset]
            add_arg(arg, default_node=default, kind='positional')

        # vararg
        if args.vararg:
            ann = getattr(args.vararg, 'annotation', None)
            ann_s = ast_unparse(ann) if ann is not None else None
            parts.append({'name': args.vararg.arg, 'annotation': ann_s, 'default': None, 'kind': 'vararg'})

        # kw-only args
        for i, arg in enumerate(args.kwonlyargs):
            default = args.kw_defaults[i] if args.kw_defaults else None
            add_arg(arg, default_node=default, kind='kwonly')

        # kwarg
        if args.kwarg:
            ann = getattr(args.kwarg, 'annotation', None)
            ann_s = ast_unparse(ann) if ann is not None else None
            parts.append({'name': args.kwarg.arg, 'annotation': ann_s, 'default': None, 'kind': 'varkw'})

        return parts


class DocVisitor(ast.NodeVisitor):
    def __init__(self, include_private: bool = False, style: str = 'auto'):
        self.include_private = include_private
        self.style = style
        self.stack: List[str] = []  # current scope (class/function names)
        self.module_doc: Dict[str, Any] = {
            'file': '',
            'docstring': None,
            'constants': [],
            'classes': [],
            'functions': []
        }

    def visit_Module(self, node: ast.Module):
        self.module_doc['docstring'] = ast.get_docstring(node)
        # Collect module-level constants and top-level defs
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                # Only simple constant assignments
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
            # ignore other top-level constructs

    def visit_ClassDef(self, node: ast.ClassDef):
        # Build class doc
        class_entry = {
            'name': node.name,
            'bases': [ast_unparse(b) for b in node.bases] if node.bases else [],
            'docstring': ast.get_docstring(node),
            'methods': [],
        }
        self.stack.append(node.name)
        # Visit methods only (don't walk entire tree with NodeVisitor.generic_visit to keep control)
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if should_include(item.name, self.include_private):
                    m = self._extract_function(item, method_of=node.name)
                    class_entry['methods'].append(m)
            # nested classes or other statements could be added here
        self.stack.pop()
        self.module_doc['classes'].append(class_entry)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        fn = self._extract_function(node)
        self.module_doc['functions'].append(fn)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Treat async functions similarly but mark as async
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
        decorators = []
        if hasattr(node, 'decorator_list') and node.decorator_list:
            decorators = [ast_unparse(d) for d in node.decorator_list]
        # detect common decorator semantics
        is_property = any(d in ('property', 'builtins.property') or d.endswith('.property') for d in decorators)
        is_static = any(d == 'staticmethod' or d.endswith('.staticmethod') for d in decorators)
        is_classmethod = any(d == 'classmethod' or d.endswith('.classmethod') for d in decorators)
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
        # Heuristic detection
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
            # plain text -> short summary + long description
            lines = [l.rstrip() for l in doc.splitlines()]
            summary = lines[0] if lines else ''
            parsed.update({'summary': summary, 'description': '\n'.join(lines[1:]).strip()})
        return parsed

    def _parse_numpy_doc(self, doc: str) -> Dict[str, Any]:
        # Parse NumPy style sections (headers underlined with dashes). We look for
        # common sections: Parameters, Returns, Raises, Examples, Attributes.
        lines = doc.expandtabs().splitlines()
        sections: Dict[str, str] = {}
        i = 0
        while i < len(lines):
            line = lines[i]
            if i + 1 < len(lines) and re.match(r'^\s*-{3,}\s*$', lines[i + 1]):
                header = line.strip()
                key = header.lower()
                i += 2
                content_lines = []
                while i < len(lines) and not (i + 1 < len(lines) and re.match(r'^\s*-{3,}\s*$', lines[i + 1])):
                    content_lines.append(lines[i])
                    i += 1
                sections[key] = '\n'.join(content_lines).rstrip()
            else:
                i += 1

        # Now parse structured content for parameters/returns/raises
        parsed: Dict[str, Any] = {'summary': None, 'description': None, 'params': [], 'returns': None, 'raises': [], 'examples': None, 'attributes': []}
        # summary + description
        first_nonempty = next((l for l in lines if l.strip()), '')
        parsed['summary'] = first_nonempty.strip() if first_nonempty else ''
        # parameters
        params_text = sections.get('parameters') or sections.get('parameter')
        if params_text:
            parsed['params'] = self._parse_numpy_parameters_block(params_text)
        # returns
        returns_text = sections.get('returns') or sections.get('return')
        if returns_text:
            parsed['returns'] = self._parse_numpy_returns_block(returns_text)
        # raises
        raises_text = sections.get('raises')
        if raises_text:
            parsed['raises'] = self._parse_numpy_raises_block(raises_text)
        # examples
        parsed['examples'] = sections.get('examples')
        # attributes
        attrs_text = sections.get('attributes')
        if attrs_text:
            parsed['attributes'] = self._parse_numpy_parameters_block(attrs_text)
        return parsed

    def _parse_numpy_parameters_block(self, text: str) -> List[Dict[str, Any]]:
        # Each parameter entry is usually like:
        # name : type, optional
        #     description line1
        #     description line2
        out = []
        lines = text.expandtabs().splitlines()
        i = 0
        current = None
        while i < len(lines):
            line = lines[i]
            m = re.match(r'^\s*([A-Za-z0-9_.,]+)\s*:\s*(.+)$', line)
            if m:
                # start of a new parameter
                if current:
                    out.append(current)
                name = m.group(1).strip()
                typ = m.group(2).strip()
                current = {'name': name, 'type': typ, 'desc': ''}
                i += 1
                # collect indented description lines
                desc_lines = []
                while i < len(lines) and (lines[i].strip() == '' or re.match(r'^\s+', lines[i])):
                    desc_lines.append(lines[i].strip())
                    i += 1
                current['desc'] = '\n'.join([l for l in desc_lines if l])
            else:
                # continuation of previous description
                if current:
                    current['desc'] = (current.get('desc') or '') + ('\n' if current.get('desc') else '') + line.strip()
                i += 1
        if current:
            out.append(current)
        return out

    def _parse_numpy_returns_block(self, text: str) -> Dict[str, Any]:
        # returns block often has form: name : type
        lines = text.expandtabs().splitlines()
        if not lines:
            return {'type': None, 'desc': None}
        # first line may contain type
        m = re.match(r'^\s*([A-Za-z0-9_.,() \[\]]+)\s*:\s*(.*)$', lines[0])
        if m:
            typ = m.group(1).strip()
            desc = '\n'.join([l.strip() for l in lines[1:]]).strip() if len(lines) > 1 else ''
            return {'type': typ, 'desc': desc}
        else:
            return {'type': None, 'desc': '\n'.join([l.strip() for l in lines]).strip()}

    def _parse_numpy_raises_block(self, text: str) -> List[Dict[str, Any]]:
        # entries like: ErrorType
        out = []
        lines = [l.strip() for l in text.expandtabs().splitlines() if l.strip()]
        for line in lines:
            # if line has ':' treat as name: desc
            if ':' in line:
                name, desc = line.split(':', 1)
                out.append({'name': name.strip(), 'desc': desc.strip()})
            else:
                out.append({'name': line, 'desc': ''})
        return out

    def _parse_google_doc(self, doc: str) -> Dict[str, Any]:
        # Parse Google style docstrings: Args:, Returns:, Raises:, Examples:, Attributes:
        sections: Dict[str, str] = {}
        cur = None
        buf: List[str] = []
        for line in doc.splitlines():
            s = line.rstrip()
            header_m = re.match(r'^\s*(Args|Arguments|Returns|Yields|Raises|Examples|Attributes)\s*:\s*$', s)
            if header_m:
                if cur:
                    sections[cur] = '\n'.join(buf).strip()
                cur = header_m.group(1).lower()
                buf = []
                continue
            if cur:
                buf.append(line)
        if cur:
            sections[cur] = '\n'.join(buf).strip()

        parsed: Dict[str, Any] = {'summary': None, 'description': None, 'params': [], 'returns': None, 'raises': [], 'examples': None, 'attributes': []}
        # summary
        lines = [l for l in doc.splitlines()]
        parsed['summary'] = lines[0].strip() if lines else ''
        # params
        params_text = sections.get('args') or sections.get('arguments')
        if params_text:
            parsed['params'] = self._parse_google_parameters_block(params_text)
        # returns
        if 'returns' in sections:
            parsed['returns'] = self._parse_google_returns_block(sections['returns'])
        # raises
        if 'raises' in sections:
            parsed['raises'] = self._parse_google_raises_block(sections['raises'])
        # examples
        parsed['examples'] = sections.get('examples')
        return parsed

    def _parse_google_parameters_block(self, text: str) -> List[Dict[str, Any]]:
        out = []
        # lines with pattern: name (type): description
        lines = text.expandtabs().splitlines()
        i = 0
        current = None
        while i < len(lines):
            line = lines[i]
            m = re.match(r'^\s*([A-Za-z0-9_]+)\s*(\([^\)]*\))?\s*:\s*(.*)$', line)
            if m:
                if current:
                    out.append(current)
                name = m.group(1)
                typ = (m.group(2) or '').strip('()')
                desc = m.group(3).strip()
                current = {'name': name, 'type': typ, 'desc': desc}
                i += 1
                # collect indented description
                desc_lines = []
                while i < len(lines) and (lines[i].strip() == '' or re.match(r'^\s+', lines[i])):
                    desc_lines.append(lines[i].strip())
                    i += 1
                current['desc'] = '\n'.join([l for l in desc_lines if l]) if desc_lines else current['desc']
            else:
                if current:
                    current['desc'] = (current.get('desc') or '') + ('\n' if current.get('desc') else '') + line.strip()
                i += 1
        if current:
            out.append(current)
        return out

    def _parse_google_returns_block(self, text: str) -> Dict[str, Any]:
        lines = text.expandtabs().splitlines()
        if not lines:
            return {'type': None, 'desc': None}
        first = lines[0].strip()
        m = re.match(r'^([A-Za-z0-9_(), \[\]]+)\s*:\s*(.*)$', first)
        if m:
            return {'type': m.group(1).strip(), 'desc': '\n'.join([l.strip() for l in lines[1:]])}
        return {'type': None, 'desc': '\n'.join([l.strip() for l in lines])}

    def _parse_google_raises_block(self, text: str) -> List[Dict[str, Any]]:
        out = []
        for line in text.expandtabs().splitlines():
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                name, desc = line.split(':', 1)
                out.append({'name': name.strip(), 'desc': desc.strip()})
            else:
                out.append({'name': line, 'desc': ''})
        return out

    def _parse_rest_doc(self, doc: str) -> Dict[str, Any]:
        # Minimal reST parser to extract :param:, :returns:, :raises:, :example:
        out = {'summary': None, 'description': None, 'params': [], 'returns': None, 'raises': [], 'examples': None}
        lines = doc.splitlines()
        out['summary'] = lines[0].strip() if lines else ''
        param_re = re.compile(r'^\s*:param\s+([A-Za-z0-9_]+)\s*:\s*(.*)$')
        type_re = re.compile(r'^\s*:type\s+([A-Za-z0-9_]+)\s*:\s*(.*)$')
        ret_re = re.compile(r'^\s*:returns?\s*:\s*(.*)$')
        raise_re = re.compile(r'^\s*:raises?\s+([A-Za-z0-9_.]+)\s*:\s*(.*)$')
        cur_param = None
        for line in lines:
            m = param_re.match(line)
            if m:
                out['params'].append({'name': m.group(1), 'desc': m.group(2)})
                continue
            m = ret_re.match(line)
            if m:
                out['returns'] = {'desc': m.group(1)}
                continue
            m = raise_re.match(line)
            if m:
                out['raises'].append({'name': m.group(1), 'desc': m.group(2)})
                continue
        return out


# Top-level parse function used by DocGenerator
def parse_file(path: str, include_private: bool = False, style: str = 'auto') -> Optional[Dict[str, Any]]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
    except Exception as e:
        print(f"Warning: cannot read {path}: {e}", file=sys.stderr)
        return None
    try:
        node = ast.parse(src, filename=path)
    except SyntaxError as e:
        print(f"Warning: syntax error parsing {path}: {e}", file=sys.stderr)
        return None
    v = DocVisitor(include_private=include_private, style=style)
    v.module_doc['file'] = os.path.relpath(path)
    v.visit(node)
    return v.module_doc


class DocGenerator:
    def __init__(self, path: str, include_private: bool = False, style: str = 'auto'):
        self.path = path
        self.include_private = include_private
        self.style = style

    def _iter_py_files(self):
        if os.path.isfile(self.path):
            yield self.path
            return
        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
            for fn in files:
                if fn.endswith('.py'):
                    yield os.path.join(root, fn)

    def parse(self) -> Dict[str, Any]:
        out = {}
        for p in self._iter_py_files():
            doc = parse_file(p, include_private=self.include_private, style=self.style)
            if doc is None:
                continue
            # normalize key to POSIX-style relative path
            key = os.path.relpath(p, self.path) if not os.path.isfile(self.path) else os.path.basename(p)
            key = key.replace(os.path.sep, '/')
            out[key] = doc
        return out
