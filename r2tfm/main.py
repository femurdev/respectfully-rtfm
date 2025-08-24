"""
Streamlit web app that generates browsable documentation from what
pydoccrawler finds in Python codebases (docstrings + inline comments),
including function signatures (args/types/defaults/returns), with export
to Markdown or JSON.

Run:
  pip install streamlit pydoccrawler
  streamlit run docsite_app.py

If you're developing both side-by-side, `pip install -e .` from the
pydoccrawler repo first.
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Tuple

import streamlit as st

try:
    # Your refactored library should provide the same interface
    # and embed function signatures in the parsed structure.
    from rtfmlib.crawler import DocCrawler
except Exception as e:
    st.warning(
        "Couldn't import `pydoccrawler`. Install it with `pip install -e .` from your repo or `pip install pydoccrawler` if published.\n\n"
        f"Import error: {e}"
    )
    DocCrawler = None  # type: ignore

# --------------------------- Helpers ---------------------------

def flatten_docs(doc_tree: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """Return list of (key, docs) where key is a file path or import marker.
    Note: we filter to dict-like values to avoid raw strings for builtins.
    """
    items: List[Tuple[str, Dict[str, Any]]] = []
    for k, v in doc_tree.items():
        if isinstance(v, dict):
            items.append((k, v))
    # Flip the array of files around before rendering (reverse order)
    items.sort(key=lambda kv: kv[0])
    items = list(reversed(items))
    return items

def _coerce(obj):
        if isinstance(obj, set):
            return list(obj)
        return obj

def search_hits(docs: Dict[str, Any], q: str) -> bool:
    q = q.lower().strip()
    if not q:
        return True
    try:
        blob = json.dumps(docs, default=_coerce, ensure_ascii=False).lower()
        return q in blob
    except Exception:
        return False


def fmt_signature(sig: Dict[str, Any] | None) -> str:
    if not sig:
        return "()"
    args = sig.get("args", []) or []
    returns = sig.get("returns")
    parts: List[str] = []
    for a in args:
        name = a.get("name") or "_"
        t = a.get("type")
        d = a.get("default")
        s = name
        if t:
            s += f": {t}"
        if d is not None:
            s += f" = {d}"
        parts.append(s)
    sig_str = f"({', '.join(parts)})"
    if returns:
        sig_str += f" -> {returns}"
    return sig_str


def docnode_to_markdown(name: str, node: Any, level: int = 2) -> str:
    """Render a single class/function or module section to Markdown."""
    md: List[str] = []
    h = "#" * max(1, min(6, level))

    if isinstance(node, dict) and ("__doc__" in node or "__comments__" in node):
        # If it's a function/method node with a signature, include it in the heading
        sig = node.get("signature") if isinstance(node, dict) else None
        title = name
        if sig and (name.startswith("def ") or name.startswith("method: ") or name.startswith("function:")):
            title += f" {fmt_signature(sig)}"
        md.append(f"{h} {title}")

        doc = node.get("__doc__")
        if doc:
            md.append("\n" + str(doc).strip() + "\n")

        comments = node.get("__comments__", [])
        if comments:
            md.append("**Inline comments**:")
            for c in comments:
                md.append(f"- {c}")

        # nested methods if it's a class
        for k, v in node.items():
            if k in {"__doc__", "__comments__", "signature"}:
                continue
            if isinstance(v, dict) and ("__doc__" in v or "__comments__" in v):
                subtitle = k
                if v.get("signature") and (k.startswith("method:") or k.startswith("function:")):
                    subtitle += f" {fmt_signature(v.get('signature'))}"
                md.append(docnode_to_markdown(subtitle, v, level + 1))

    return "\n".join(md)


def file_docs_to_markdown(filepath_key: str, docs: Dict[str, Any]) -> str:
    md: List[str] = []
    md.append(f"# {os.path.basename(filepath_key)}")

    if "__module__" in docs and docs["__module__"]:
        md.append("\n" + str(docs["__module__"]).strip() + "\n")

    comments = docs.get("__comments__", [])
    if comments:
        md.append("## Module Inline Comments")
        for c in comments:
            md.append(f"- {c}")

    # classes / functions
    for k, v in docs.items():
        if k.startswith("class:"):
            md.append(docnode_to_markdown(k.replace("class:", "class "), v, 2))
    for k, v in docs.items():
        if k.startswith("function:"):
            title = k.replace("function:", "def ")
            md.append(docnode_to_markdown(title, v, 2))

    # imports summary if present in this node (often stored only at crawl-level markers)
    imports = docs.get("__imports__")
    if imports:
        md.append("## Imports\n")
        for imp in imports:
            md.append(f"- `{imp}`")

    return "\n\n".join([s for s in md if s])


def entire_site_markdown(doc_tree: Dict[str, Any]) -> str:
    parts: List[str] = ["# Project Documentation\n"]
    for key, docs in flatten_docs(doc_tree):
        if key.startswith("__import__:"):
            # render a short stub for imports
            parts.append(f"\n## {key}\n")
            if isinstance(docs, dict):
                origin = docs.get("__package__", "(package or module)")
                parts.append(f"Origin: `{origin}`\n")
            else:
                parts.append(f"{docs}\n")
            continue
        parts.append(file_docs_to_markdown(key, docs))
    return "\n\n".join(parts)


# --------------------------- UI ---------------------------

st.set_page_config(page_title="Python Doc Site Generator", layout="wide")
st.title("🐍 Python Doc Site Generator")

with st.sidebar:
    st.header("Crawl Settings")
    project_path = st.text_input("Project path", value=os.getcwd())
    max_modules = st.number_input("Max modules", min_value=1, max_value=50000, value=5, step=10)
    max_file_size = st.number_input("Max file size (bytes)", min_value=10000, max_value=50_000_000, value=2_000_000, step=10000)
    follow = st.checkbox("Follow dependency tree (external libraries)", value=True)
    run = st.button("🚀 Crawl Project", type="primary", use_container_width=True)

if "doc_tree" not in st.session_state:
    st.session_state.doc_tree = None

if run:
    if not DocCrawler:
        st.stop()
    crawler = DocCrawler(max_modules=int(max_modules), max_file_size_bytes=int(max_file_size), follow_dependency_tree=bool(follow))

    with st.status("Crawling… This may take a while for big dependency trees.", expanded=True) as status:
        st.write(f"Scanning: `{project_path}`")
        results = crawler.crawl_directory(project_path)
        st.session_state.doc_tree = results
        status.update(label="Done", state="complete")

# --------------- Results / Exploration ---------------

doc_tree: Dict[str, Any] | None = st.session_state.doc_tree

if not doc_tree:
    st.info("Run a crawl to generate documentation.")
    st.stop()

st.subheader("Overview")
items = flatten_docs(doc_tree)
left, right = st.columns([1, 3], gap="large")

with left:
    st.caption("Files & Import Markers (reversed order)")
    query = st.text_input("Search (full-text)")
    filtered = [(k, v) for (k, v) in items if search_hits(v, query)]
    st.write(f"Showing **{len(filtered)}** of **{len(items)}** entries")

    # Simple navigator list (reversed was already applied in flatten_docs)
    for key, _ in filtered:
        if st.button(key, use_container_width=True):
            st.session_state["active_key"] = key

active_key = st.session_state.get("active_key", (filtered[0][0] if filtered else (items[0][0] if items else None)))

with right:
    if not active_key:
        st.warning("No entries to display.")
    else:
        docs = doc_tree.get(active_key, {})
        st.markdown(f"### {active_key}")

        if isinstance(docs, dict):
            # Module docstring
            if docs.get("__module__"):
                with st.expander("Module docstring", expanded=True):
                    st.markdown(docs["__module__"])  # docstring may contain Markdown-like text

            # Module inline comments
            if docs.get("__comments__"):
                with st.expander("Module inline comments"):
                    for c in docs["__comments__"]:
                        st.markdown(f"- {c}")

            # Classes
            class_keys = [k for k in docs.keys() if k.startswith("class:")]
            if class_keys:
                st.markdown("#### Classes")
            for ck in class_keys:
                cnode = docs[ck]
                with st.expander(ck):
                    if isinstance(cnode, dict):
                        if cnode.get("__doc__"):
                            st.markdown(cnode["__doc__"])
                        if cnode.get("__comments__"):
                            st.markdown("**Comments:**")
                            for c in cnode["__comments__"]:
                                st.markdown(f"- {c}")
                        # Methods
                        method_keys = [mk for mk in cnode.keys() if mk not in {"__doc__", "__comments__", "signature"}]
                        for mk in method_keys:
                            mnode = cnode.get(mk)
                            with st.expander(f"method: {mk}"):
                                if isinstance(mnode, dict):
                                    # Signature line
                                    sig = mnode.get("signature")
                                    if sig:
                                        st.code(f"{mk}{fmt_signature(sig)}")
                                    if mnode.get("__doc__"):
                                        st.markdown(mnode["__doc__"])
                                    if mnode.get("__comments__"):
                                        st.markdown("**Comments:**")
                                        for c in mnode["__comments__"]:
                                            st.markdown(f"- {c}")

            # Functions
            func_keys = [k for k in docs.keys() if k.startswith("function:")]
            if func_keys:
                st.markdown("#### Functions")
            for fk in func_keys:
                fnode = docs[fk]
                with st.expander(fk):
                    if isinstance(fnode, dict):
                        # Signature line
                        sig = fnode.get("signature")
                        if sig:
                            name = fk.replace("function:", "")
                            st.code(f"{name}{fmt_signature(sig)}")
                        if fnode.get("__doc__"):
                            st.markdown(fnode["__doc__"])
                        if fnode.get("__comments__"):
                            st.markdown("**Comments:**")
                            for c in fnode["__comments__"]:
                                st.markdown(f"- {c}")

            # Imports (if stored on this node)
            if docs.get("__imports__"):
                with st.expander("Imports in this module"):
                    for imp in docs["__imports__"]:
                        st.code(imp)
        else:
            st.code(str(docs))

# --------------- Exports ---------------

st.subheader("Export")
col1, col2 = st.columns(2)

with col1:
    md = entire_site_markdown(doc_tree)
    md_bytes = md.encode("utf-8")
    st.download_button(
        label="⬇️ Download Markdown",
        data=md_bytes,
        file_name="documentation.md",
        mime="text/markdown",
    )

with col2:
    json_bytes = json.dumps(doc_tree, ensure_ascii=False, default=_coerce, indent=2).encode("utf-8")
    st.download_button(
        label="⬇️ Download JSON",
        data=json_bytes,
        file_name="documentation.json",
        mime="application/json",
    )

st.caption("Tip: Use the search box to quickly locate symbols or comments across all files.")
