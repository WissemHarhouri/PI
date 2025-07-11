from src.generation.prompt_templates import mcq_prompt, short_answer_prompt
from src.models.grok_wrapper import call_grok_api

def generate_exam_from_custom_config(question_config, topic_to_clos):
    """
    Génère un examen basé sur une liste personnalisée de questions.

    :param question_config: Liste de dicts contenant:
        - "type": "QCM", "QCU", "Rédigée", "Vrai/Faux"
        - "difficulty": "easy", "medium", "hard"
        - "topic": le sujet
    :param topic_to_clos: dict {topic: [clo1, clo2, ...]}
    :return: dict {type: [liste de questions]}
    """

    results = {
        "QCM": [],
        "QCU": [],
        "Rédigée": [],
        "Vrai/Faux": []
    }

    for q in question_config:
        qtype = q["type"]
        clo = q.get("clo")   # <- récupérer la clé "clo" au lieu de "topic"
        difficulty = q["difficulty"]
        
        # Note : si tu veux garder la compatibilité avec "topic", tu peux faire :
        # topic = q.get("topic", None)
        # clos = topic_to_clos.get(topic, ["?"]) if topic else [clo]
        
        clos = [clo] if clo else ["?"]  # clos est une liste
        
        if qtype in ["QCM", "QCU"]:
            prompt = mcq_prompt([clo], num_questions=1, difficulty=difficulty, clos=clos)
        else:
            prompt = short_answer_prompt([clo], num_questions=1, difficulty=difficulty, clos=clos)
        
        try:
            response = call_grok_api(prompt)
            results[qtype].append(response.strip())
        except Exception as e:
            results[qtype].append(f"[Erreur] {str(e)}")

    return results


