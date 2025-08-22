import os

class HTMLExporter:
    def __init__(self, docs, theme='default'):
        self.docs = docs
        self.theme = theme

    def render(self):
        """Render the documentation as an HTML string."""
        html = ["<html>", "<head>", f"<title>Documentation</title>", self._include_theme(), "</head>", "<body>"]
        html.append("<h1>Documentation</h1>")

        for doc in self.docs:
            html.append(self._render_file(doc))

        html.extend(["</body>", "</html>"])
        return "\n".join(html)

    def _include_theme(self):
        """Include the CSS theme."""
        if self.theme == 'default':
            return "<style>body { font-family: Arial, sans-serif; }</style>"
        # Add other themes as needed
        return ""

    def _render_file(self, doc):
        """Render a single file's documentation."""
        sections = [f"<h2>{doc['file']}</h2>"]

        if doc['modules']:
            sections.append("<h3>Modules</h3>")
            sections.append("<ul>")
            for module in doc['modules']:
                sections.append(f"<li>{module}</li>")
            sections.append("</ul>")

        if doc['classes']:
            sections.append("<h3>Classes</h3>")
            for cls in doc['classes']:
                sections.append(f"<h4>{cls['name']}</h4>")
                sections.append(f"<p>{cls['docstring']}</p>")
                if cls['methods']:
                    sections.append("<h5>Methods</h5>")
                    sections.append("<ul>")
                    for method in cls['methods']:
                        sections.append(f"<li>{method['name']} - {method['docstring']}</li>")
                    sections.append("</ul>")

        if doc['functions']:
            sections.append("<h3>Functions</h3>")
            sections.append("<ul>")
            for func in doc['functions']:
                sections.append(f"<li>{func['name']} - {func['docstring']}</li>")
            sections.append("</ul>")

        return "\n".join(sections)

    def save(self, output_dir):
        """Save the rendered HTML to a file."""
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "documentation.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.render())

class HTMLExporter:
    def __init__(self, docs, theme='default'):
        self.docs = docs
        self.theme = theme

    def render(self):
        """Render the documentation as an HTML string."""
        html = ["<html>", "<head>", f"<title>Documentation</title>", self._include_theme(), "</head>", "<body>"]
        html.append(self._generate_table_of_contents())
        html.append("<h1>Documentation</h1>")

        for doc in self.docs:
            html.append(self._render_file(doc))

        html.extend(["</body>", "</html>"])
        return "\n".join(html)

    def _include_theme(self):
        """Include the CSS theme."""
        if self.theme == 'default':
            return "<style>body { font-family: Arial, sans-serif; } .toc { position: fixed; left: 10px; top: 10px; background: #f9f9f9; border: 1px solid #ccc; padding: 10px; } .collapsible { cursor: pointer; }</style>"
        # Add other themes as needed
        return ""

    def _generate_table_of_contents(self):
        """Generate a table of contents for the documentation."""
        toc = ["<div class=\"toc\"><h3>Table of Contents</h3><ul>"]
        for i, doc in enumerate(self.docs):
            toc.append(f"<li><a href=\"#doc-{i}\">{doc['file']}</a></li>")
        toc.append("</ul></div>")
        return "\n".join(toc)

    def _render_file(self, doc):
        """Render a single file's documentation."""
        sections = [f"<h2 id=\"doc-{self.docs.index(doc)}\">{doc['file']}</h2>"]

        if doc['modules']:
            sections.append("<h3>Modules</h3>")
            sections.append("<ul>")
            for module in doc['modules']:
                sections.append(f"<li>{module}</li>")
            sections.append("</ul>")

        if doc['classes']:
            sections.append("<h3>Classes</h3>")
            for cls in doc['classes']:
                sections.append(f"<h4>{cls['name']}</h4>")
                sections.append(f"<p>{cls['docstring'] or 'No documentation provided.'}</p>")
                if cls['methods']:
                    sections.append("<h5>Methods</h5>")
                    sections.append("<ul>")
                    for method in cls['methods']:
                        sections.append(f"<li>{method['name']} - {method['docstring'] or 'No documentation provided.'}</li>")
                    sections.append("</ul>")

        if doc['functions']:
            sections.append("<h3>Functions</h3>")
            sections.append("<ul>")
            for func in doc['functions']:
                sections.append(f"<li>{func['name']} - {func['docstring'] or 'No documentation provided.'}</li>")
            sections.append("</ul>")

        return "\n".join(sections)

    def save(self, output_dir):
        """Save the rendered HTML to a file."""
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "documentation.html")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self.render())