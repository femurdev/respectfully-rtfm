"""rtfm main CLI

Enhanced single-file interactive HTML viewer generation.
Features added:
 - Client-side config for rendering markdown, sanitization, and fuzzy search
 - CLI flags: --render-markdown, --sanitize, --fuzzy-search
 - Pages include both HTML and (when available) markdown source for client-side rendering
 - Simple client-side fuzzy search implementation (no external deps)

Security: the generated page may insert page.html using innerHTML to support native
HTML content. Only serve or open output you trust. Use --sanitize to attempt DOMPurify
client-side sanitization (will try to load DOMPurify from a CDN at runtime).
"""
from __future__ import annotations

import argparse
import http.server
import socketserver
import threading
import time
import os
import sys
import html as htmlmod
import json
from typing import Dict, Any, Optional

try:
    from rtfmlib.docgen import parse_file
    from rtfmlib import exporters
    from rtfmlib.utils import logger
except Exception:
    parse_file = None  # type: ignore
    exporters = None  # type: ignore
    logger = None  # type: ignore


def compute_mtime_fingerprint(path: str) -> str:
    import hashlib

    hasher = hashlib.sha1()
    entries = []
    if os.path.isfile(path):
        try:
            rel = os.path.basename(path).replace(os.path.sep, '/')
            m = os.path.getmtime(path)
            entries.append((rel, m))
        except OSError:
            pass
    else:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
            for fn in files:
                if not fn.endswith('.py'):
                    continue
                try:
                    p = os.path.join(root, fn)
                    rel = os.path.relpath(p, path).replace(os.path.sep, '/')
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


def collect_docs(path: str, include_private: bool = False, style: str = 'auto') -> Dict[str, Any]:
    if parse_file is None:
        raise RuntimeError('rtfmlib.docgen.parse_file is not available')

    docs: Dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            parsed = parse_file(path, include_private=include_private, style=style)
            key = os.path.basename(path).replace(os.path.sep, '/')
            if parsed is not None:
                if isinstance(parsed, dict) and 'file' not in parsed:
                    parsed['file'] = key
                docs[key] = parsed
        except Exception as e:
            if logger:
                logger.error('Failed to parse %s: %s', path, e)
            else:
                print('Failed to parse', path, e, file=sys.stderr)
        return docs

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
        for fn in files:
            if not fn.endswith('.py'):
                continue
            p = os.path.join(root, fn)
            try:
                parsed = parse_file(p, include_private=include_private, style=style)
                rel = os.path.relpath(p, path).replace(os.path.sep, '/')
                if parsed is not None:
                    if isinstance(parsed, dict) and 'file' not in parsed:
                        parsed['file'] = rel
                    docs[rel] = parsed
            except Exception as e:
                if logger:
                    logger.warning('Skipping %s: %s', p, e)
                else:
                    print('Skipping', p, e, file=sys.stderr)
    return docs


