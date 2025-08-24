r2tfm — Python codebase documentation crawler and exporter

Overview

r2tfm is a small tool for crawling Python projects (source files and, optionally, the dependency tree), extracting docstrings, inline comments, and function/method signatures, and producing browsable documentation. It includes a Streamlit-based viewer for interactive exploration and a CLI for generating JSON output.

This repository is organized as a lightweight refactor of earlier pydoccrawler-style code.

Key features

- Crawl a project directory and optionally follow the import dependency tree
- Extract module, class, function, and method docstrings
- Attach inline comments to surrounding code elements when possible
- Extract function signatures (arguments, types, defaults, return type)
- Export entire documentation as Markdown or JSON
- Simple Streamlit app for interactive browsing (r2tfm/main.py)
- CLI entrypoint (r2tfm/rtfmlib/cli.py)

Quick install (editable install)

1. Download or clone this repository to a directory on your machine.

2. From within the project directory, run:

   python3 -m pip install -e .

This installs the package in editable mode so you can modify the source and use the installed CLI.

Locating and exporting the Python path (zsh)

If you want to run the CLI entrypoint `r2tfm` (installed via the package) and your shell needs the package path on PYTHONPATH, do the following in zsh:

1. Locate the path to this project’s package directory. For an editable install the package source is the project directory; find the absolute path. Example:

   python3 -c "import os, r2tfm; print(os.path.dirname(r2tfm.__file__))"

2. Export that path to PYTHONPATH in zsh (replace /path/to/project with the directory printed above):

   export PYTHONPATH="/path/to/project:$PYTHONPATH"

Running the CLI (zsh)

Once installed and PYTHONPATH set, run the CLI by invoking the console script (entry point) `r2tfm` in zsh:

   r2tfm /path/to/target_project

Alternatively, run the module directly with python3:

   python3 -m r2tfm.rtfmlib.cli /path/to/target_project

Using the Streamlit web viewer

To run the Streamlit web UI for interactive browsing and exporting Markdown/JSON:

   python3 -m pip install streamlit
   streamlit run r2tfm/main.py

Documentation and usage examples

See the docs/ directory for detailed installation instructions, usage examples, CLI options, and notes on output format and limitations.

Contributing

Contributions welcome. For local development, use the editable install above. Please open issues or PRs.
