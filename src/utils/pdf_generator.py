# src/utils/pdf_generator.py
from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        """Adds a header to each page."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'ExamGenius Generated Exam', 0, 1, 'C')

    def footer(self):
        """Adds a footer to each page."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf_from_text(title, content):
    """
    Generates a PDF document from a title and a block of text content.

    Args:
        title (str): The title of the document.
        content (str): The main text content.

    Returns:
        bytes: The generated PDF content as a byte string.
    """
    pdf = PDF()
    pdf.add_page()
    
    # Document Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=title, ln=True, align='C')
    pdf.ln(10)  # Add a little space after the title

    # Document Content
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=content)
    
    # Return PDF as a byte string
    return bytes(pdf.output(dest='S'))


