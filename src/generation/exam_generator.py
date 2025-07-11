from src.generation.prompt_templates import (
    mcq_prompt,
    short_answer_prompt,
    essay_question_prompt,
    true_false_prompt,
    fill_in_the_blank_prompt
)

from src.models.grok_wrapper import call_grok_api


def generate_exam_from_custom_config(question_config, topic_to_clos):
    """
    Génère un examen basé sur une liste personnalisée de questions.

    :param question_config: Liste de dicts contenant:
        - "type": "QCM", "QCU", "Rédigée", "Vrai/Faux"
        - "difficulty": "easy", "medium", "hard"
        - "clo": le numéro (ex: "2")
        - "clo_desc": description textuelle du CLO
        - "topic": sujet associé (facultatif)
    :param topic_to_clos: dict {topic: [clo1, clo2, ...]} (non utilisé ici mais conservé)
    :return: dict {type: [liste de questions]}
    """

    results = {
        "QCM": [],
        "QCU": [],
        "Rédigée": [],
        "Vrai/Faux": [],
        "Texte à trous": [],
        "Dissertation": []
    }

    for q in question_config:
        qtype = q["type"]
        clo_desc = q.get("clo_desc", "N/A")
        difficulty = q.get("difficulty", "medium")
        topic = q.get("topic", clo_desc)  # fallback = clo_desc s’il n’y a pas de topic
        clos = [clo_desc]

        # Sélection du prompt selon le type
        if qtype == "QCM":
            prompt = mcq_prompt([topic], num_questions=1, difficulty=difficulty, clos=clos)

        elif qtype == "QCU":
            prompt = mcq_prompt([topic], num_questions=1, difficulty=difficulty, clos=clos)

        elif qtype == "Rédigée":
            prompt = short_answer_prompt([topic], num_questions=1, difficulty=difficulty, clos=clos)

        elif qtype == "Vrai/Faux":
            context_str = f"Génère une question vrai/faux sur le sujet '{topic}' en lien avec l'objectif : {clo_desc}."
            prompt = true_false_prompt([context_str], num_questions=1)

        elif qtype == "Texte à trous":
            prompt = fill_in_the_blank_prompt([topic], num_questions=1)

        elif qtype == "Dissertation":
            prompt = essay_question_prompt(topic, difficulty=difficulty)

        else:
            prompt = short_answer_prompt([topic], num_questions=1, difficulty=difficulty, clos=clos)

        try:
            response = call_grok_api(prompt)
            results[qtype].append(response.strip())
        except Exception as e:
            results[qtype].append(f"[Erreur] {str(e)}")

    return results
