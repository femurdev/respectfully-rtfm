#!/usr/bin/env python3
"""
doc_server.py

Run: python3 doc_server.py [path] [--port PORT]

Scans the given directory (default: current directory) for .py files,
extracts module/function/class docstrings and signatures, builds a simple
search index, and serves HTML documentation with a sidebar and search bar.

No external dependencies required.
"""

from __future__ import annotations
import ast
import html
import http.server
import json
import os
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.abspath(os.getcwd())
DEFAULT_PORT = 8000

# Utilities

def relpath_for_url(root: str, path: str) -> str:
    rel = os.path.relpath(path, root)
    return rel.replace(os.path.sep, '/')


def safe_join(root: str, rel_url_path: str) -> Optional[str]:
    rel = rel_url_path.lstrip('/')
    rel_os = rel.replace('/', os.path.sep)
    candidate = os.path.normpath(os.path.join(root, rel_os))
    try:
        common = os.path.commonpath([root, candidate])
    except Exception:
        return None
    if common != root:
        return None
    return candidate


def get_signature_from_args(node: ast.FunctionDef) -> str:
    params = []
    # positional args and defaults
    args = node.args
    defaults = [None] * (len(args.args) - len(args.defaults)) + list(args.defaults)
    for arg, default in zip(args.args, defaults):
        name = arg.arg
        if default is not None:
            try:
                default_val = ast.unparse(default)
            except Exception:
                default_val = '<default>'
            params.append(f"{name}={default_val}")
        else:
            params.append(name)
    # vararg
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    # kwonlyargs
    for k, d in zip(args.kwonlyargs, args.kw_defaults):
        if d is not None:
            try:
                dv = ast.unparse(d)
            except Exception:
                dv = '<default>'
            params.append(f"{k.arg}={dv}")
        else:
            params.append(k.arg)
    # kwargs
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")
    return f"({', '.join(params)})"


