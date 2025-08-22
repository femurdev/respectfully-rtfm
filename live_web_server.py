#
# Flask is imported lazily inside start_server so users who only use CLI exports
# won't need Flask installed.
"""
"""

import os
import threading
import time
import hashlib
import json
import re
from typing import Optional
from docgen import DocGenerator
from utils import logger


class DocCache:
    """Thread-safe documentation cache with robust mtime fingerprinting.

    Also maintains a simple inverted index for quick search over module names,
    class/function names and docstrings.
    """

    def __init__(self, path, include_private=False, style='auto'):
        self.path = path
        self.include_private = include_private
        self.style = style
        self.lock = threading.Lock()
        self.docs = None
        self.last_updated = 0.0
        self._mtimes = {}
        # simple token splitter regex
        self._re_split = re.compile(r'[^0-9a-zA-Z_]+')
        self.index = {}  # token -> set(module_keys)
        self.meta = {}   # module_key -> metadata dict (file, snippet, type)

    def compute_mtime_fingerprint(self):
        # Build a stable hash of all (relative path, mtime) entries to detect changes.
        hasher = hashlib.sha1()
        entries = []

        if os.path.isfile(self.path):
            # single file mode
            try:
                rel = os.path.basename(self.path)
                rel = rel.replace(os.path.sep, '/')
                m = os.path.getmtime(self.path)
                entries.append((rel, m))
            except OSError:
                pass
        else:
            for root, dirs, files in os.walk(self.path):
                # skip virtualenv / cache dirs heuristically
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
                for fn in files:
                    if not fn.endswith('.py'):
                        continue
                    try:
                        p = os.path.join(root, fn)
                        rel = os.path.relpath(p, self.path)
                        # normalize to POSIX-style so keys are consistent across platforms
                        rel = rel.replace(os.path.sep, '/')
                        m = os.path.getmtime(p)
                        entries.append((rel, m))
                    except OSError:
                        continue
        for rel, m in sorted(entries):
            hasher.update(rel.encode('utf-8'))
            hasher.update(b'\0')
            hasher.update(str(m).encode('utf-8'))
            hasher.update(b'\0')
        return hasher.hexdigest()

    def _tokenize_for_index(self, text: Optional[str]):
        if not text:
            return []
        toks = [t.lower() for t in self._re_split.split(text) if t]
        return toks

    def _build_index(self, docs: dict):
        # Rebuild a simple inverted index for fast prefix searches.
        # This function now returns (idx, meta) so caller can atomically swap.
        idx = {}
        meta = {}
        for key, doc in docs.items():
            # collect token sources
            sources = []
            sources.append(key)
            if isinstance(doc, dict):
                ds = doc.get('docstring') or ''
                sources.append(ds)
                for cls in doc.get('classes', []) or []:
                    sources.append(cls.get('name') or '')
                    sources.append(cls.get('docstring') or '')
                    for m in cls.get('methods', []) or []:
                        sources.append(m.get('name') or '')
                        sources.append(m.get('docstring') or '')
                for fn in doc.get('functions', []) or []:
                    sources.append(fn.get('name') or '')
                    sources.append(fn.get('docstring') or '')
            # tokenize and add
            seen = set()
            for src in sources:
                for tok in self._tokenize_for_index(src):
                    if not tok:
                        continue
                    if tok in seen:
                        continue
                    seen.add(tok)
                    # add full token
                    idx.setdefault(tok, set()).add(key)
                    # also add short prefixes of the token for efficient prefix search
                    # limit prefix lengths to avoid exploding the index size
                    max_pref = min(len(tok), 6)
                    for i in range(2, max_pref + 1):
                        pref = tok[:i]
                        idx.setdefault(pref, set()).add(key)
            # build metadata for fast response: file, snippet, type
            file_field = None
            snippet = ''
            try:
                if isinstance(doc, dict):
                    file_field = doc.get('file') or key
                    ds = (doc.get('docstring') or '').strip()
                    if ds:
                        lines = [l.strip() for l in ds.splitlines() if l.strip()]
                        if lines:
                            snippet = lines[0][:200]
            except Exception:
                file_field = key
                snippet = ''
            meta[key] = {'key': key, 'file': file_field, 'snippet': snippet, 'type': 'module'}
        return idx, meta

    def scan_and_update(self):
        """Scan for changes and update docs if needed."""
        try:
            fingerprint = self.compute_mtime_fingerprint()
            # Quick check: if fingerprint same and docs present, skip
            if fingerprint == self._mtimes.get('fingerprint') and self.docs is not None:
                return False

            generator = DocGenerator(path=self.path, include_private=self.include_private, style=self.style)
            new_docs = generator.parse()

            # Build index and meta outside lock then swap atomically
            try:
                new_idx, new_meta = self._build_index(new_docs)
            except Exception:
                new_idx, new_meta = {}, {}

            with self.lock:
                self.docs = new_docs
                self.last_updated = time.time()
                self._mtimes['fingerprint'] = fingerprint
                # atomic swap
                self.index = new_idx
                self.meta = new_meta
            return True
        except Exception as e:
            # Don't crash the server on parser errors; log and continue
            try:
                logger.error("Error updating docs: %s", e)
            except Exception:
                print("Error updating docs:", e)
            return False

    def snapshot(self):
        """Return a shallow snapshot of current docs/meta/index sizes for safe reads.

        This can be used by request handlers to avoid holding locks for long.
        """
        with self.lock:
            docs_copy = dict(self.docs) if self.docs else {}
            meta_copy = dict(self.meta) if self.meta else {}
            idx_len = len(self.index) if self.index else 0
            return {'docs': docs_copy, 'meta': meta_copy, 'index_keys': idx_len, 'last_updated': self.last_updated}

    def search(self, query: str, limit: int = 200):
        """Return ordered list of result objects matching the query using the inverted index.

        Each result is a dict: {key, file, snippet, type}.
        The query is split into tokens; tokens are matched against index keys
        by exact or prefix (we pre-populated short prefixes), and the result is
        modules that match all query tokens (AND semantics).
        """
        q = (query or '').strip().lower()
        if not q:
            with self.lock:
                # return metadata objects for modules
                keys = sorted(self.docs.keys()) if self.docs else []
                return [self.meta.get(k, {'key': k, 'file': k, 'snippet': '', 'type': 'module'}) for k in keys[:limit]]
        tokens = [t for t in self._tokenize_for_index(q) if t]
        if not tokens:
            return []
        with self.lock:
            # For each token, collect candidate module sets using direct lookup (exact or prefix)
            results_sets = []
            for tok in tokens:
                matched = set()
                # direct lookup (exact token or prefix) - since index includes short prefixes
                if tok in self.index:
                    matched.update(self.index.get(tok, set()))
                # fallback: if tok longer than our prefix limit, also try shorter prefix entry
                if not matched and len(tok) > 6:
                    pref = tok[:6]
                    matched.update(self.index.get(pref, set()))
                if not matched:
                    # no matches for this token => empty overall
                    return []
                results_sets.append(matched)
            # intersect sets
            out = set.intersection(*results_sets) if results_sets else set()
            out_list = sorted(out)
            # map to metadata objects
            results = [self.meta.get(k, {'key': k, 'file': k, 'snippet': '', 'type': 'module'}) for k in out_list]
            return results[:limit]


