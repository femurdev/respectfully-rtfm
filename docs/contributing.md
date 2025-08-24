# Contributing

Thanks for your interest in contributing! Tips:

- Run tests (if present) and linting locally.
- Keep changes small and focused.
- Add unit tests for parsing edge cases (complex signatures, decorators, unusual imports).
- When modifying AST logic, include sample source files in tests/docs to ensure inline comment attachment and signatures remain correct.

Local development

- Install the package in editable mode:

  python3 -m pip install -e .

- Run the Streamlit dev app:

  streamlit run main.py

Reporting problems

- Open an issue with a small reproducible example (source file) and the expected documentation output.

