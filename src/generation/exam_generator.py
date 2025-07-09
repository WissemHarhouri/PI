# src/generation/exam_generator.py
from src.generation.prompt_templates import mcq_prompt, short_answer_prompt
from src.models.grok_wrapper import call_grok_api


def generate_exam_from_topics(topics, num_mcqs=5, num_short_answers=3, difficulty="medium"):
    """
    Generate MCQs and short-answer questions from a list of topics.
    """
    mcqs_prompt = mcq_prompt(topics, num_questions=num_mcqs, difficulty=difficulty)
    short_answers_prompt = short_answer_prompt(topics, num_questions=num_short_answers, difficulty=difficulty)

    mcqs = call_grok_api(mcqs_prompt)
    short_answers = call_grok_api(short_answers_prompt)

    return {
        "mcqs": mcqs,
        "short_answers": short_answers
    }