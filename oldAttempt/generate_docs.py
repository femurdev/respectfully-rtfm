#!/usr/bin/env python3
"""
generate_docs.py

Simple generator to update the embedded pages JSON in docs.html from a directory
of source files (HTML or Markdown) or from a single docs.json input file.

Usage:
  python3 generate_docs.py --input-dir docs/ --template docs.html --output docs.html
  python3 generate_docs.py --input-json pages.json --template docs.html --output docs.html

Options:
  --sanitize   : attempt to sanitize HTML content at build time using bleach (optional).

The script finds the <script id="rtfm-data" type="application/json">...</script>
block in the template and replaces its contents with the generated JSON array.

For .md files the generator places the markdown into the `md` field and a
minimal escaped pre into `html` so the viewer can render markdown when toggled.
For .html files the file is used as the `html` field (optionally sanitized).

"""
import argparse
import json
import sys
from pathlib import Path

try:
    import bleach
except Exception:
    bleach = None


def maybe_sanitize(html: str, do_sanitize: bool) -> str:
    if not do_sanitize:
        return html
    if bleach is None:
        print('Warning: bleach not installed, skipping build-time sanitization')
        return html
    # allow a reasonable superset of typical documentation tags
    allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS) | set([
        'h1', 'h2', 'h3', 'h4', 'pre', 'code', 'div', 'span', 'p', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'em', 'strong'])
    allowed_attrs = {
        '*': ['class', 'id', 'title', 'style'],
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
    }
    try:
        return bleach.clean(html, tags=list(allowed_tags), attributes=allowed_attrs, strip=True)
    except Exception as e:
        print('Warning: bleach.clean failed:', e)
        return html


def collect_from_dir(path: Path, sanitize: bool):
    pages = []
    for p in sorted(path.iterdir()):
        if p.is_dir():
            continue
        name = p.name
        if p.suffix.lower() in ('.md', '.markdown'):
            md = p.read_text(encoding='utf-8')
            # keep pre-wrapped HTML for the viewer's html field; do not render markdown here
            html = '<div class="rtfm-markdown"><pre style="white-space:pre-wrap;">' + md.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '</pre></div>'
            # sanitizing the pre is unnecessary, but honor sanitize flag for consistency
            html = maybe_sanitize(html, sanitize)
            pages.append({'id': name, 'title': name, 'tags': [], 'html': html, 'md': md})
        elif p.suffix.lower() in ('.html', '.htm'):
            raw = p.read_text(encoding='utf-8')
            html = maybe_sanitize(raw, sanitize)
            pages.append({'id': name, 'title': name, 'tags': [], 'html': html})
        else:
            # treat other text files as preformatted content
            try:
                txt = p.read_text(encoding='utf-8')
                html = '<pre style="white-space:pre-wrap;">' + txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '</pre>'
                html = maybe_sanitize(html, sanitize)
                pages.append({'id': name, 'title': name, 'tags': [], 'html': html})
            except Exception:
                # binary or unreadable: skip
                continue
    return pages


def collect_from_json(path: Path, sanitize: bool):
    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, dict) and 'pages' in data:
        pages = data['pages']
    elif isinstance(data, list):
        pages = data
    else:
        raise SystemExit('Unsupported JSON structure in {}'.format(path))
    # optionally sanitize any html fields
    if sanitize:
        for p in pages:
            if 'html' in p and isinstance(p['html'], str):
                p['html'] = maybe_sanitize(p['html'], True)
    return pages


def replace_json_in_template(template_text: str, pages_list):
    start_tag = '<script id="rtfm-data" type="application/json">'
    start = template_text.find(start_tag)
    if start == -1:
        raise SystemExit('Template does not contain rtfm-data script tag')
    start_end = template_text.find('>', start)
    if start_end == -1:
        raise SystemExit('Malformed script tag')
    end_tag = '</script>'
    end = template_text.find(end_tag, start_end)
    if end == -1:
        raise SystemExit('Template missing closing </script> for rtfm-data')
    before = template_text[:start_end+1]
    after = template_text[end:]
    pages_json = json.dumps(pages_list, ensure_ascii=False, indent=2)
    return before + '\n' + pages_json + '\n' + after


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--input-dir', help='Directory containing .html or .md files')
    p.add_argument('--input-json', help='JSON file with pages array or {"pages": [...]}')
    p.add_argument('--template', required=True, help='Path to docs.html template to update')
    p.add_argument('--output', required=True, help='Output path for generated docs.html')
    p.add_argument('--sanitize', action='store_true', help='Sanitize HTML content at build time (requires bleach)')
    args = p.parse_args(argv)

    pages = []
    if args.input_dir:
        d = Path(args.input_dir)
        if not d.exists() or not d.is_dir():
            raise SystemExit('input-dir does not exist or is not a directory')
        pages = collect_from_dir(d, args.sanitize)
    elif args.input_json:
        j = Path(args.input_json)
        if not j.exists():
            raise SystemExit('input-json not found')
        pages = collect_from_json(j, args.sanitize)
    else:
        raise SystemExit('Either --input-dir or --input-json must be provided')

    tpl_path = Path(args.template)
    if not tpl_path.exists():
        raise SystemExit('Template file not found: {}'.format(tpl_path))
    tpl = tpl_path.read_text(encoding='utf-8')

    out_text = replace_json_in_template(tpl, pages)
    out_path = Path(args.output)
    out_path.write_text(out_text, encoding='utf-8')
    print('Wrote', out_path)


if __name__ == '__main__':
    main()
