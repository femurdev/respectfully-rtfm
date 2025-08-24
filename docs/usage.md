# Usage

There are two main ways to use this project:

1. Streamlit app (interactive)
2. Command-line interface (script)

Streamlit app

- Run: streamlit run main.py
- Use the sidebar to set the project path and crawl options. After crawling, explore files, classes, functions, and inline comments. Export Markdown or JSON using the Export section.

CLI

- Run: python3 -m rtfmlib.cli /path/to/project
- The CLI prints JSON to stdout. Use --no-follow to prevent crawling external dependencies.

Options

- --max-modules (CLI / app): maximum number of modules/files to parse
- --max-file-size: skip files larger than this size
- --no-follow: do not follow the import dependency tree

Output format

- The crawler returns a dict keyed by file paths and markers:
  - file paths: dict with keys __module__, __comments__, class:Name, function:name, etc.
  - __import__:module markers for packages / modules encountered
  - __unresolved__: set of import strings that couldn't be resolved

