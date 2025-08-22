"""Single entrypoint CLI for the documentation generator.

Usage examples:
  python3 pydocgen.py --path . --format json
  python3 pydocgen.py --path mypkg --format web
  python3 pydocgen.py --path file.py --format md --output docs

This script dispatches to DocGenerator for parsing and to exporters or the
live web server when requested. When --output is omitted for export formats,
output is printed to stdout.
"""

import argparse
import json
import os
import sys
from docgen import DocGenerator


def dump_json(docs, output_dir=None):
    s = json.dumps(docs, indent=2)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_file = os.path.join(output_dir, 'documentation.json')
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(s)
        print(f'Wrote JSON to {out_file}')
    else:
        print(s)


def dump_md(docs, output_dir=None):
    """Generate a simple markdown document from docs.

    Accepts either a mapping (module -> doc) or a list of doc dicts. If
    output_dir is provided, writes documentation.md into that directory.
    Otherwise prints to stdout.
    """
    # Normalize docs to a list of module docs
    if isinstance(docs, dict):
        mod_docs = list(docs.values())
    else:
        mod_docs = list(docs)

    lines = ['# Documentation']
    for doc in mod_docs:
        # doc may be a simple dict with 'file' key or a string; be defensive
        file_label = doc.get('file') if isinstance(doc, dict) else str(doc)
        lines.append(f"\n## {file_label}\n")
        if isinstance(doc, dict) and doc.get('docstring'):
            lines.append('> ' + '\n> '.join(doc['docstring'].splitlines()))
        if isinstance(doc, dict) and doc.get('constants'):
            lines.append('\n### Constants')
            for c in doc['constants']:
                # c expected to be {'name':..., 'value':...}
                lines.append(f"- {c.get('name')} = {c.get('value')}")
        if isinstance(doc, dict) and doc.get('classes'):
            lines.append('\n### Classes')
            for cls in doc['classes']:
                lines.append(f"#### {cls.get('name')}")
                if cls.get('docstring'):
                    lines.append('\n' + cls['docstring'])
                if cls.get('methods'):
                    lines.append('\nMethods:')
                    for m in cls['methods']:
                        sig = format_signature(m.get('signature'))
                        lines.append(f"- {m.get('name')}{sig} - {m.get('docstring') or ''}")
        if isinstance(doc, dict) and doc.get('functions'):
            lines.append('\n### Functions')
            for fn in doc['functions']:
                sig = format_signature(fn.get('signature'))
                lines.append(f"- {fn.get('name')}{sig} - {fn.get('docstring') or ''}")
    out = '\n'.join(lines)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        out_file = os.path.join(output_dir, 'documentation.md')
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(out)
        print(f'Wrote MD to {out_file}')
    else:
        print(out)


def format_signature(sig_parts):
    if not sig_parts:
        return '()'
    parts = []
    for p in sig_parts:
        s = p.get('name', '')
        if p.get('annotation'):
            s += ': ' + p['annotation']
        if p.get('default'):
            s += ' = ' + p['default']
        if p.get('kind') == 'vararg':
            s = '*' + s
        if p.get('kind') == 'varkw':
            s = '**' + s
        parts.append(s)
    return '(' + ', '.join(parts) + ')'


def start_web(path, include_private, style, host='127.0.0.1', port=5000, interval=5.0):
    # Lazy import to avoid requiring Flask when not running web mode
    from live_web_server import start_server
    start_server(path=path, include_private=include_private, style=style, host=host, port=port, interval=interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description='pydocgen - AST documentation generator')
    parser.add_argument('--path', default=os.getcwd(), help='Path to file or package (default cwd)')
    parser.add_argument('--include-private', action='store_true', help='Include members starting with a single underscore')
    parser.add_argument('--style', default='auto', choices=['auto', 'google', 'numpy', 'rest', 'plain'])
    parser.add_argument('--format', choices=['web', 'json', 'md'], default='web', help='Output format or web server')
    parser.add_argument('--output', help='Output directory for generated files (if omitted prints to stdout)')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--interval', type=float, default=5.0, help='Polling interval for web server scanner')

    args = parser.parse_args(argv)

    if args.format == 'web':
        start_web(args.path, args.include_private, args.style, host=args.host, port=args.port, interval=args.interval)
        return

    gen = DocGenerator(path=args.path, include_private=args.include_private, style=args.style)
    docs = gen.parse()

    if args.format == 'json':
        dump_json(docs, args.output)
    elif args.format == 'md':
        dump_md(docs, args.output)


if __name__ == '__main__':
    main()
