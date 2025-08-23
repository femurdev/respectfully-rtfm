"""Simple exporters for rtfmlib: markdown and JSON helpers.

The markdown exporter is intentionally minimal: it generates human-readable
markdown for each module including constants, classes, methods and functions.
It can either print to stdout or write files to an output directory.
"""
from typing import Dict, Any, Optional
import os
import json


def _format_sig_md(sig) -> str:
    if not sig:
        return '()'
    parts = []
    for p in sig:
        prefix = '*' if p.get('kind') == 'vararg' else ('**' if p.get('kind') == 'varkw' else '')
        ann = f": {p.get('annotation')}" if p.get('annotation') else ''
        default = f"={p.get('default')}" if p.get('default') is not None else ''
        parts.append(f"{prefix}{p.get('name')}{ann}{default}")
    return '(' + ', '.join(parts) + ')'


def module_to_markdown(key: str, doc: Dict[str, Any]) -> str:
    lines = []
    title = doc.get('file') or key
    lines.append(f"# {title}")
    lines.append('')
    if doc.get('docstring'):
        lines.append(doc.get('docstring'))
        lines.append('')

    if doc.get('constants'):
        lines.append('## Constants')
        lines.append('')
        for c in doc.get('constants'):
            lines.append(f"- **{c.get('name')}** = `{c.get('value')}`")
        lines.append('')

    if doc.get('classes'):
        lines.append('## Classes')
        lines.append('')
        for cls in doc.get('classes'):
            lines.append(f"### {cls.get('name')}")
            lines.append('')
            if cls.get('docstring'):
                lines.append(cls.get('docstring'))
                lines.append('')
            if cls.get('methods'):
                lines.append('Methods:')
                lines.append('')
                for m in cls.get('methods'):
                    sig = _format_sig_md(m.get('signature'))
                    lines.append(f"- `{m.get('name')}{sig}` — { (m.get('docstring') or '').splitlines()[0] if m.get('docstring') else '' }")
                lines.append('')

    if doc.get('functions'):
        lines.append('## Functions')
        lines.append('')
        for fn in doc.get('functions'):
            sig = _format_sig_md(fn.get('signature'))
            lines.append(f"- `{fn.get('name')}{sig}` — { (fn.get('docstring') or '').splitlines()[0] if fn.get('docstring') else '' }")
        lines.append('')

    return '\n'.join(lines)


def dump_markdown(docs: Dict[str, Any], output_dir: Optional[str] = None):
    """Dump docs mapping to markdown. If output_dir is None, print combined markdown to stdout.

    If output_dir is provided, a file is created per module with sanitized path.
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for key, doc in docs.items():
            # sanitize key into a filepath
            fname = key.replace('/', '_')
            path = os.path.join(output_dir, f"{fname}.md")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(module_to_markdown(key, doc))
    else:
        # print combined
        out = []
        for key, doc in docs.items():
            out.append(module_to_markdown(key, doc))
            out.append('\n---\n')
        print('\n'.join(out))


def dump_json(docs: Dict[str, Any], output_path: Optional[str] = None):
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(docs, indent=2, ensure_ascii=False))