def parse_file(path: str) -> Dict[str, Any]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        return {'_error': str(e)}
    try:
        tree = ast.parse(source)
    except Exception as e:
        return {'_error': f"AST parse error: {e}", 'source': source}
    module_doc = ast.get_docstring(tree) or ''
    entries: List[Dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            entries.append({'type': 'function', 'name': node.name, 'signature': get_signature_from_args(node), 'doc': ast.get_docstring(node) or ''})
        elif isinstance(node, ast.AsyncFunctionDef):
            entries.append({'type': 'async function', 'name': node.name, 'signature': get_signature_from_args(node), 'doc': ast.get_docstring(node) or ''})
        elif isinstance(node, ast.ClassDef):
            methods: List[Dict[str, Any]] = []
            class_doc = ast.get_docstring(node) or ''
            for cnode in node.body:
                if isinstance(cnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({'name': cnode.name, 'signature': get_signature_from_args(cnode), 'doc': ast.get_docstring(cnode) or ''})
            entries.append({'type': 'class', 'name': node.name, 'doc': class_doc, 'methods': methods})
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            names: List[str] = []
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        names.append(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.append(node.target.id)
            for n in names:
                entries.append({'type': 'variable', 'name': n, 'doc': ''})
    return {'module_doc': module_doc, 'entries': entries, 'source': source}


def build_docs(root: str) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    docs_map: Dict[str, Any] = {}
    search_index: List[Dict[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        for fn in filenames:
            if not fn.endswith('.py'):
                continue
            full = os.path.join(dirpath, fn)
            rel = relpath_for_url(root, full)
            parsed = parse_file(full)
            docs_map[rel] = parsed
            title = rel
            snippet = (parsed.get('module_doc') or '').strip().splitlines()[0][:200] if parsed.get('module_doc') else ''
            search_index.append({'title': title, 'path': rel, 'snippet': snippet})
            for e in parsed.get('entries', []):
                if e['type'] in ('function', 'async function'):
                    s = (e.get('doc') or '').strip().splitlines()[0][:200]
                    search_index.append({'title': e['name'], 'path': rel, 'snippet': s})
                elif e['type'] == 'class':
                    s = (e.get('doc') or '').strip().splitlines()[0][:200]
                    search_index.append({'title': e['name'], 'path': rel, 'snippet': s})
                    for m in e.get('methods', []):
                        ms = (m.get('doc') or '').strip().splitlines()[0][:200]
                        search_index.append({'title': f"{e['name']}.{m['name']}", 'path': rel, 'snippet': ms})
    return docs_map, search_index

# Templates

BASE_CSS = '''
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial; margin:0; }
.header { background:#222; color:#fff; padding:12px 16px; display:flex; align-items:center; gap:12px;}
.header h1 { margin:0; font-size:18px; }
.container { display:flex; height: calc(100vh - 56px); }
.sidebar { width:320px; border-right:1px solid #ddd; overflow:auto; padding:12px; background:#f7f7f7;}
.content { flex:1; padding:16px; overflow:auto; }
.file-link { display:block; padding:6px 8px; border-radius:4px; color:#111; text-decoration:none; }
.file-link:hover { background:#e8e8e8; }
.search { flex:1; display:flex; gap:8px; }
.search input[type="search"] { width:100%; padding:8px; border-radius:6px; border:1px solid #ccc; }
.result { padding:8px; border-bottom:1px solid #eee; }
.signature { font-family: monospace; background:#f2f2f2; padding:2px 6px; border-radius:4px; }
.code { background:#111; color:#f8f8f2; padding:12px; border-radius:6px; overflow:auto; font-family:monospace; font-size:13px; white-space:pre; }
.small { color:#666; font-size:13px; }
.topbar-button { background:#fff; color:#222; border:1px solid #ccc; padding:6px 8px; border-radius:6px; cursor:pointer; text-decoration:none; }
.empty { color:#666; padding:20px; text-align:center; }
'''

BASE_JS = r'''
async function searchQuery(q) {
    if (!q) { document.getElementById('search-results').innerHTML = ''; return; }
    const resp = await fetch('/search?q=' + encodeURIComponent(q));
    const data = await resp.json();
    const container = document.getElementById('search-results');
    if (data.results.length === 0) { container.innerHTML = '<div class="empty">No results</div>'; return; }
    container.innerHTML = data.results.map(r =>
        `<div class="result"><a href="/doc/${encodeURIComponent(r.path)}" class="file-link"><strong>${escapeHtml(r.title)}</strong></a><div class="small">${escapeHtml(r.snippet)}</div></div>`
    ).join('');
}
function escapeHtml(s){ return s.replace(/[&<>"']/g, function(m){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[m]; }); }
let searchTimeout = null;
function onSearchInput(evt){ clearTimeout(searchTimeout); const q = evt.target.value.trim(); searchTimeout = setTimeout(()=>searchQuery(q), 200); }
document.addEventListener('DOMContentLoaded', function(){ const inp = document.getElementById('search-input'); if (inp){ inp.addEventListener('input', onSearchInput); } });
'''

PAGE_TEMPLATE = '''
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{css}</style>
</head>
<body>
<div class="header">
  <div class="logo">PyDocServer</div>
  <h1>{title}</h1>
  <div style="flex:1"></div>
  <div style="width:420px">
    <div class="search">
      <input id="search-input" type="search" placeholder="Search modules, classes, functions..." autocomplete="off"/>
    </div>
  </div>
</div>
<div class="container">
  <div class="sidebar">
    <div style="margin-bottom:8px"><a href="/" class="topbar-button">Home</a> <a href="/source/" class="topbar-button">Source index</a></div>
    {sidebar}
  </div>
  <div class="content">
    {content}
    <div id="search-results" style="margin-top:20px"></div>
  </div>
</div>
<script>{js}</script>
</body>
</html>
'''

class DocHandler(http.server.BaseHTTPRequestHandler):
    docs_map: Dict[str, Any] = {}
    search_index: List[Dict[str, str]] = []
    root_path: str = ROOT

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), fmt%args))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == '/' or path == '/index.html':
            self.serve_index(); return
        if path.startswith('/doc/'):
            rel = urllib.parse.unquote(path[len('/doc/'):]); self.serve_doc(rel); return
        if path.startswith('/source/'):
            rel = urllib.parse.unquote(path[len('/source/'):])
            if rel == '': self.serve_source_index()
            else: self.serve_source(rel)
            return
        if path == '/search':
            self.serve_search(parsed.query); return
        if path == '/favicon.ico':
            self.send_response(204); self.end_headers(); return
        self.send_response(404); self.end_headers(); self.wfile.write(b'Not Found')

    def serve_index(self):
        sidebar = self.build_sidebar()
        readme = None
        for candidate in ('README.md','README.rst','README.txt','README'):
            p = os.path.join(self.root_path, candidate)
            if os.path.isfile(p):
                try:
                    with open(p,'r',encoding='utf-8') as f: readme = f.read(); break
                except Exception:
                    pass
        if readme:
            content = '<h2>README</h2><pre class="code">%s</pre>' % html.escape(readme)
        else:
            content = '<h2>Project documentation</h2><p class="small">Browse the sidebar to open generated documentation for Python modules.</p>'
        page = PAGE_TEMPLATE.format(title=f"Docs for {os.path.basename(self.root_path) or self.root_path}", css=BASE_CSS, sidebar=sidebar, content=content, js=BASE_JS)
        self.send_html(page)

    def build_sidebar(self) -> str:
        items = sorted(self.docs_map.keys())
        if not items:
            return '<div class="empty">No Python files found</div>'
        lines = []
        prev_dir = None
        for item in items:
            dirpart = os.path.dirname(item)
            if dirpart != prev_dir:
                if prev_dir is not None:
                    lines.append('<hr/>')
                if dirpart:
                    lines.append(f'<div style="font-weight:600; margin:8px 0;">{html.escape(dirpart)}</div>')
                prev_dir = dirpart
            lines.append(f'<a class="file-link" href="/doc/{urllib.parse.quote(item)}">{html.escape(os.path.basename(item))}</a>')
        return '\n'.join(lines)

    def serve_doc(self, rel_path: str):
        target = safe_join(self.root_path, rel_path)
        if target is None or not os.path.isfile(target):
            self.send_response(404); self.end_headers(); self.wfile.write(b'Not Found'); return
        rel_posix = relpath_for_url(self.root_path, target)
        parsed = self.docs_map.get(rel_posix) or parse_file(target)
        content = self.render_doc_page(rel_posix, parsed)
        page = PAGE_TEMPLATE.format(title=f"{rel_posix}", css=BASE_CSS, sidebar=self.build_sidebar(), content=content, js=BASE_JS)
        self.send_html(page)

    def render_doc_page(self, rel: str, parsed: Dict[str, Any]) -> str:
        parts: List[str] = []
        parts.append(f'<h2>{html.escape(rel)}</h2>')
        parts.append(f'<div style="margin-bottom:8px"><a href="/source/{urllib.parse.quote(rel)}" class="topbar-button">View source</a></div>')
        if parsed.get('_error'):
            parts.append(f'<div class="empty">Error parsing file: {html.escape(parsed["_error"])}</div>')
            return '\n'.join(parts)
        if parsed.get('module_doc'):
            parts.append(f'<div class="small">{html.escape(parsed.get("module_doc"))}</div>')
        entries = parsed.get('entries', [])
        if not entries:
            parts.append('<div class="empty">No top-level functions, classes, or variables found.</div>')
        for e in entries:
            if e['type'] in ('function','async function'):
                parts.append(f'<h3>{html.escape(e["name"])} <span class="signature">{html.escape(e["signature"])}</span></h3>')
                if e.get('doc'):
                    parts.append(f'<div class="small">{html.escape(e.get("doc"))}</div>')
            elif e['type'] == 'class':
                parts.append(f'<h3>class {html.escape(e["name"])}</h3>')
                if e.get('doc'):
                    parts.append(f'<div class="small">{html.escape(e.get("doc"))}</div>')
                methods = e.get('methods', [])
                if methods:
                    parts.append('<h4>Methods</h4><ul>')
                    for m in methods:
                        parts.append(f'<li><strong>{html.escape(m["name"])}</strong> <span class="signature">{html.escape(m["signature"])}</span><div class="small">{html.escape(m.get("doc") or "")}</div></li>')
                    parts.append('</ul>')
            elif e['type'] == 'variable':
                parts.append(f'<div><strong>{html.escape(e["name"])}</strong> <span class="small">variable</span></div>')
        parts.append('<h4>Source (excerpt)</h4>')
        snippet = parsed.get('source','')[:4000]
        parts.append('<pre class="code">%s</pre>' % html.escape(snippet))
        return '\n'.join(parts)

    def serve_source_index(self):
        lines = ['<h2>Source files</h2>']
        for path in sorted(self.docs_map.keys()):
            lines.append(f'<div><a class="file-link" href="/source/{urllib.parse.quote(path)}">{html.escape(path)}</a></div>')
        page = PAGE_TEMPLATE.format(title="Source index", css=BASE_CSS, sidebar=self.build_sidebar(), content=''.join(lines), js=BASE_JS)
        self.send_html(page)

    def serve_source(self, rel_path: str):
        target = safe_join(self.root_path, rel_path)
        if target is None or not os.path.isfile(target):
            self.send_response(404); self.end_headers(); self.wfile.write(b'Not Found'); return
        try:
            with open(target,'r',encoding='utf-8') as f: src = f.read()
        except Exception:
            self.send_response(500); self.end_headers(); self.wfile.write(b'Error reading file'); return
        content = f'<h2>Source: {html.escape(rel_path)}</h2><pre class="code">{html.escape(src)}</pre>'
        page = PAGE_TEMPLATE.format(title=f"Source: {rel_path}", css=BASE_CSS, sidebar=self.build_sidebar(), content=content, js=BASE_JS)
        self.send_html(page)

    def serve_search(self, query: str):
        qs = urllib.parse.parse_qs(query)
        q = qs.get('q', [''])[0].strip().lower()
        results: List[Dict[str,str]] = []
        if q:
            for item in self.search_index:
                title = item['title']
                path = item['path']
                snippet = item.get('snippet','')
                hay = (title + ' ' + snippet).lower()
                if q in hay or q in path.lower():
                    results.append({'title': title, 'path': path, 'snippet': snippet})
            results = results[:200]
        payload = {'q': q, 'count': len(results), 'results': results}
        b = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_html(self, html_text: str):
        b = html_text.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def run_server(root: str, port: int):
    print(f"Scanning Python files in: {root} ...")
    docs_map, search_index = build_docs(root)
    print(f"Found {len(docs_map)} Python files; search index items: {len(search_index)}")
    DocHandler.docs_map = docs_map
    DocHandler.search_index = search_index
    DocHandler.root_path = root
    server_address = ('', port)
    httpd = http.server.ThreadingHTTPServer(server_address, DocHandler)
    sa = httpd.socket.getsockname()
    print(f"Serving HTTP on {sa[0]} port {sa[1]} (http://localhost:{sa[1]}/) ...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        httpd.server_close()


def parse_args(argv):
    import argparse
    p = argparse.ArgumentParser(description="Simple Python documentation web server")
    p.add_argument('path', nargs='?', default='.', help='Path to project root (default: current directory)')
    p.add_argument('--port', '-p', type=int, default=DEFAULT_PORT, help='Port to serve on (default 8000)')
    return p.parse_args(argv[1:])


if __name__ == '__main__':
    args = parse_args(sys.argv)
    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print('Path is not a directory:', root, file=sys.stderr); sys.exit(1)
    run_server(root, args.port)
