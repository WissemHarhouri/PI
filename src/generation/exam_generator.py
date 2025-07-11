from src.generation.prompt_templates import mcq_prompt, short_answer_prompt
from src.models.grok_wrapper import call_grok_api
from src.generation.prompt_templates import parse_mcq_questions

def generate_exam_from_custom_config(question_config, topic_to_clos):
    results = {
        "QCM": [],
        "QCU": [],
        "Rédigée": [],
        "Vrai/Faux": []
    }

    # Regroupe par type
    from collections import defaultdict
    grouped = defaultdict(list)
    for q in question_config:
        grouped[q["type"]].append(q)

    for qtype, qlist in grouped.items():
        topics = list({q.get("clo", "?") for q in qlist})

        num_questions = len(qlist)
        difficulty = qlist[0]["difficulty"] if qlist else "medium"

        if qtype in ["QCM", "QCU"]:
            prompt = mcq_prompt(topics, num_questions=num_questions, difficulty=difficulty, clos=topics)
        else:
            # Pour les questions ouvertes / vrai-faux, tu peux créer un prompt similaire adapté
            prompt = short_answer_prompt(topics, num_questions=num_questions, difficulty=difficulty, clos=topics)

        try:
            response = call_grok_api(prompt)
            # Parser les questions
            parsed = parse_mcq_questions(response) if qtype in ["QCM", "QCU"] else [response]  # Ajuster pour autres types
            results[qtype].extend(parsed)
        except Exception as e:
            results[qtype].append(f"[Erreur] {str(e)}")

    return results
