# Developer Guide for Python Documentation Generator

This guide provides an overview of the internal components of the Python Documentation Generator and explains how to extend and debug the tool.

## Core Components

### 1. `docgen.py`
The main script that serves as the entry point for the CLI interface.
- Handles command-line arguments using the `argparse` library.
- Routes the parsing tasks based on the provided arguments (e.g., `--path`, `--format`).
- Outputs the generated documentation in the specified format (e.g., JSON, Markdown).

### 2. AST Parsing
Uses Python's `ast` module to parse the codebase without executing it:
- **Node Types**:
  - `ClassDef` for classes.
  - `FunctionDef` for functions and methods.
  - `Assign` for module-level constants.
- **Key Functions**:
  - Traverses the AST tree using `ast.walk` or `ast.iter_child_nodes`.
  - Extracts information such as fully qualified names, signatures, docstrings, and constants.

### 3. Docstring Parsing
Parses docstrings using custom logic for different styles:
- **Supported Styles**:
  - Google-style.
  - NumPy-style.
  - reStructuredText (reST).
- **Auto Detection**:
  - Heuristics to detect the docstring style when `--style auto` is used.
  - Fallback for unparsable or missing docstrings.

### 4. Output Formats
Supports multiple output formats:
- **JSON**:
  - Structured representation of modules, classes, functions, and constants.
- **Markdown (MD)**:
  - Readable documentation for developers.
- **Other Formats**:
  - Extendable to support additional formats like HTML or PDF.

## Extending the Tool

### Adding a New Output Format
1. Create a new function in `docgen.py` to handle the format.
   ```python
   def generate_html(docs):
       # Convert the docs dictionary to HTML format
       return html_output
   ```
2. Update the `--format` argument in the CLI to include the new format.
   ```python
   parser.add_argument('--format', choices=['json', 'md', 'html'], default='json')
   ```

### Supporting Additional Docstring Styles
1. Add a new parser function for the style in the `docstring_parsers.py` file.
   ```python
   def parse_custom_style(docstring):
       # Logic to parse the custom style
       return parsed_docstring
   ```
2. Update the auto-detection logic to include the new style.

### Adding CLI Features
1. Modify the `argparse` configuration in `docgen.py` to include the new flag.
   ```python
   parser.add_argument('--debug', action='store_true', help='Enable detailed debugging output')
   ```
2. Implement the logic for the new feature in the relevant section of the code.

### Improving Performance
- Use `ast.iter_child_nodes` instead of `ast.walk` for better memory efficiency.
- Implement incremental file processing to handle large codebases.

## Debugging Tips

### 1. Enable Debug Logging
Use the `--debug` flag to enable detailed logging during execution:
- Logs encountered AST nodes and their attributes.
- Tracks updates to the `docs` object.
- Reports skipped files and nodes with reasons.

### 2. Validate AST Traversal
- Create minimal test cases with single-node files (e.g., one class, one function).
- Log each traversed node type and its attributes.

### 3. Check the `docs` Object
- Print the state of the `docs` object after processing each node to ensure data is being appended correctly.

### 4. Test Edge Cases
- Nested classes and functions.
- Decorated functions and methods.
- Files with syntax errors or dynamic imports.

## Testing Guidelines
- Use the `unittest` framework to write test cases in the `tests/` directory.
- Add test cases for edge scenarios such as:
  - Complex type annotations.
  - Mixed docstring styles.
  - Large codebases (~2k files).
- Run all tests before submitting changes:
  ```bash
  python3 -m unittest discover tests
  ```

---

Thank you for contributing to the Python Documentation Generator! Your efforts help improve this tool for the Python community.

Happy coding!