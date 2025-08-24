FAQ — Edge cases, limitations, and gotchas

This project aims to extract docstrings, inline comments, and function signatures from Python source, but there are several edge cases and limitations to be aware of.

Parsing and AST limitations

- Dynamic code (exec/eval/importlib): Any code executed dynamically at runtime (exec, eval, importlib.machinery, plugins loaded via entry points) will not be visible to an AST-based static crawler.
- C extensions and compiled modules: Extension modules (.so/.pyd) and built-in modules cannot be parsed; the crawler records import markers for them but cannot extract docstrings or comments.
- Generated code: Files produced by code generators or templating systems may contain unusual patterns or encodings and can confuse the parser.
- Complex annotations: Signature extraction relies on ast.unparse (Python 3.9+). Extremely complex or newer-syntax annotations may fail to unparse or may produce less-readable strings.
- Decorators that change signatures: If a decorator rewrites a function's signature (e.g., via functools.wraps or custom wrappers), the AST-reported signature will be the source signature — runtime signatures may differ.

Comment association heuristics

- Loose/remote comments: Comments that are intended to document a symbol but are separated by blank lines or are placed far from a node's lineno..end_lineno span might not be attached to the intended node and will instead become module-level floating comments.
- Trailing inline comments: Comments at the end of a code line (trailing comments) are captured as comments but may not be associated with the surrounding symbol if they fall outside a node's span.
- Nested scopes: Comments inside nested functions or comprehensions may be attributed to the nearest containing AST node; attribution is heuristic and can be imperfect.

File handling and encodings

- Non-UTF-8 files: The parser opens files as UTF-8. Files encoded differently may raise errors — ensure source files are UTF-8 or pre-convert them.
- Very large files: Files larger than the configured max file size are skipped to prevent excessive memory use; reduce the file size limit with --max-file-size if needed but be cautious.

Import resolution and environment

- Namespace packages and non-standard layouts: Resolving imports to actual files uses heuristics and sys.path lookups; unusual project layouts or namespace packages may not resolve correctly.
- Virtual environments: If you crawl a project from outside its virtualenv, imported dependencies may point to a different Python environment. Consider activating the target project's venv or exporting PYTHONPATH to include project sources.
- Circular imports: The crawler avoids infinite recursion by tracking visited modules, but large or complex circular dependency graphs may still slow the crawl.

Signatures and defaults

- Defaults that are expressions: Default values are unparsed into source text with ast.unparse; in some cases these will reference names or expressions that only make sense at runtime and cannot be evaluated.
- Keyword-only args and varargs: These are extracted, but presentation may differ from runtime introspection (inspect.signature) in nuanced cases.

Other cases

- Windows vs POSIX paths: File path keys are stored using the file paths seen when crawling — path normalization differences may affect reproducibility across OSes.
- Duplicate symbol names: Multiple functions/classes with the same name in different files will be recorded separately keyed by file path. Within the same file, nested or redefined names may overwrite keys or collide depending on how nodes are enumerated.

Mitigations and recommendations

- For runtime-accurate signatures, consider combining static extraction with runtime introspection (import modules and use inspect.signature) when safe and appropriate.
- Activate the target project's virtual environment before crawling to ensure imports resolve consistently to the intended installed packages.
- Pre-convert files to UTF-8 and keep file sizes reasonable, or increase the --max-file-size with caution.
- Use the Streamlit UI to inspect and verify attachments (docstrings/comments) interactively when heuristics are uncertain.

If you encounter specific files or patterns that produce incorrect output, please open an issue with a minimal reproduction so we can improve the heuristics and parsing logic.