#!/usr/bin/env python3
import sys, json, re, pathlib
p = pathlib.Path('docs.html')
if not p.exists():
    print('docs.html not found')
    sys.exit(1)
text = p.read_text(encoding='utf-8')
m = re.search(r"<script[^>]*id=\"rtfm-data\"[^>]*>([\s\S]*?)</script>", text)
if not m:
    print('ERROR: rtfm-data script tag not found')
    sys.exit(2)
js = m.group(1).strip()
try:
    data = json.loads(js)
    print('OK: parsed rtfm-data JSON with', len(data), 'pages')
    # sanity check keys
    for i,p in enumerate(data):
        if not isinstance(p, dict):
            print('page {} is not an object'.format(i)); sys.exit(3)
        if 'id' not in p or 'title' not in p or 'html' not in p:
            print('page {} missing required fields'.format(i)); sys.exit(4)
except Exception as e:
    print('ERROR: failed to parse JSON:', e)
    sys.exit(5)
print('Validation OK')
