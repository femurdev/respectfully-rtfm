# Contributing

Thanks for considering contributing! This project is small and easy to extend. Here are some ways you can help:

1) Bug reports & issues
- Open an issue describing the problem, the Python version you used, and steps to reproduce.

2) Documentation improvements
- The `docs/` folder contains usage, API notes, and troubleshooting tips. Improvements are welcome.

3) Features
- Ideas:
  - Markdown rendering for README and docstrings
  - Syntax highlighting (server-side with `pygments` or client-side with highlight.js)
  - Live reload / watcher to automatically rebuild docs on file changes
  - Better search (fuzzy matching or full-text index)

4) Tests
- This project currently has no automated tests. If you add features, consider adding tests that validate
  the parser behavior (parse_file) on representative source files.

5) Style
- Use modern Python (3.8+). Keep external dependencies optional. The goal is a small and easy-to-run tool.

6) Submitting changes
- Fork the repository, create a branch, commit your change, and open a pull request. Describe your changes
  and rationale in the PR description.

License
- Please include or confirm the project license in your PR. If a license is not present, contact the
  project maintainer to agree on one before contributing substantial changes.
