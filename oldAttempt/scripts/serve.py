#!/usr/bin/env python3
"""
scripts/serve.py

Start a simple local server that regenerates docs.html from docs/ when files change.

Usage:
  python3 scripts/serve.py --port 8000

It will run generate_docs.py once at start and then start a ThreadingHTTPServer to serve
files from the current directory. It polls the docs/ directory (and docs.html template)
for changes and re-runs the generator when files are modified.
"""
import argparse
import os
import subprocess
import sys
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def compute_mtimes(paths):
    mt = {}
    for p in paths:
        if p.is_dir():
            for f in p.rglob('*'):
                if f.is_file():
                    try:
                        mt[str(f)] = f.stat().st_mtime
                    except Exception:
                        mt[str(f)] = 0
        else:
            try:
                mt[str(p)] = p.stat().st_mtime
            except Exception:
                mt[str(p)] = 0
    return mt


def run_generator():
    print('Running generator...')
    res = subprocess.run([sys.executable, 'generate_docs.py', '--input-dir', 'docs', '--template', 'docs.html', '--output', 'docs.html'])
    if res.returncode != 0:
        print('Generator failed with', res.returncode)
    else:
        print('Generator finished')


def serve(port):
    host = ('', port)
    httpd = ThreadingHTTPServer(host, SimpleHTTPRequestHandler)
    print(f'Serving HTTP on port {port} (http://localhost:{port}/)')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down server')
        httpd.shutdown()


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8000)
    args = p.parse_args(argv)

    paths = [Path('docs'), Path('docs.html')]
    run_generator()
    mt0 = compute_mtimes(paths)

    # start server in background
    import threading
    t = threading.Thread(target=serve, args=(args.port,), daemon=True)
    t.start()

    try:
        while True:
            time.sleep(1.0)
            mt1 = compute_mtimes(paths)
            if mt1 != mt0:
                print('Changes detected, regenerating...')
                run_generator()
                mt0 = compute_mtimes(paths)
    except KeyboardInterrupt:
        print('Exiting')


if __name__ == '__main__':
    main()
