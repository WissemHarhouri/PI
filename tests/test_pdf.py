import os
from fpdf import FPDF

# Chemin absolu ou relatif correct vers la police
current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(current_dir, "..", "fonts", "DejaVuSans.ttf")

pdf = FPDF()
pdf.add_page()
pdf.add_font("DejaVu", "", font_path)
pdf.set_font("DejaVu", size=14)
pdf.cell(0, 10, "Texte avec caractères spéciaux : é, è, à, œ", ln=True)
pdf.output("test.pdf")
print("PDF généré : test.pdf")
