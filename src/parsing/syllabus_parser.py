import pdfplumber
from nltk.tokenize import sent_tokenize
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
                # Tokenize sentences for each page
                sentences = sent_tokenize(text)
                texts.extend(sentences)
        return "\n".join(texts)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = "../../raw_data/uploaded_syllabus.pdf"
    result_text = extract_text_from_pdf(pdf_path)

    # Example extraction logic
    import re

    # Dynamic extraction by label
    def extract_by_label(label, text):
        # Match label followed by colon or whitespace, then capture value until end of line
        match = re.search(rf"{label}\s*[:\-]?\s*(.+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    school_name = extract_by_label("School", result_text)
    if not school_name:
        # Try French label
        school_name = extract_by_label("École", result_text)

    course_title = extract_by_label("Course Title", result_text)
    # If course_title is a placeholder or invalid, fallback
    if not course_title or course_title.lower() in ["no.", "n/a", "none", ""]:
        # Try French label
        course_title = extract_by_label("Intitulé du cours", result_text)
    # If still invalid, fallback to first non-empty line that is not a label
    if not course_title or course_title.lower() in ["no.", "n/a", "none", ""]:
        for line in result_text.splitlines():
            line = line.strip()
            # Skip empty lines, lines that look like labels, and the school name
            if line and not re.match(r"^[A-Za-z\s]+[:\-]", line) and line != school_name:
                course_title = line
                break

    instructor = extract_by_label("Instructor", result_text)
    duration = extract_by_label("Duration", result_text)
    program_name = extract_by_label("Program", result_text)
    cohort = extract_by_label("Cohort \(s\)", result_text)

    # Extract instructor
    instructor = re.search(r"Instructor[:\s]+(.+)", result_text)
    instructor = instructor.group(1).strip() if instructor else ""

    # Extract duration
    duration = re.search(r"Duration[:\s]+(.+)", result_text)
    duration = duration.group(1).strip() if duration else ""

    # Extract program name
    program_name = re.search(r"Program[:\s]+(.+)", result_text)
    program_name = program_name.group(1).strip() if program_name else ""

    # Extract cohort
    cohort = re.search(r"Cohort \(s\)[:\s]+(.+)", result_text)
    cohort = cohort.group(1).strip() if cohort else ""


    # Extract Pre-requisite section
    pre_req = ""
    pre_req_match = re.search(r"Pre[- ]?requisite[s]?\s*[:\-]?\s*(.+)", result_text, re.IGNORECASE)
    if pre_req_match:
        pre_req = pre_req_match.group(1).strip()
    else:
        # Try French label
        pre_req_match = re.search(r"Pré[- ]?requis\s*[:\-]?\s*(.+)", result_text, re.IGNORECASE)
        if pre_req_match:
            pre_req = pre_req_match.group(1).strip()

    # If the pre-req is followed by more lines (not a label or blank), capture them
    if pre_req:
        lines = result_text.splitlines()
        for i, line in enumerate(lines):
            if pre_req in line:
                # Collect subsequent lines until blank or label
                for next_line in lines[i+1:]:
                    next_line = next_line.strip()
                    if not next_line or re.match(r"^[A-Za-z\s]+[:\-]", next_line):
                        break
                    pre_req += "\n" + next_line
                break


    # Build course_metadata dictionary for PDF generator
    course_metadata = {
        "school_name": school_name,
        "course_title": course_title,
        "instructor": instructor,
        "duration": duration,
        "program_name": program_name,
        "cohort": cohort,
        "pre_req": pre_req
    }

    # Print for debug/demo
    for k, v in course_metadata.items():
        print(f"{k}: {v}")