# Flask app will be created inside start_server lazily

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Documentation</title>
    <style>
        :root { --bg: #f4f4f9; --text: #333; --accent: #007BFF; --card: #fff; }
        [data-theme="dark"] { --bg: #0f1115; --text: #ddd; --accent: #4ea1ff; --card: #111216; }
        body { font-family: Arial, sans-serif; line-height: 1.6; background-color: var(--bg); color: var(--text); }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        .module-list { display: flex; flex-wrap: wrap; gap: 8px; }
        .module { background: var(--card); padding: 10px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); cursor: pointer; min-width: 200px }
        .search { margin-bottom: 12px; padding:6px; width: 60%; }
        pre { white-space: pre-wrap; word-break: break-word; background: var(--card); padding: 10px; border: 1px solid #ddd; }
        .controls { display:flex; gap:8px; margin-bottom:12px; align-items:center }
        button { cursor:pointer; }
        .snippet { color: #666; font-size: 0.9em; margin-top:6px }
    </style>
</head>
<body data-theme="{{ theme }}">
    <div class="container">
        <h1>Python Documentation</h1>
        <div class="controls">
            <input id="search" class="search" placeholder="Search modules, classes, functions..." />
            <select id="theme-select"><option value="light">Light</option><option value="dark">Dark</option></select>
        </div>
        <div id="modules" class="module-list"></div>
        <hr />
        <div id="module-detail"></div>
        <script type="application/json" id="modules-json">{{ modules_json|safe }}</script>
        <script type="text/plain" id="last-ts">{{ last_ts }}</script>
        <script>
            document.addEventListener('DOMContentLoaded', function(){
                // modules is an array of module metadata objects {key,file,snippet,type}
                let modules = JSON.parse(document.getElementById('modules-json').textContent || '[]');
                const modulesListElem = document.getElementById('modules');
                const moduleDetail = document.getElementById('module-detail');
                const search = document.getElementById('search');
                const themeSelect = document.getElementById('theme-select');

                themeSelect.value = '{{ theme }}';
                themeSelect.addEventListener('change', () => {
                    document.body.setAttribute('data-theme', themeSelect.value === 'dark' ? 'dark' : 'light');
                });

                function renderList(items) {
                    modulesListElem.innerHTML = '';
                    (items || []).forEach(item => {
                        const el = document.createElement('div');
                        el.className = 'module';
                        const title = document.createElement('div');
                        title.textContent = item.key;
                        el.appendChild(title);
                        if (item.snippet) {
                            const s = document.createElement('div'); s.className = 'snippet'; s.textContent = item.snippet; el.appendChild(s);
                        }
                        el.onclick = () => loadModule(item.key);
                        modulesListElem.appendChild(el);
                    });
                }

                function renderModule(doc) {
                    moduleDetail.innerHTML = '';
                    const h = document.createElement('h2');
                    h.textContent = doc.file || 'untitled';
                    moduleDetail.appendChild(h);
                    if (doc.docstring) {
                        const p = document.createElement('pre'); p.textContent = doc.docstring; moduleDetail.appendChild(p);
                    }
                    if (doc.constants && doc.constants.length) {
                        const c = document.createElement('div'); c.innerHTML = '<h3>Constants</h3>'; moduleDetail.appendChild(c);
                        const ul = document.createElement('ul');
                        doc.constants.forEach(x => { const li = document.createElement('li'); li.textContent = `${x.name} = ${x.value}`; ul.appendChild(li); });
                        moduleDetail.appendChild(ul);
                    }
                    if (doc.classes && doc.classes.length) {
                        const cl = document.createElement('div'); cl.innerHTML = '<h3>Classes</h3>'; moduleDetail.appendChild(cl);
                        doc.classes.forEach(cls => {
                            const s = document.createElement('div'); s.innerHTML = `<h4>${cls.name}</h4>`;
                            if (cls.docstring) { const pre = document.createElement('pre'); pre.textContent = cls.docstring; s.appendChild(pre); }
                            if (cls.methods && cls.methods.length) {
                                const ml = document.createElement('ul');
                                cls.methods.forEach(m => { const li = document.createElement('li'); li.textContent = m.fqn + formatSig(m.signature); ml.appendChild(li); });
                                s.appendChild(ml);
                            }
                            moduleDetail.appendChild(s);
                        });
                    }
                    if (doc.functions && doc.functions.length) {
                        const fl = document.createElement('div'); fl.innerHTML = '<h3>Functions</h3>'; moduleDetail.appendChild(fl);
                        const ul = document.createElement('ul');
                        doc.functions.forEach(fn => { const li = document.createElement('li'); li.textContent = fn.fqn + formatSig(fn.signature); ul.appendChild(li); });
                        moduleDetail.appendChild(ul);
                    }
                }

                function formatSig(sig) {
                    if (!sig) return '()';
                    return '(' + sig.map(p => (p.kind==='vararg' ? '*' : p.kind==='varkw' ? '**' : '') + p.name + (p.annotation ? ': '+p.annotation : '') + (p.default ? '='+p.default : '')).join(', ') + ')';
                }

                async function loadModule(name) {
                    try {
                        const resp = await fetch(`/module/${encodeURIComponent(name)}`);
                        if (!resp.ok) { moduleDetail.innerHTML = '<p>Error loading module</p>'; return; }
                        const payload = await resp.json();
                        renderModule(payload.doc);
                    } catch (e) { moduleDetail.innerHTML = '<p>Error loading module</p>'; }
                }

                // Debounced search using server-side /search endpoint for scalability
                let debounceTimer = null;
                async function doSearch(q) {
                    try {
                        const r = await fetch('/search?q=' + encodeURIComponent(q || ''));
                        if (!r.ok) return;
                        const j = await r.json();
                        // j.results is an array of metadata objects
                        renderList(j.results);
                    } catch (e) { console.debug('search failed', e); }
                }
                search.addEventListener('input', (e) => {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(() => doSearch(search.value), 250);
                });

                // initial render
                renderList(modules);

                // Poll for updates and refresh module list minimally
                let lastTs = Number(document.getElementById('last-ts').textContent) || 0;
                async function poll() {
                    try {
                        const r = await fetch(`/summary?ts=${lastTs}`);
                        const j = await r.json();
                        if (j.updated) {
                            const m = await fetch('/modules');
                            const mm = await m.json();
                            modules = mm.modules || [];
                            lastTs = mm.timestamp || Date.now()/1000;
                            renderList(modules);
                        }
                    } catch (e) { console.debug('poll failed', e); }
                }
                setInterval(poll, 5000);
            });
        </script>
    </div>
</body>
</html>
"""


def _create_app(cache: DocCache):
    # Lazy import here
    from flask import Flask, render_template_string, request, jsonify
    app = Flask(__name__)

    @app.route('/')
    def home():
        with cache.lock:
            if cache.docs is None:
                return "<h1>No documentation generated yet. Please check your input path.</h1>"
            # Embed only the module metadata list initially to keep payload small; module details are fetched lazily
            modules_meta = [cache.meta.get(k, {'key': k, 'file': k, 'snippet': ''}) for k in sorted(cache.docs.keys())]
            # Ensure JSON is safely embedded as a string literal in the template
            modules_json = json.dumps(modules_meta)
            last_ts = cache.last_updated
        return render_template_string(HTML_TEMPLATE, modules_json=modules_json, last_ts=last_ts, theme='light')

    @app.route('/summary')
    def summary():
        ts = float(request.args.get('ts') or 0)
        with cache.lock:
            updated = cache.last_updated > ts
        return jsonify({'updated': bool(updated)})

    @app.route('/dump')
    def dump_docs():
        with cache.lock:
            return jsonify({'docs': cache.docs or {}, 'timestamp': cache.last_updated})

    @app.route('/modules')
    def modules_list():
        with cache.lock:
            keys = list(cache.docs.keys()) if cache.docs else []
            ts = cache.last_updated
            modules_meta = [cache.meta.get(k, {'key': k, 'file': k, 'snippet': ''}) for k in keys]
        return jsonify({'modules': modules_meta, 'count': len(keys), 'timestamp': ts})

    @app.route('/module/<path:name>')
    def module_view(name):
        # name is a filesystem relative path; decode and lookup
        with cache.lock:
            doc = cache.docs.get(name)
        if not doc:
            return jsonify({'error': 'not found'}), 404
        return jsonify({'doc': doc})

    @app.route('/search')
    def search_endpoint():
        q = (request.args.get('q') or '').strip()
        # Use index-backed search for faster performance on large repos
        try:
            results = cache.search(q)
        except Exception:
            # fallback to naive search if index failed
            ql = q.lower()
            results_keys = []
            if not ql:
                with cache.lock:
                    results_keys = sorted(cache.docs.keys())
            else:
                with cache.lock:
                    for key, doc in (cache.docs or {}).items():
                        matched = False
                        if ql in key.lower() or (doc.get('docstring') and ql in (doc.get('docstring') or '').lower()):
                            matched = True
                        else:
                            for cls in doc.get('classes', []):
                                if ql in (cls.get('name') or '').lower() or (cls.get('docstring') and ql in (cls.get('docstring') or '').lower()):
                                    matched = True
                                    break
                        if not matched:
                            for fn in doc.get('functions', []):
                                if ql in (fn.get('name') or '').lower() or (fn.get('docstring') and ql in (fn.get('docstring') or '').lower()):
                                    matched = True
                                    break
                        if matched:
                            results_keys.append(key)
            # map to metadata objects
            with cache.lock:
                results = [cache.meta.get(k, {'key': k, 'file': k, 'snippet': ''}) for k in results_keys]
        # dedupe and limit (results are metadata dicts)
        seen = set()
        out = []
        for r in results:
            k = r.get('key')
            if k not in seen:
                seen.add(k)
                out.append(r)
                if len(out) >= 200:
                    break
        return jsonify({'results': out})

    return app


def start_server(path, host='127.0.0.1', port=5000, include_private=False, style='auto'):
    cache = DocCache(path, include_private=include_private, style=style)

    # initial scan
    cache.scan_and_update()

    def background_scanner():
        while True:
            try:
                changed = cache.scan_and_update()
                if changed:
                    logger.debug('Documentation updated')
            except Exception:
                logger.debug('Background scanner exception')
            time.sleep(2.0)

    t = threading.Thread(target=background_scanner, daemon=True)
    t.start()

    app = _create_app(cache)
    # Flask is started by the CLI entrypoint; don't enable debug here
    app.run(host=host, port=port, debug=False)
