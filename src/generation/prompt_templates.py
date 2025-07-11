def mcq_prompt(topics, num_questions=5, difficulty="medium", clos=None):
    """
    Generate a prompt to create multiple-choice questions based on topics and CLOs.
    """
    topic_str = ", ".join(topics)
    clo_text = ""
    if clos:
        clo_text = "\nThe questions must align with the following learning outcomes:\n" + "\n".join([f"- {c}" for c in clos])

    return f"""
You are an expert educational AI assistant. Your task is to generate {num_questions} professional multiple-choice questions (MCQs)
based on the topic(s): {topic_str}.
Difficulty Level: {difficulty.capitalize()}.

{clo_text}

Guidelines:
- Each question must be clear, specific, and test meaningful understanding.
- Avoid trivial or overly simple questions.
- The questions should reflect academic standards and be directly relevant to the given topics and CLOs.
- Each question must explore a different aspect or nuance of the topic.
- Do NOT repeat the same concept in multiple questions.
- Provide 4 answer options (A, B, C, D) per question.
- Only one option should be correct. Clearly indicate the correct answer.
- Use realistic distractors that test conceptual clarity.

Output Format:
Question: [your question here]
A) Option A
B) Option B
C) Option C
D) Option D
Answer: [Correct Option Letter]

Example:
Question: What is the function of the ReLU activation in neural networks?
A) To introduce non-linearity
B) To reduce overfitting
C) To compute probabilities
D) To normalize inputs
Answer: A)

Now, generate {num_questions} questions following this format:
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
    Generates a prompt for True/False questions, context-aware.
    """
    # Accept clos and difficulty for context
    clos = None
    difficulty = "medium"
    # If called with [context_str], treat as topics
    if isinstance(topics, list) and len(topics) == 1 and topics[0].startswith("Génère une question vrai/faux"):
        context_str = topics[0]
        return f"""
{context_str}
Format like this:
Question: [question text]
Answer: [True/False]
Ensure a balanced mix of True and False answers.
"""
    clo_text = ""
    if clos:
        clo_text = "\nFocus the questions on the following learning outcomes:\n" + "\n".join([f"- CLO {c}" for c in clos])
    return f"""
Generate {num_questions} True/False questions based on the topics: {', '.join(topics)}.
Difficulty Level: {difficulty.capitalize()}.
{clo_text}
Format like this:
Question: [question text]
Answer: [True/False]
Ensure a balanced mix of True and False answers.
"""


def fill_in_the_blank_prompt(topics, num_questions=5):
    """
    Generates a prompt for Fill-in-the-blank questions, context-aware.
    """
    clos = None
    difficulty = "medium"
    clo_text = ""
    if clos:
        clo_text = "\nFocus the questions on the following learning outcomes:\n" + "\n".join([f"- CLO {c}" for c in clos])
    return f"""
Create {num_questions} fill-in-the-blank questions from the topics: {', '.join(topics)}.
Difficulty Level: {difficulty.capitalize()}.
{clo_text}
For each:
- Provide a sentence with a missing word or phrase
- Clearly indicate where the blank is
- Give the correct answer
Example format:
Sentence: The capital of France is _______.
Answer: Paris
"""