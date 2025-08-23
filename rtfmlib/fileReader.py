import ast
import os
import tokenize
from io import StringIO


def extract_docstrings_and_comments_from_file(filepath):
    """
    Parse a Python file and extract all documentation (docstrings + inline comments).
    Returns a nested dict, attaching comments to the closest class/function/module.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    # We'll store docs here
    docs = {"__module__": ast.get_docstring(tree), "__comments__": []}

    # Track spans of classes and functions
    node_spans = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            node_spans.append(
                (node.lineno, node.end_lineno, f"function:{node.name}", node)
            )
        elif isinstance(node, ast.ClassDef):
            node_spans.append((node.lineno, node.end_lineno, f"class:{node.name}", node))

    # Extract inline comments
    for tok_type, tok_string, start, _, _ in tokenize.generate_tokens(
        StringIO(source).readline
    ):
        if tok_type == tokenize.COMMENT:
            line_no = start[0]
            comment_text = tok_string.lstrip("# ").rstrip()

            # Try to attach to the closest node by line span
            attached = False
            for start_line, end_line, key, node in node_spans:
                if start_line <= line_no <= end_line:
                    if key not in docs:
                        if isinstance(node, ast.ClassDef):
                            docs[key] = {"__doc__": ast.get_docstring(node), "__comments__": []}
                            # also attach method docstrings
                            for body_item in node.body:
                                if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    docs[key][body_item.name] = {
                                        "__doc__": ast.get_docstring(body_item),
                                        "__comments__": [],
                                    }
                        else:
                            docs[key] = {"__doc__": ast.get_docstring(node), "__comments__": []}

                    docs[key]["__comments__"].append(comment_text)
                    attached = True
                    break

            if not attached:
                docs["__comments__"].append(comment_text)

    return docs


def extract_from_directory(directory):
    """
    Walk a directory and extract docs from all .py files.
    """
    results = {}
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                results[path] = extract_docstrings_and_comments_from_file(path)
    return results


# Example usage
if __name__ == "__main__":
    docs = extract_from_directory("./my_project")
    from pprint import pprint
    pprint(docs)
