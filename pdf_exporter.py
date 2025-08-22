from fpdf import FPDF
import os

class PDFExporter:
    def __init__(self, docs):
        self.docs = docs
        self.pdf = FPDF()

    def render(self):
        """Generate PDF content from documentation."""
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=12)

        self.pdf.set_font("Arial", style="B", size=16)
        self.pdf.cell(200, 10, txt="Documentation", ln=True, align="C")

        for doc in self.docs:
            self._render_file(doc)

    def _render_file(self, doc):
        """Render a single file's documentation in the PDF."""
        self.pdf.set_font("Arial", style="B", size=14)
        self.pdf.cell(200, 10, txt=f"File: {doc['file']}", ln=True, align="L")

        if doc['modules']:
            self.pdf.set_font("Arial", style="B", size=12)
            self.pdf.cell(200, 10, txt="Modules:", ln=True)
            for module in doc['modules']:
                self.pdf.set_font("Arial", size=12)
                self.pdf.cell(200, 10, txt=f"- {module}", ln=True)

        if doc['classes']:
            self.pdf.set_font("Arial", style="B", size=12)
            self.pdf.cell(200, 10, txt="Classes:", ln=True)
            for cls in doc['classes']:
                self.pdf.set_font("Arial", style="B", size=12)
                self.pdf.cell(200, 10, txt=f"Class: {cls['name']}", ln=True)
                self.pdf.set_font("Arial", size=12)
                self.pdf.multi_cell(0, 10, txt=f"Description: {cls['docstring']}")
                if cls['methods']:
                    self.pdf.cell(200, 10, txt="Methods:", ln=True)
                    for method in cls['methods']:
                        self.pdf.cell(200, 10, txt=f"- {method['name']}: {method['docstring']}", ln=True)

        if doc['functions']:
            self.pdf.set_font("Arial", style="B", size=12)
            self.pdf.cell(200, 10, txt="Functions:", ln=True)
            for func in doc['functions']:
                self.pdf.cell(200, 10, txt=f"- {func['name']}: {func['docstring']}", ln=True)

    def save(self, output_dir):
        """Save the PDF to the specified directory."""
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "documentation.pdf")
        self.pdf.output(output_file)