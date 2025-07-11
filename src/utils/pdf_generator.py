from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'École Supérieure Privée de Management de Tunis - ESPRIT School of Business', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_cover_page(self, course_info):
        self.add_page()
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, "Examen Final", 0, 1, 'C')
        self.ln(5)

        # School Name
        if 'school_name' in course_info and course_info['school_name']:
            self.set_font("Arial", 'B', 12)
            self.cell(0, 10, course_info['school_name'], 0, 1, 'C')
            self.ln(2)

        # Course Title
        if 'course_title' in course_info and course_info['course_title']:
            self.set_font("Arial", 'B', 16)
            self.cell(0, 10, course_info['course_title'], 0, 1, 'C')

        self.set_font("Arial", '', 12)

        # Program Name
        if 'program_name' in course_info and course_info['program_name'] and course_info['program_name'] != "N/A":
            self.cell(0, 10, f"Programme : {course_info['program_name']}", 0, 1, 'C')

        # Cohort
        if 'cohort' in course_info and course_info['cohort'] and course_info['cohort'] != "N/A":
            self.cell(0, 10, f"Cohorte : {course_info['cohort']}", 0, 1, 'C')

        # Instructor
        if 'instructor' in course_info and course_info['instructor'] and course_info['instructor'] != "N/A":
            self.cell(0, 10, f"Enseignant : {course_info['instructor']}", 0, 1, 'C')

        # Pre-requisite
        if 'pre_req' in course_info and course_info['pre_req']:
            self.ln(2)
            self.set_font("Arial", 'B', 12)
            self.cell(0, 10, "Pré-requis :", 0, 1)
            self.set_font("Arial", '', 12)
            self.multi_cell(0, 8, course_info['pre_req'])

        self.ln(5)
        self.set_font("Arial", '', 12)
        self.multi_cell(0, 8,
            "Instructions :\n"
            "- Répondez clairement à chaque question.\n"
            "- Aucun appareil électronique n'est autorisé.\n"
            "- Lisez attentivement toutes les questions avant de commencer."
        )

    def add_question_section(self, section_title, questions, include_answers=False):
        self.add_page()
        self.set_font("Arial", 'B', 14)
        self.cell(0, 10, section_title, 0, 1)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

        self.set_font("Arial", '', 12)
        for i, q in enumerate(questions, 1):
            self.multi_cell(0, 8, f"{i}. {q['text']}")
            if q['type'] in ['open', 'rédigée']:
                for _ in range(3):
                    self.cell(0, 10, '_' * 80, 0, 1)
            elif q['type'] in ['qcm', 'qcu']:
                for opt in q.get('options', []):
                    self.cell(0, 10, f"[ ] {opt}", 0, 1)
            elif q['type'] in ['vrai/faux', 'truefalse']:
                self.cell(0, 10, "[ ] Vrai     [ ] Faux", 0, 1)
            self.ln(5)

    def add_answers_section(self, all_sections):
        self.add_page()
        self.set_font("Arial", 'B', 16)
        self.cell(0, 10, "Corrigé des questions", 0, 1)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

        self.set_font("Arial", '', 12)
        for section in all_sections:
            self.set_font("Arial", 'B', 13)
            self.cell(0, 10, section['title'], 0, 1)
            self.set_font("Arial", '', 12)
            for i, q in enumerate(section['questions'], 1):
                if q.get('answer'):
                    self.cell(0, 10, f"{i}. Réponse : {q['answer']}", 0, 1)
            self.ln(5)

def create_pdf_from_text(title, teacher, duration, sections, course_metadata=None):
    """
    Génère le PDF d'examen avec page de garde, sections de questions sans réponses, et corrigé.
    """
    pdf = PDF()

    course_info = course_metadata or {
        "course_title": title,
        "instructor": teacher,
        "duration": duration,
    }

    pdf.add_cover_page(course_info)

    for section in sections:
        pdf.add_question_section(section['title'], section['questions'], include_answers=False)

    pdf.add_answers_section(sections)

    return bytes(pdf.output(dest='S'))