def _page_from_doc(key: str, d: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a parsed doc entry into a page dict for embedding in the HTML viewer.

    The produced page dict has fields: id, title, tags, html, md (optional).
    """
    file_name = d.get('file') or key
    page_id = file_name.replace('/', '_')
    title = file_name
    tags = d.get('tags') if isinstance(d.get('tags'), list) else []

    content_parts = []
    md_source = None

    # prefer exporters.module_to_markdown when available
    if exporters is not None:
        try:
            md = exporters.module_to_markdown(key, d)
            md_source = md
            # keep escaped markdown as fallback view
            content_parts.append('<div class="rtfm-markdown"><pre style="white-space:pre-wrap;">{}</pre></div>'.format(htmlmod.escape(md)))
        except Exception:
            pass

    # fallback: docstring
    docstring = d.get('docstring') or ''
    if docstring:
        content_parts.append('<h2>Docstring</h2><pre style="white-space:pre-wrap;">{}</pre>'.format(htmlmod.escape(docstring)))

    # include a JSON dump for advanced inspection
    try:
        json_dump = json.dumps(d, indent=2, ensure_ascii=False)
        content_parts.append('<h3>Raw data</h3><pre style="white-space:pre-wrap;">{}</pre>'.format(htmlmod.escape(json_dump)))
    except Exception:
        pass

    html = '\n'.join(content_parts) if content_parts else '<p>No documentation available.</p>'
    page = {'id': page_id, 'title': title, 'tags': tags, 'html': html}
    if md_source:
        page['md'] = md_source
    return page


def generate_html_from_docs(docs: Dict[str, Any], render_markdown: bool = False, sanitize: bool = False, fuzzy_search: bool = False) -> str:
    """Produce a single-file interactive HTML page embedding the docs.

    Options control client-side behavior and are embedded into the page config.
    """
    pages = []
    for k, d in docs.items():
        pages.append(_page_from_doc(k, d))

    pages_js = json.dumps(pages, ensure_ascii=False)
    config_js = json.dumps({'renderMarkdown': bool(render_markdown), 'sanitize': bool(sanitize), 'fuzzySearch': bool(fuzzy_search)})

    tpl = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>RTFM — Documentation Viewer</title>
<style>
  :root{{
    --bg: #f6f7fb;
    --panel: #ffffff;
    --muted: #6b7280;
    --accent: #2563eb;
    --accent-2: #7c3aed;
    --text: #0f172a;
    --border: #e6e9ef;
    --mark: #fff59d;
    --shadow: 0 6px 24px rgba(12,18,30,0.06);
  }}
  [data-theme="dark"]{{
    --bg: #0b1020;
    --panel: #0f1724;
    --muted: #98a0b2;
    --accent: #60a5fa;
    --accent-2: #b794f4;
    --text: #e6eef8;
    --border: #1f2937;
    --mark: #7c5b00;
    --shadow: 0 6px 24px rgba(2,6,23,0.6);
  }}
  html,body{{height:100%;margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial; background:var(--bg); color:var(--text);}}
  .app{{display:flex; height:100vh; gap:18px; padding:18px; box-sizing:border-box;}}
  .sidebar{{
    width:320px; min-width:220px; max-width:38%;
    background:var(--panel); border-radius:12px; padding:12px; box-shadow:var(--shadow);
    border:1px solid var(--border); display:flex; flex-direction:column; overflow:hidden;
  }}
  .search{{display:flex; gap:8px; align-items:center; padding:8px;}}
  .search input{{flex:1; padding:8px 12px; border-radius:8px; border:1px solid var(--border); background:transparent;color:var(--text); outline:none; font-size:14px;}}
  .btn{{background:transparent;border:1px solid var(--border); color:var(--muted); padding:8px 10px;border-radius:8px; cursor:pointer;}}
  .controls{{display:flex; gap:8px; align-items:center; margin-left:6px;}}
  .list{{overflow:auto; padding:6px 6px 12px 6px;}}
  .item{{padding:10px;border-radius:10px; cursor:pointer; display:block; text-decoration:none; color:inherit; margin-bottom:8px; border:1px solid transparent;}}
  .item:hover{{background:linear-gradient(90deg, rgba(37,99,235,0.06), rgba(124,58,237,0.03)); border-color:rgba(37,99,235,0.06);}}
  .item.active{{box-shadow:var(--shadow); border-color:var(--border); background:linear-gradient(180deg, rgba(255,255,255,0.02), transparent);}}
  .title{{font-weight:600; font-size:15px; margin-bottom:6px;}}
  .meta{{font-size:13px; color:var(--muted);}}
  .preview{{font-size:13px; color:var(--muted); margin-top:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}}
  .main{{flex:1; min-width:0; display:flex; flex-direction:column; gap:12px;}}
  .topbar{{display:flex; align-items:center; gap:12px;}}
  .page-card{{background:var(--panel); border-radius:12px; padding:18px; border:1px solid var(--border); box-shadow:var(--shadow); overflow:auto; flex:1;}}
  .page-title{{margin:0 0 8px 0; display:flex; align-items:center; gap:12px;}}
  .page-title h1{{margin:0; font-size:20px;}}
  .badge{{padding:4px 8px;border-radius:999px;background:linear-gradient(90deg,var(--accent),var(--accent-2)); color:white; font-size:12px;}}
  .empty{{color:var(--muted); font-size:15px; text-align:center; padding:48px 12px;}}
  mark{{background:var(--mark); padding:0 2px; border-radius:3px; color:inherit;}}
  pre{{background:#0b1220;color:#dbeafe;padding:12px;border-radius:8px;overflow:auto}}
  code{{background:#0b1220;color:#dbeafe;padding:2px 6px;border-radius:6px}}
  .toolbar{{margin-left:auto; display:flex; gap:8px;}}
  .small{{font-size:13px;color:var(--muted)}}
  @media (max-width:900px){{
    .app{{flex-direction:column;padding:12px;}}
    .sidebar{{width:100%; max-width:none; order:2;}}
    .main{{order:1;}}
  }}
</style>
</head>
<body data-theme="light">
<div class="app" role="application" aria-label="Docs app">
  <aside class="sidebar" aria-label="Sidebar">
    <div class="search">
      <input id="search" type="search" placeholder="Search titles & content (press /)" aria-label="Search" />
      <div class="controls">
        <button id="themeToggle" class="btn" title="Toggle theme">🌙</button>
        <button id="clearSearch" class="btn" title="Clear search">✕</button>
      </div>
    </div>
    <div id="list" class="list" role="list"></div>
  </aside>

  <main class="main" aria-live="polite">
    <div class="topbar">
      <div class="small">Single-file interactive docs — native HTML content</div>
      <div class="toolbar">
        <button id="prevBtn" class="btn" title="Previous">◀</button>
        <button id="nextBtn" class="btn" title="Next">▶</button>
        <button id="copyLink" class="btn" title="Copy page link">🔗 Copy Link</button>
        <button id="copyHtml" class="btn" title="Copy page HTML">📋 Copy HTML</button>
      </div>
    </div>

    <section id="page" class="page-card">
      <div id="pageHeader" class="page-title"><h1>Welcome</h1><span class="badge">RTFM</span></div>
      <div id="content" class="page-content">
        <p class="empty">Choose a document on the left or use search to find content. This viewer renders HTML natively. Use the search box (or press /) to find matches. Click an item to show it here.</p>
      </div>
    </section>
  </main>
</div>

<script>
// Embedded pages dataset (generated from docs)
const pages = {pages_js};
// Configuration for client-side behavior
const __RTFM_CONFIG = {config_js};

// DOM refs
const listEl = document.getElementById('list');
const contentEl = document.getElementById('content');
const pageHeaderEl = document.getElementById('pageHeader');
const searchInput = document.getElementById('search');
const themeToggle = document.getElementById('themeToggle');
const clearSearch = document.getElementById('clearSearch');
const prevBtn = document.getElementById('prevBtn'), nextBtn = document.getElementById('nextBtn');
const copyLink = document.getElementById('copyLink');
const copyHtml = document.getElementById('copyHtml');

let currentId = null;
let query = '';
let theme = 'light';

function setTheme(t){
  document.body.setAttribute('data-theme', t);
  theme = t;
  themeToggle.textContent = t === 'light' ? '🌙' : '☀️';
}

function stripHtml(html){ const d = document.createElement('div'); d.innerHTML = html; return d.innerText || ''; }
function escapeHtml(s){ return s.replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function escapeRegExp(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

// Simple fuzzy score: higher is better. Exact substring -> high score, startsWith -> higher, otherwise character-sequence match score
function fuzzyScore(text, pattern){
  text = text.toLowerCase(); pattern = pattern.toLowerCase();
  if(text === pattern) return 1000;
  const idx = text.indexOf(pattern);
  if(idx !== -1) return 500 - idx; // earlier occurrence better
  // approximate: count matched characters in order
  let i = 0, j = 0, matches = 0;
  while(i < text.length && j < pattern.length){
    if(text[i] === pattern[j]){ matches++; j++; }
    i++;
  }
  return matches > 0 ? matches : 0;
}

function rankMatches(pagesArr, q){
  if(!q) return pagesArr.map(p => ({p, score:0}));
  const scored = pagesArr.map(p => {
    const hay = (p.title + ' ' + stripHtml(p.html)).toLowerCase();
    const s = fuzzyScore(hay, q);
    return {p, score:s};
  });
  scored.sort((a,b) => b.score - a.score);
  return scored.filter(x => x.score > 0);
}

function renderPage(id){
  const p = pages.find(x => x.id === id);
  currentId = id;
  Array.from(listEl.querySelectorAll('.item')).forEach(a => { a.classList.toggle('active', a.getAttribute('href') === ('#'+id)); });
  if(!p){ pageHeaderEl.innerHTML = '<h1>Not found</h1>'; contentEl.innerHTML = '<div class="empty">Document not found.</div>'; return; }
  pageHeaderEl.innerHTML = `<h1>${escapeHtml(p.title)}</h1><span class="badge">${(p.tags||[]).join(', ') || 'Document'}</span>`;

  // Decide how to render content based on config and page data
  if(__RTFM_CONFIG.renderMarkdown && p.md){
    // try to render markdown to HTML using marked if available; otherwise fall back to pre
    if(window.marked){
      try{
        let out = window.marked(p.md);
        if(__RTFM_CONFIG.sanitize && window.DOMPurify){ out = window.DOMPurify.sanitize(out); }
        contentEl.innerHTML = out;
      }catch(e){ contentEl.innerHTML = '<pre style="white-space:pre-wrap;">' + escapeHtml(p.md) + '</pre>'; }
    } else {
      // no marked: show escaped pre and optionally load marked for better rendering
      contentEl.innerHTML = '<pre style="white-space:pre-wrap;">' + escapeHtml(p.md) + '</pre>';
      // attempt to load marked dynamically to improve experience (best-effort)
      const s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
      s.crossOrigin = 'anonymous';
      s.onload = () => { try{ const out = window.marked(p.md); if(__RTFM_CONFIG.sanitize && window.DOMPurify) { contentEl.innerHTML = window.DOMPurify.sanitize(out); } else { contentEl.innerHTML = out; } }catch(e){} };
      s.onerror = () => {/* ignore */};
      document.head.appendChild(s);
    }
  } else {
    // Insert native HTML content
    let insertHtml = p.html;
    if(__RTFM_CONFIG.sanitize){
      if(window.DOMPurify){ insertHtml = window.DOMPurify.sanitize(insertHtml); contentEl.innerHTML = insertHtml; }
      else { contentEl.innerHTML = insertHtml; // still insert, try to load DOMPurify next
        const sd = document.createElement('script'); sd.src = 'https://cdn.jsdelivr.net/npm/dompurify@2.4.0/dist/purify.min.js'; sd.crossOrigin = 'anonymous'; sd.onload = () => { try{ contentEl.innerHTML = window.DOMPurify.sanitize(p.html); }catch(e){} }; document.head.appendChild(sd);
      }
    } else {
      contentEl.innerHTML = insertHtml;
    }
  }

  if(query) highlightMatches(contentEl, query);
  if(location.hash !== '#'+id) history.pushState(null,'','#'+id);
}

function navigateTofunction renderPage(id){ renderPage(id); }
function onHashChange(){ const id = location.hash ? location.hash.slice(1) : null; iffunction renderPage(id){ renderPage(id); } else { currentId = null; pageHeaderEl.innerHTML = '<h1>Welcome</h1><span class="badge">RTFM</span>'; contentEl.innerHTML = '<p class="empty">Choose a document on the left or use search to find content.</p>'; renderList(query); } }

function highlightMatches(container, q){ if(!q) return; const regex = new RegExp(escapeRegExp(q),'ig'); const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null); const nodes = []; while(walker.nextNode()) nodes.push(walker.currentNode); nodes.forEach(node => { if(!node.nodeValue.trim()) return; const parent = node.parentNode; if(parent && parent.closest && parent.closest('mark')) return; const text = node.nodeValue; if(regex.test(text)){ const frag = document.createDocumentFragment(); let lastIndex = 0; text.replace(regex, (m, idx) => { if(idx > lastIndex) frag.appendChild(document.createTextNode(text.slice(lastIndex, idx))); const mark = document.createElement('mark'); mark.textContent = m; frag.appendChild(mark); lastIndex = idx + m.length; return m; }); if(lastIndex < text.length) frag.appendChild(document.createTextNode(text.slice(lastIndex))); parent.replaceChild(frag, node); } }); }
function clearHighlights(container){ const marks = Array.from(container.querySelectorAll('mark')); marks.forEach(m => { m.replaceWith(document.createTextNode(m.textContent)); }); }
function highlightTextNode(el, q){ if(!q) return; const regex = new RegExp(escapeRegExp(q),'ig'); el.innerHTML = el.textContent.replace(regex, m => `<mark>${m}</mark>`); }

searchInput.addEventListener('input', (e) => { query = e.target.value.trim(); renderList(query); if(currentId) renderPage(currentId); else clearHighlights(contentEl); });
clearSearch.addEventListener('click', () => { searchInput.value = ''; searchInput.focus(); query = ''; renderList(''); if(currentId) renderPage(currentId); });
document.addEventListener('keydown', (e) => { if(e.key === '/' && document.activeElement !== searchInput){ e.preventDefault(); searchInput.focus(); searchInput.select(); } if(e.key === 'Escape'){ searchInput.blur(); } if(e.key === 'n' && (e.ctrlKey || e.metaKey)){ e.preventDefault(); goNext(); } if(e.key === 'p' && (e.ctrlKey || e.metaKey)){ e.preventDefault(); goPrev(); } });

themeToggle.addEventListener('click', () => setTheme(theme === 'light' ? 'dark' : 'light'));

function getCurrentIndex(){ if(!currentId) return -1; return pages.findIndex(p => p.id === currentId); }
function goNext(){ const idx = getCurrentIndex(); if(idx === -1) return; const next = pages[(idx + 1) % pages.length]; navigateTo(next.id); }
function goPrev(){ const idx = getCurrentIndex(); if(idx === -1) return; const prev = pages[(idx - 1 + pages.length) % pages.length]; navigateTo(prev.id); }
nextBtn.addEventListener('click', goNext); prevBtn.addEventListener('click', goPrev);
copyLink.addEventListener('click', () => { const url = location.href; navigator.clipboard?.writeText(url).then(() => { copyLink.textContent = '✓ Copied'; setTimeout(()=> copyLink.textContent = '🔗 Copy Link', 1200); }).catch(()=> { alert('Copy failed — your browser may not allow clipboard access.'); }); });
copyHtml.addEventListener('click', () => { try{ const html = contentEl.innerHTML; navigator.clipboard?.writeText(html).then(()=>{ copyHtml.textContent = '✓ Copied'; setTimeout(()=>copyHtml.textContent='📋 Copy HTML',1200); }).catch(()=>{ alert('Copy failed — your browser may not allow clipboard access.'); }); }catch(e){ alert('Copy failed: '+e.message); } });

// initial render
renderList(''); onHashChange(); window.addEventListener('hashchange', onHashChange);

// external API
window.docsApp = { addPage(page){ pages.push(page); renderList(query); }, openfunction renderPage(id){ navigateTo(id); } };

// If sanitize config is set, attempt to load DOMPurify proactively for better UX
if(__RTFM_CONFIG.sanitize && !window.DOMPurify){
  const sd = document.createElement('script'); sd.src = 'https://cdn.jsdelivr.net/npm/dompurify@2.4.0/dist/purify.min.js'; sd.crossOrigin = 'anonymous'; document.head.appendChild(sd);
}

</script>
</body>
</html>"""

    return tpl.replace('{pages_js}', pages_js).replace('{config_js}', config_js)


class DocsHandler(http.server.BaseHTTPRequestHandler):
    server_version = "rtfm/0.1"

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            html = self.server.get_html()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        sys.stderr.write("[http] %s - - %s\n" % (self.address_string(), format % args))


def run_server(path: str, include_private: bool, style: str, nowatchdog: bool, host: str = '0.0.0.0', port: int = 8000, render_markdown: bool = False, sanitize: bool = False, fuzzy_search: bool = False):
    docs = collect_docs(path, include_private=include_private, style=style)
    fingerprint = compute_mtime_fingerprint(path)
    html_cache = generate_html_from_docs(docs, render_markdown=render_markdown, sanitize=sanitize, fuzzy_search=fuzzy_search)
    html_lock = threading.Lock()

    def get_html():
        with html_lock:
            return html_cache

    stop_event = threading.Event()

    def watcher():
        nonlocal docs, fingerprint, html_cache
        while not stop_event.is_set():
            time.sleep(1.5)
            try:
                fp = compute_mtime_fingerprint(path)
                if fp != fingerprint:
                    new_docs = collect_docs(path, include_private=include_private, style=style)
                    new_html = generate_html_from_docs(new_docs, render_markdown=render_markdown, sanitize=sanitize, fuzzy_search=fuzzy_search)
                    with html_lock:
                        docs = new_docs
                        html_cache = new_html
                        fingerprint = fp
                    print('Files changed; regenerated docs.')
            except Exception as e:
                print('Watcher error:', e, file=sys.stderr)

    if not nowatchdog:
        th = threading.Thread(target=watcher, daemon=True)
        th.start()
    else:
        th = None

    class _Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        def __init__(self, server_address, RequestHandlerClass):
            super().__init__(server_address, RequestHandlerClass)
            self.get_html = get_html

    with _Server((host, port), DocsHandler) as httpd:
        sa = httpd.socket.getsockname()
        print(f"Serving HTTP on {sa[0]} port {sa[1]} (http://{host}:{port}/) ...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('Shutting down server...')
        finally:
            stop_event.set()
            if th is not None:
                th.join(timeout=1.0)


def export_docs(docs: Dict[str, Any], export_type: Optional[str], export_path: Optional[str], generatehtml: bool, render_markdown: bool, sanitize: bool, fuzzy_search: bool):
    if generatehtml:
        export_type = 'html'

    if export_type is None or export_type == 'markdown':
        if exporters is None:
            raise RuntimeError('rtfmlib.exporters not available')
        if export_path:
            if os.path.isdir(export_path) or export_path.endswith(os.path.sep):
                exporters.dump_markdown(docs, output_dir=export_path)
            else:
                parent = os.path.dirname(export_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(export_path, 'w', encoding='utf-8') as f:
                    for k, d in docs.items():
                        f.write(exporters.module_to_markdown(k, d))
                        f.write('\n\n---\n\n')
        else:
            exporters.dump_markdown(docs, output_dir=None)

    elif export_type == 'json':
        if exporters is None:
            raise RuntimeError('rtfmlib.exporters not available')
        if export_path:
            if os.path.isdir(export_path):
                out = os.path.join(export_path, 'docs.json')
                exporters.dump_json(docs, output_path=out)
            else:
                parent = os.path.dirname(export_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                exporters.dump_json(docs, output_path=export_path)
        else:
            exporters.dump_json(docs, output_path=None)

    elif export_type == 'html':
        html = generate_html_from_docs(docs, render_markdown=render_markdown, sanitize=sanitize, fuzzy_search=fuzzy_search)
        if export_path:
            if os.path.isdir(export_path):
                out = os.path.join(export_path, 'index.html')
                with open(out, 'w', encoding='utf-8') as f:
                    f.write(html)
            else:
                parent = os.path.dirname(export_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(html)
        else:
            print(html)
    else:
        raise ValueError(f'Unknown export type: {export_type}')


def main(argv=None):
    p = argparse.ArgumentParser(prog='rtfm', description='Generate documentation for Python code (minimal).')
    p.add_argument('--server', action='store_true', help='Start a webserver')
    p.add_argument('--nowatchdog', action='store_true', help="Don't watch for file changes when running the server")
    p.add_argument('--generatehtml', action='store_true', help='Produce HTML output')
    p.add_argument('--path', type=str, default='.', help='Path to files to document')
    p.add_argument('--export', type=str, choices=['markdown', 'json', 'html'], help='Export format')
    p.add_argument('--exportpath', type=str, help='Path to write exported docs (directory or file)')
    p.add_argument('--include-private', action='store_true', help='Include private members (starting with _)')
    p.add_argument('--style', type=str, default='auto', help='Docstring style hint (auto, numpy, google, rest, plain)')
    p.add_argument('--host', type=str, default='0.0.0.0', help='Host for server')
    p.add_argument('--port', type=int, default=8000, help='Port for server')
    p.add_argument('--render-markdown', action='store_true', help='Render markdown client-side when available')
    p.add_argument('--sanitize', action='store_true', help='Attempt to sanitize HTML client-side using DOMPurify')
    p.add_argument('--fuzzy-search', action='store_true', help='Enable fuzzy search ranking in the client')

    args = p.parse_args(argv)

    if parse_file is None or exporters is None:
        try:
            from rtfmlib.docgen import parse_file as _pf  # type: ignore
            from rtfmlib import exporters as _ex  # type: ignore
            globals()['parse_file'] = _pf
            globals()['exporters'] = _ex
        except Exception as e:
            print('Failed to import rtfmlib components:', e, file=sys.stderr)
            sys.exit(1)

    if args.server:
        try:
            run_server(args.path, include_private=args.include_private, style=args.style, nowatchdog=args.nowatchdog, host=args.host, port=args.port, render_markdown=args.render_markdown, sanitize=args.sanitize, fuzzy_search=args.fuzzy_search)
        except Exception as e:
            print('Failed to start server:', e, file=sys.stderr)
            sys.exit(1)
        return

    docs = collect_docs(args.path, include_private=args.include_private, style=args.style)

    try:
        export_docs(docs, args.export, args.exportpath, args.generatehtml, render_markdown=args.render_markdown, sanitize=args.sanitize, fuzzy_search=args.fuzzy_search)
    except Exception as e:
        print('Export failed:', e, file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
