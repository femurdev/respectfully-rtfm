import tokenize
from io import StringIO
import ast


def _get_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef):
    """
    Extract arguments, type hints, defaults, and return type
    from a function or async function definition.
    """
    args_info = []

    # helper for defaults alignment
    total_args = node.args.args
    defaults = node.args.defaults or []
    defaults_start = len(total_args) - len(defaults)

    for i, arg in enumerate(total_args):
        default = None
        if i >= defaults_start:
            default = ast.unparse(defaults[i - defaults_start])
        annotation = ast.unparse(arg.annotation) if arg.annotation else None
        args_info.append({
            "name": arg.arg,
            "type": annotation,
            "default": default
        })

    # *args
    if node.args.vararg:
        args_info.append({
            "name": f"*{node.args.vararg.arg}",
            "type": ast.unparse(node.args.vararg.annotation) if node.args.vararg.annotation else None,
            "default": None
        })

    # keyword-only args
    for kwarg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        args_info.append({
            "name": kwarg.arg,
            "type": ast.unparse(kwarg.annotation) if kwarg.annotation else None,
            "default": ast.unparse(default) if default else None
        })

    # **kwargs
    if node.args.kwarg:
        args_info.append({
            "name": f"**{node.args.kwarg.arg}",
            "type": ast.unparse(node.args.kwarg.annotation) if node.args.kwarg.annotation else None,
            "default": None
        })

    return_type = ast.unparse(node.returns) if node.returns else None

    return {"args": args_info, "returns": return_type}


def extract_docstrings_and_comments_from_source(source: str):
    """
    Parse Python source and extract documentation:
    - module, class, and function docstrings
    - inline comments
    - function signatures (args, types, defaults, return type)
    """
    tree = ast.parse(source)
    docs = {
        "__module__": ast.get_docstring(tree),
        "__comments__": [],
    }

    # Track spans of classes and functions for attaching comments
    node_spans = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docs[f"function:{node.name}"] = {
                "__doc__": ast.get_docstring(node),
                "__comments__": [],
                "signature": _get_function_signature(node),
            }
            node_spans.append((node.lineno, node.end_lineno, f"function:{node.name}", node))

        elif isinstance(node, ast.ClassDef):
            docs[f"class:{node.name}"] = {
                "__doc__": ast.get_docstring(node),
                "__comments__": {},
            }
            node_spans.append((node.lineno, node.end_lineno, f"class:{node.name}", node))

            # also extract methods
            for body_item in node.body:
                if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    docs[f"class:{node.name}"][f"method:{body_item.name}"] = {
                        "__doc__": ast.get_docstring(body_item),
                        "__comments__": [],
                        "signature": _get_function_signature(body_item),
                    }

    # Collect inline comments
    for tok_type, tok_string, start, _, _ in tokenize.generate_tokens(StringIO(source).readline):
        if tok_type == tokenize.COMMENT:
            line_no = start[0]
            comment_text = tok_string.lstrip("# ").rstrip()
            attached = False
            for start_line, end_line, key, node in node_spans:
                if start_line <= line_no <= end_line:
                    if key not in docs:
                        docs[key] = {"__doc__": ast.get_docstring(node), "__comments__": []}
                    docs[key]["__comments__"].append(comment_text)
                    attached = True
                    break
            if not attached:
                docs["__comments__"].append(comment_text)

    return docs


def extract_docstrings_and_comments_from_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    return extract_docstrings_and_comments_from_source(source)
