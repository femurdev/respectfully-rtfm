# main.py

rtfm main CLI

Enhanced single-file interactive HTML viewer generation.

Features:
- Client-side config for rendering markdown, sanitization, and fuzzy search
- CLI flags: --render-markdown, --sanitize, --fuzzy-search
- Pages include both HTML and (when available) markdown source for client-side rendering

Security: the generated page may insert page.html using innerHTML to support native
HTML content. Only serve or open output you trust. Use --sanitize to attempt DOMPurify
client-side sanitization.