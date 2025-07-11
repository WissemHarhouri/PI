from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'ExamGenius - Examen Officiel', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_cover_page(self, course_title, teacher_name, duration):
        self.add_page()
        self.set_font("Arial", 'B', 18)
        self.cell(0, 10, course_title, 0, 1, 'C')
        self.ln(10)

        self.set_font("Arial", '', 14)
        self.cell(0, 10, f"Enseignant : {teacher_name}", 0, 1, 'C')
        self.cell(0, 10, f"Durée de l'examen : {duration}", 0, 1, 'C')
        self.ln(20)

        self.set_font("Arial", 'I', 12)
        self.multi_cell(0, 10,
            "Instructions :\n- Répondez clairement à chaque question.\n"
            "- Aucun appareil électronique n'est autorisé.\n"
            "- Lisez toutes les questions attentivement avant de répondre.",
            align='L'
        )

    def add_question_section(self, section_title, questions):
        self.add_page()
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, section_title, 0, 1, 'L')
        self.ln(5)

        self.set_font("Arial", '', 12)
        for i, question in enumerate(questions, 1):
            self.multi_cell(0, 10, f"{i}. {question['text']}")
            if question['type'] == 'open':
                for _ in range(3):  # Espace réponse
                    self.cell(0, 10, '_' * 80, 0, 1)
            elif question['type'] in ['qcm', 'qcu']:
                for opt in question.get('options', []):
                    self.cell(0, 10, f"[ ] {opt}", 0, 1)
            self.ln(5)

def create_pdf_from_text(title, teacher, duration, sections):
    pdf = PDF()
    pdf.add_cover_page(course_title=title, teacher_name=teacher, duration=duration)

    for section in sections:
        pdf.add_question_section(section_title=section['title'], questions=section['questions'])

    return bytes(pdf.output(dest='S'))
