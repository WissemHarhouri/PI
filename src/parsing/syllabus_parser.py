import pdfplumber
import nltk

nltk.download('punkt')

def extract_text_from_pdf(pdf_path):
    """
    Ouvre un fichier PDF et extrait tout le texte page par page.
    """
    with pdfplumber.open(pdf_path) as pdf:
        texts = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
        return "\n".join(texts)


