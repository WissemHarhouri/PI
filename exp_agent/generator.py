import os
from openai import OpenAI, APIError, AuthenticationError, RateLimitError
from typing import List, Dict

# --- Constants ---
DEFAULT_LLM_MODEL = "gpt-4o" # As per your Streamlit app / Document
DEFAULT_TEMPERATURE = 0.2

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

# --- LLM Call (adapted from Streamlit app's real_llm_generation_with_openai) ---
def generate_llm_response(
    prompt: str,
    openai_api_key: str,
    llm_model: str = DEFAULT_LLM_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,

) -> str:
    if not openai_api_key:
        print("Generator: OpenAI API Key not provided.")
        return "Erreur: Clé API OpenAI non configurée."


    try:
        client = OpenAI(api_key=openai_api_key)
        # Your generator.py system message is good.
        messages = [
            {"role": "system", "content": "Tu es un assistant expert, précis et neutre, qui répond en se basant uniquement sur le contexte fourni."},
            {"role": "user", "content": prompt}
        ]
        
        response = client.chat.completions.create(
            model=llm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=350 # from Streamlit app
        )
        llm_response_content = response.choices[0].message.content.strip()

        return llm_response_content
    except AuthenticationError:
        print("Generator: OpenAI API Key is invalid or not authorized.")
        return "Erreur d'authentification OpenAI: Vérifiez votre clé API."
    except RateLimitError:
        print("Generator: OpenAI API rate limit exceeded.")
        return "Erreur OpenAI: Limite de taux d'appels API atteinte."
    except APIError as e:
        print(f"Generator: OpenAI API error occurred: {e}")
        return f"Erreur API OpenAI: {e}"
    except Exception as e:
        print(f"Generator: An unexpected error occurred: {str(e)}")
        return f"Erreur inattendue: {str(e)}"