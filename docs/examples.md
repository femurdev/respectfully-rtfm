# Examples

Example: parsing a small module

Given the following file, sample.py:

```
"""Module docstring for sample."""

# module-level comment

class Greeter:
    """Greeter class"""

    def greet(self, name: str) -> str:
        # Return a friendly greeting
        return f"Hello, {name}!"


def add(x: int, y: int = 1) -> int:
    """Add two numbers"""
    return x + y
```

Running the crawler on the directory containing sample.py will produce a JSON document where:

- sample.py has __module__ set to the module docstring
- __comments__ contains the module-level comment
- class:Greeter includes its docstring and the method method:greet with its docstring, inline comment, and signature
- function:add has its docstring and signature


Known issues and edge cases

- Complex annotations that depend on runtime imports may not unparse cleanly with ast.unparse.
- Decorated functions retain the underlying FunctionDef and should still parse, but decorator-related metadata is not captured.
- Inline comment attachment is based on the AST node lineno/end_lineno: comments outside ranges fall back to module-level comments.
- Relative import resolution tries to resolve to package names when __init__.py files are present; in namespace-package layouts this may fail.
