# src/generation/prompt_templates.py

def mcq_prompt(topics, num_questions=5, difficulty="medium"):
    """
    Generates a prompt for multiple-choice questions.
    """
    return f"""
You are an AI assistant helping create an exam. Generate {num_questions} multiple-choice questions 
from the following topics: {', '.join(topics)}.

Difficulty Level: {difficulty.capitalize()}

Each question should have 4 options (A, B, C, D), with one correct answer clearly marked.
Format your output exactly as shown below:

Question: [question text]
A) [option A]
B) [option B]
C) [option C]
D) [option D]
Answer: [Correct option letter]

Make sure the questions are relevant and varied across the listed topics.
"""


def short_answer_prompt(topics, num_questions=3, difficulty="medium"):
    """
    Generates a prompt for short-answer questions.
    """
    return f"""
Generate {num_questions} short-answer questions from the following topics: {', '.join(topics)}.
Difficulty Level: {difficulty.capitalize()}

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