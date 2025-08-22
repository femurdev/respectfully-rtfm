"""DocCache: thread-safe documentation cache with mtime fingerprinting and inverted index.

This module provides DocCache, a reusable component suitable for embedding into
web servers or other tools that need to keep an up-to-date view of parsed
Python documentation for a path.

It intentionally does not depend on Flask or any web framework; it simply
maintains parsed docs, an inverted index, and exposes a snapshot and search
API that are safe to call from multiple threads.
"""

from typing import Optional, Dict, Any, List
import threading
import time
import hashlib
import os
import re

from .docgen import DocGenerator, parse_file
from .utils import logger


class DocCache:
    """Thread-safe documentation cache.

    Usage:
      cache = DocCache(path)
      cache.scan_and_update()  # parse initial set
      snapshot = cache.snapshot()  # safe copy for readers
      results = cache.search('query')

    The cache keeps a per-file mtime map so repeated scans only reparse changed
    files. It also builds a simple inverted index mapping tokens to result keys
    for quick search.
    """

    def __init__(self, path: str, include_private: bool = False, style: str = 'auto'):
        self.path = path
        self.include_private = include_private
        self.style = style
        self.lock = threading.Lock()
        self.docs: Optional[Dict[str, Any]] = None
        self.last_updated: float = 0.0
        # fingerprint and per-file mtimes
        self._mtimes: Dict[str, Any] = {}
        self._file_mtimes: Dict[str, float] = {}
        self._re_split = re.compile(r'[^0-9a-zA-Z_]+')
        self.index: Dict[str, Dict[str, int]] = {}
        self.meta: Dict[str, Dict[str, Any]] = {}

    def compute_mtime_fingerprint(self) -> str:
        hasher = hashlib.sha1()
        entries: List[tuple] = []

        if os.path.isfile(self.path):
            try:
                rel = os.path.basename(self.path).replace(os.path.sep, '/')
                m = os.path.getmtime(self.path)
                entries.append((rel, m))
            except OSError:
                pass
        else:
            for root, dirs, files in os.walk(self.path):
                dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
                for fn in files:
                    if not fn.endswith('.py'):
                        continue
                    try:
                        p = os.path.join(root, fn)
                        rel = os.path.relpath(p, self.path).replace(os.path.sep, '/')
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

    def _tokenize_for_index(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        toks = [t.lower() for t in self._re_split.split(text) if t]
        return toks

    def _build_index(self, docs: Dict[str, Any]):
        idx: Dict[str, Dict[str, int]] = {}
        meta: Dict[str, Dict[str, Any]] = {}

        for module_key, doc in (docs or {}).items():
            try:
                file_field = doc.get('file') if isinstance(doc, dict) else module_key
            except Exception:
                file_field = module_key

            module_doc = (doc.get('docstring') or '') if isinstance(doc, dict) else ''
            snippet = ''
            if module_doc:
                lines = [l.strip() for l in module_doc.splitlines() if l.strip()]
                if lines:
                    snippet = lines[0][:200]

            module_result_key = module_key
            meta[module_result_key] = {'key': module_key, 'file': file_field, 'fqn': module_key, 'snippet': snippet, 'type': 'module'}

            sources_by_key: Dict[str, List[str]] = {module_result_key: [module_key, module_doc]}

            if isinstance(doc, dict):
                for cls in doc.get('classes', []) or []:
                    cls_name = cls.get('name') or ''
                    cls_doc = cls.get('docstring') or ''
                    cls_fqn = f"{module_key}::{cls_name}" if cls_name else f"{module_key}::class"
                    cls_key = cls_fqn
                    cls_snip = ''
                    if cls_doc:
                        lines = [l.strip() for l in cls_doc.splitlines() if l.strip()]
                        if lines:
                            cls_snip = lines[0][:200]
                    meta[cls_key] = {'key': module_key, 'file': file_field, 'fqn': cls_fqn, 'snippet': cls_snip, 'type': 'class'}
                    sources_by_key[cls_key] = [cls_name, cls_doc]

                    for m in cls.get('methods', []) or []:
                        m_name = m.get('name') or ''
                        m_doc = m.get('docstring') or ''
                        m_fqn = f"{cls_fqn}#{m_name}" if m_name else f"{cls_fqn}#method"
                        m_key = m_fqn
                        m_snip = ''
                        if m_doc:
                            lines = [l.strip() for l in m_doc.splitlines() if l.strip()]
                            if lines:
                                m_snip = lines[0][:200]
                        meta[m_key] = {'key': module_key, 'file': file_field, 'fqn': m_fqn, 'snippet': m_snip, 'type': 'method'}
                        sources_by_key[m_key] = [m_name, m_doc]

                for fn in doc.get('functions', []) or []:
                    fn_name = fn.get('name') or ''
                    fn_doc = fn.get('docstring') or ''
                    fn_fqn = f"{module_key}::{fn_name}" if fn_name else f"{module_key}::function"
                    fn_key = fn_fqn
                    fn_snip = ''
                    if fn_doc:
                        lines = [l.strip() for l in fn_doc.splitlines() if l.strip()]
                        if lines:
                            fn_snip = lines[0][:200]
                    meta[fn_key] = {'key': module_key, 'file': file_field, 'fqn': fn_fqn, 'snippet': fn_snip, 'type': 'function'}
                    sources_by_key[fn_key] = [fn_name, fn_doc]

            for result_key, sources in sources_by_key.items():
                counts: Dict[str, int] = {}
                for src in sources:
                    for tok in self._tokenize_for_index(src):
                        if not tok:
                            continue
                        counts[tok] = counts.get(tok, 0) + 1
                for tok, c in counts.items():
                    idx.setdefault(tok, {})
                    idx[tok][result_key] = idx[tok].get(result_key, 0) + c
                    max_pref = min(len(tok), 6)
                    for i in range(2, max_pref + 1):
                        pref = tok[:i]
                        idx.setdefault(pref, {})
                        idx[pref][result_key] = idx[pref].get(result_key, 0) + c

        return idx, meta

    def _iter_files(self):
        """Yield (module_key, abs_path, mtime) for Python files under self.path.

        module_key is normalized to posix-style relative path or basename for single-file mode.
        """
        if os.path.isfile(self.path):
            try:
                p = self.path
                m = os.path.getmtime(p)
                key = os.path.basename(p).replace(os.path.sep, '/')
                yield key, p, m
            except OSError:
                return
            return
        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.venv', 'venv')]
            for fn in files:
                if not fn.endswith('.py'):
                    continue
                p = os.path.join(root, fn)
                try:
                    m = os.path.getmtime(p)
                except OSError:
                    continue
                rel = os.path.relpath(p, self.path).replace(os.path.sep, '/')
                yield rel, p, m

    def scan_and_update(self) -> bool:
        """Scan files and incrementally update parsed docs and the index.

        Returns True if any change occurred (added/removed/modified files), False otherwise.
        """
        try:
            # Compute current fingerprint quickly; avoid reparsing if unchanged
            fingerprint = self.compute_mtime_fingerprint()
            if fingerprint == self._mtimes.get('fingerprint') and self.docs is not None:
                return False

            # incremental parse: only (re)parse files whose mtimes changed
            new_docs: Dict[str, Any] = dict(self.docs) if self.docs else {}
            new_file_mtimes: Dict[str, float] = dict(self._file_mtimes) if self._file_mtimes else {}
            seen_keys = set()
            errors = []

            for key, path, mtime in self._iter_files():
                seen_keys.add(key)
                prev_mtime = self._file_mtimes.get(key)
                if prev_mtime is not None and prev_mtime == mtime and key in new_docs:
                    # unchanged
                    new_file_mtimes[key] = mtime
                    continue
                # changed or new -> parse
                try:
                    parsed = parse_file(path, include_private=self.include_private, style=self.style)
                    if parsed is None:
                        # parsing failed; skip and remove if previously present
                        if key in new_docs:
                            new_docs.pop(key, None)
                            new_file_mtimes.pop(key, None)
                        errors.append((path, 'parse_failed'))
                        continue
                    new_docs[key] = parsed
                    new_file_mtimes[key] = mtime
                except Exception as e:
                    errors.append((path, str(e)))
                    # on exception, don't crash; skip file
                    continue

            # detect deleted files (present previously but not seen now)
            if self.docs:
                for old_key in list(self.docs.keys()):
                    if old_key not in seen_keys:
                        new_docs.pop(old_key, None)
                        new_file_mtimes.pop(old_key, None)

            # build index/meta from new_docs (outside lock)
            try:
                new_idx, new_meta = self._build_index(new_docs)
            except Exception:
                new_idx, new_meta = {}, {}

            # atomically swap
            with self.lock:
                self.docs = new_docs
                self._file_mtimes = new_file_mtimes
                self.last_updated = time.time()
                self._mtimes['fingerprint'] = fingerprint
                self.index = new_idx
                self.meta = new_meta

            if errors:
                logger.debug('DocCache scan encountered errors: %s', errors)

            return True
        except Exception as e:
            try:
                logger.error("Error updating docs: %s", e)
            except Exception:
                print("Error updating docs:", e)
            return False

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            docs_copy = dict(self.docs) if self.docs else {}
            meta_copy = dict(self.meta) if self.meta else {}
            idx_len = len(self.index) if self.index else 0
            return {'docs': docs_copy, 'meta': meta_copy, 'index_keys': idx_len, 'last_updated': self.last_updated}

    def search(self, query: str, limit: int = 50, page: int = 1) -> List[Dict[str, Any]]:
        q = (query or '').strip().lower()
        if not q:
            with self.lock:
                all_keys = sorted([k for k, v in self.meta.items() if v.get('type') == 'module'])
                start = (page - 1) * limit
                end = start + limit
                return [self.meta.get(k) for k in all_keys[start:end]]

        tokens = [t for t in self._tokenize_for_index(q) if t]
        if not tokens:
            return []

        with self.lock:
            results_sets: List[set] = []
            for tok in tokens:
                matched = set()
                if tok in self.index:
                    matched.update(self.index.get(tok, {}).keys())
                if not matched and len(tok) > 6:
                    pref = tok[:6]
                    matched.update(self.index.get(pref, {}).keys())
                if not matched:
                    return []
                results_sets.append(matched)

            out = set.intersection(*results_sets) if results_sets else set()
            scores: Dict[str, int] = {}
            for tok in tokens:
                postings = self.index.get(tok) or {}
                for rk, cnt in postings.items():
                    if rk in out:
                        scores[rk] = scores.get(rk, 0) + cnt

            sorted_keys = sorted(out, key=lambda k: (-scores.get(k, 0), self.meta.get(k, {}).get('fqn', k)))
            start = (page - 1) * limit
            end = start + limit
            page_keys = sorted_keys[start:end]
            results: List[Dict[str, Any]] = []
            for k in page_keys:
                m = dict(self.meta.get(k, {}))
                m['score'] = scores.get(k, 0)
                results.append(m)
            return results
