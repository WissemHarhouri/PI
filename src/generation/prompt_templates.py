def mcq_prompt(topics, num_questions=5, difficulty="medium", clos=None):
    clo_text = ""
    if clos:
        clo_text = "\nFocus the questions on the following learning outcomes:\n" + "\n".join([f"- CLO {c}" for c in clos])

    return f"""
You are an AI assistant helping create an exam. Generate {num_questions} distinct multiple-choice questions 
from the following topics: {', '.join(topics)}.
Difficulty Level: {difficulty.capitalize()}.

{clo_text}

Each question should have 4 options (A, B, C, D), with one correct answer clearly marked.
Make sure questions cover different aspects of the topics without repetition.

Example questions:

Question: What is the function of the ReLU activation in neural networks?
A) To introduce non-linearity
B) To reduce overfitting
C) To compute probabilities
D) To normalize inputs
Answer: A)

Question: Which layer is responsible for feature extraction in CNNs?
A) Fully connected layers
B) Convolutional layers
C) Output layers
D) Dropout layers
Answer: B)

Now, generate {num_questions} questions like these:

"""

import re

def parse_mcq_questions(text):
    # Découpe en questions via "Question:"
    raw_questions = re.split(r"\nQuestion:", text)
    questions = []

    for i, q in enumerate(raw_questions):
        q = q.strip()
        if not q:
            continue
        # On remet "Question:" au début (sauf pour le premier si split produit un vide)
        if i > 0:
            q = "Question: " + q
        
        # Extraire question + options + answer, ou prendre la question brute
        questions.append(q.strip())
    return questions


def short_answer_prompt(topics, num_questions=3, difficulty="medium", clos=None):
    """
    Generates a prompt for short-answer questions.
    """
    clo_text = ""
    if clos:
        clo_text = "\nFocus the questions on the following learning outcomes:\n" + "\n".join([f"- CLO {c}" for c in clos])

    return f"""
Generate {num_questions} short-answer questions from the following topics: {', '.join(topics)}.
Difficulty Level: {difficulty.capitalize()}.

{clo_text}

Each question should require a concise written response of 1-2 sentences.
Format each question like this:

Question: [question text]

Keep the questions concept-focused and aligned with standard academic expectations.
"""


def essay_question_prompt(topic, instructions="", difficulty="medium"):
    """
    Generates a prompt for a single essay-style question.
    """
    return f"""
Create one detailed essay question about the topic: "{topic}".
Difficulty Level: {difficulty.capitalize()}

Include instructions for the student, such as:
"{instructions if instructions else 'Discuss the impact and provide examples.'}"

The question should be thought-provoking and suitable for advanced students.
"""


def true_false_prompt(topics, num_questions=5):
    """
    Generates a prompt for True/False questions.
    """
    return f"""
Generate {num_questions} True/False questions based on the topics: {', '.join(topics)}.
Each question should be clear and unambiguous.

Format like this:

Question: [question text]
Answer: [True/False]

Ensure a balanced mix of True and False answers.
"""


def fill_in_the_blank_prompt(topics, num_questions=5):
    """
    Generates a prompt for Fill-in-the-blank questions.
    """
    return f"""
Create {num_questions} fill-in-the-blank questions from the topics: {', '.join(topics)}.

For each:
- Provide a sentence with a missing word or phrase
- Clearly indicate where the blank is
- Give the correct answer

Example format:

Sentence: The capital of France is _______.
Answer: Paris
"""