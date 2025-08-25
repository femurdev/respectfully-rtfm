# Usage

SITE

The primary and supported use case of this app is the r2tfm command. To use this, simply go to the directory you want to use it in and run:

```bash
r2tfm
```

Visit [this url](http://localhost:8501) or [this url](http://192.168.1.185:8501)

CLI

After an editable install (see docs/install.md), run the CLI to crawl a project and print JSON output:

```bash
r2tfm /path/to/project
```

Or invoke the module directly (useful if console scripts are not available):

```bash
python3 -m r2tfm.rtfmlib.cli /path/to/project
```

Options

- --max-modules N: Limit how many modules will be crawled (default: 5000)
- --max-file-size BYTES: Skip files larger than this (default: 2_000_000)
- --no-follow: Do not follow imports into installed dependencies

Example

```bash
r2tfm ./my_project --max-modules 200
```

Streamlit web UI

Install Streamlit if you haven't already:

```bash
python3 -m pip install streamlit
```

Run the web app (interactive browser UI):

```bash
streamlit run r2tfm/main.py
```

Exports

- From the Streamlit UI you can download the entire documentation as Markdown or JSON.
- The CLI prints a JSON representation to stdout which you can redirect to a file.

Output format

The crawler produces a dictionary keyed by file path or import markers. Typical nodes include:

- __module__: module docstring
- __comments__: list of inline/floating comments attached to the module or symbol
- class:ClassName: a dict with __doc__, __comments__, and method:MethodName entries
- function:func_name: a dict with __doc__, __comments__, and signature (args/returns)
- __import__:package_name: a reference to an external package with __package__ pointing to its installed path

Limitations

- AST-based signature extraction uses ast.unparse and requires Python 3.9+ for reliable parsing of annotations.
- Comments are associated to AST nodes if they lie within the node's line span; this heuristic may be imperfect.

Troubleshooting

- If r2tfm is not found after installation, ensure you used python3 -m pip install -e . and that your PATH includes the environment's bin/ where console scripts are installed.
- If imports are not resolved correctly, try exporting PYTHONPATH to include the project source (see docs/install.md).
