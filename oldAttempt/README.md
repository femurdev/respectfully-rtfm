RTFM — Documentation Viewer (single-file)

Overview

This repository includes docs.html — a single-file interactive documentation viewer that embeds a dataset of pages and renders them natively in the browser.

Key features
- Single HTML file that renders a list of pages and shows content in the main pane.
- Pages dataset stored as a JSON script tag (id="rtfm-data") to avoid brittle JS string escaping.
- Runtime toggles for: render Markdown (via marked), sanitize HTML (via DOMPurify), and fuzzy search.
- Client-side navigation, search (including fuzzy matching), highlights, copy link/html, theme toggle, and keyboard shortcuts.

How docs.html is structured
- The pages are stored in the <script id="rtfm-data" type="application/json"> tag as an array of objects: {id, title, tags, html, md}.
  - html: native HTML content to insert with innerHTML (be careful with untrusted content).
  - md: optional markdown source to be rendered when "MD" is toggled on (uses marked if available).
- The viewer reads the JSON: const pages = JSON.parse(document.getElementById('rtfm-data').textContent);
- The __RTFM_CONFIG object controls runtime behavior: renderMarkdown, sanitize, fuzzySearch. These preferences are persisted to localStorage.

Security note
- Inserting HTML with innerHTML is dangerous with untrusted content. Use the "🛡️" (Sanitize) toggle to enable DOMPurify-based sanitization before inserting. If you expect untrusted input, enable sanitize by default or host docs.html behind a trusted build step that sanitizes each page.

How to run locally
1. Start a simple static server from the project root (uses python3):
   python3 -m http.server 8000
2. Open http://localhost:8000/docs.html in your browser.

Editing / regenerating pages
- Quick edit: open docs.html and modify the JSON inside the <script id="rtfm-data">...</script> tag (be careful to maintain correct JSON escaping). Each page object should include a unique id.
- Programmatic generation: you can write a small Python script to produce the JSON array and inject it into the HTML template. If you want, I can add a generator script (generate_docs.py) that takes a docs.json and emits docs.html.

Development suggestions / next steps
- Add a Python script to generate docs.html automatically from a docs/ directory of Markdown/HTML files.
- Enable sanitize by default if pages may be untrusted.
- Add an automated test or HTML validation step (CI) that ensures docs.html remains valid and accessible.
- Consider paging or lazy-loading for very large datasets.

API for external scripts
- window.docsApp.addPage(page) — add a page object (same shape as the JSON) at runtime.
- window.docsApp.open(id) — open a page by id.

If you want me to:
- Add generate_docs.py to auto-create docs.html from a docs.json or directory.
- Change defaults (e.g., enable sanitize by default).
- Add README-style documentation inside docs.html or other project docs.

Tell me which of those you'd like next and I will add it.