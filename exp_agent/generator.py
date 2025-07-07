import os
from typing import List, Dict, Optional
from litellm import completion, BadRequestError


# --- Prompt Construction (from your generator.py, slightly adapted) ---
def build_augmented_prompt(query: str, chunks: List[Dict]) -> str:
    if not chunks:

        prompt = f"""### QUESTION UTILISATEUR :
{query}

### INSTRUCTION :
Réponds de manière claire et factuelle à la question en utilisant tes connaissances générales.

Réponse :
"""
        return prompt

    context_parts = []
    for chunk in chunks:
        source_info = chunk.get('doc_name', chunk.get('source', 'Source inconnue')) # Prefer doc_name if available
        context_parts.append(f"[Source: {source_info}] {chunk['text']}")

    context = "\n\n---\n\n".join(context_parts) # Aligning with Streamlit app separator

    prompt = f"""### CONTEXTE DOCUMENTAIRE :
{context}

### QUESTION UTILISATEUR :
{query}

### INSTRUCTION :
Réponds de manière claire et factuelle à la question, en t’appuyant UNIQUEMENT sur les informations du contexte fourni. Si la réponse n’est pas présente dans le contexte, indique que tu ne peux pas répondre sur la base des informations fournies. Cite la source du document si possible à partir du contexte.

Réponse :
"""
    return prompt

def build_exam_generation_prompt(course_text: str, num_questions: int = 5, question_type: str = "mixte", difficulty: str = "moyen") -> str:
    """
    Génère un prompt structuré pour demander à un LLM de créer un examen à partir d'un cours.
    """
    return f"""
Vous êtes un générateur d'examens expert. À partir du texte de cours fourni ci-dessous, générez un examen structuré.

---
TEXTE DU COURS :
{course_text}
---

CONSIGNE :
- Générez un examen de {num_questions} questions.
- Type de questions : {question_type} (QCM, questions ouvertes, vrai/faux, etc.)
- Difficulté : {difficulty}
- Pour chaque question, fournissez la réponse attendue.
- Numérotez les questions et séparez clairement chaque question/réponse.
- N'inventez rien qui ne soit pas dans le cours.

Format attendu :
1. Question ...
   Réponse attendue : ...
2. ...

Commencez l'examen ci-dessous :
"""

def build_exam_generation_prompt_with_syllabus(syllabus_text: str, course_text: str, question_types: dict = None, difficulty: str = "moyen") -> str:
    """
    Génère un prompt structuré pour demander à un LLM de créer un examen à partir d'un syllabus (cadre à respecter) et d'un contenu de cours (source principale des questions), avec répartition par type.
    """
    # Construction de la consigne sur la répartition
    repartition = ""
    if question_types:
        repartition = "- Répartition des questions : " + ", ".join([f"{v} {k}" for k, v in question_types.items()]) + "."
    total_questions = sum(question_types.values()) if question_types else 5
    return f"""
Vous êtes un générateur d'examens expert. Générez un examen à partir du contenu du cours ci-dessous, en respectant strictement le cadre, les thèmes et les compétences du syllabus fourni. N'incluez aucune question qui ne soit pas couverte à la fois par le syllabus ET le cours.

---
SYLLABUS (cadre à respecter) :
{syllabus_text}
---

CONTENU DU COURS (source principale des questions) :
{course_text}
---

CONSIGNE :
- Générez exactement {total_questions} questions, pas moins, pas plus.
{repartition}
- Difficulté : {difficulty}
- Pour chaque question, fournissez la réponse attendue.
- Numérotez les questions et séparez clairement chaque question/réponse.
- N'inventez rien qui ne soit pas dans le cours.
- N'incluez que des questions qui respectent le cadre/thèmes/compétences du syllabus.
- N'arrêtez la génération qu'après avoir produit toutes les questions et réponses demandées.

Format attendu :
1. Question ...\n   Réponse attendue : ...\n2. ...

Commencez l'examen ci-dessous :
"""

# --- LLM Call (adapted from Streamlit app's real_llm_generation_with_openai) ---
def generate_llm_response(
    prompt: str,
    openai_api_key: str = None,
    llm_model: str = None,
    temperature: float = None,
) -> str:
    # Use environment variables if not provided
    if llm_model is None:
        llm_model = os.getenv("MODEL")
    if temperature is None:
        try:
            temperature = float(os.getenv("DEFAULT_TEMPERATURE", 0.2))
        except Exception:
            temperature = 0.2
    if openai_api_key is None:
        openai_api_key = os.getenv("API_KEY")
    if not openai_api_key:
        print("Generator: API Key not provided.")
        return "Erreur: Clé API non configurée."

    try:
        # Groq/LiteLLM: Only a single user message is allowed
        messages = [
            {"role": "user", "content": prompt}
        ]
        response = completion(
            model=llm_model,
            messages=messages,
            api_base="https://api.groq.com/openai/v1",
            api_key=openai_api_key,
            temperature=temperature,
        )
        llm_response_content = response["choices"][0]["message"]["content"].strip()
        return llm_response_content
    except BadRequestError as e:
        print(f"Generator: LLM BadRequestError: {e}")
        return f"Erreur LLM: {e}"
    except Exception as e:
        print(f"Generator: An unexpected error occurred: {str(e)}")
        return f"Erreur inattendue: {str(e)}"

def generate_exam_from_course(
    course_text: str,
    num_questions: int = 5,
    question_type: str = "mixte",
    difficulty: str = "moyen",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.2
) -> str:
    """
    Utilise un LLM pour générer un examen à partir d'un texte de cours et des paramètres donnés.
    """
    if api_key is None:
        api_key = os.getenv("API_KEY")
    if model is None:
        model = os.getenv("MODEL")
    prompt = build_exam_generation_prompt(course_text, num_questions, question_type, difficulty)
    try:
        # Groq/LiteLLM: Only a single user message is allowed
        messages = [
            {"role": "user", "content": prompt}
        ]
        response = completion(
            model=model,
            messages=messages,
            api_base="https://api.groq.com/openai/v1",
            api_key=api_key,
            temperature=temperature,
        )
        return response["choices"][0]["message"]["content"].strip()
    except BadRequestError as e:
        return f"Erreur LLM: {e}"
    except Exception as e:
        return f"Erreur inattendue: {str(e)}"