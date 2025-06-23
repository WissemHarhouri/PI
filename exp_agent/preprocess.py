# exp_agent/net.py
import re
import unicodedata
import logging
import os
import json
from typing import Tuple, Optional, List
from openai import OpenAI

# Initialize OpenAI client (can also be passed as an argument for more flexibility)
# For now, keeping the module-level client initialization as in your original file
# Ensure OPENAI_API_KEY is set in your .env or environment
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_API_KEY_AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))
except Exception as e:
    client = None
    OPENAI_API_KEY_AVAILABLE = False
    logging.error(f"[NET_PREPROCESS] Failed to initialize OpenAI client: {e}. LLM-based intention detection will fail if API key is not provided later.")


# === Version simple (fallback) — mots-clés (from your net.py)
def detect_intention_keywords(query: str) -> str:
    query_lower = query.lower()
    if any(kw in query_lower for kw in ["résume", "résumer", "synthèse", "condense"]):
        return "demande_resume"
    elif any(kw in query_lower for kw in ["explique", "pourquoi", "comment", "définir"]):
        return "explication"
    elif "génère" in query_lower or "écris" in query_lower:
        return "commande_generation"
    else:
        return "question_factuelle"

# === Version LLM — multi-intentions (from your net.py, with API key check)
def detect_intention_llm(query: str, openai_api_key_override: Optional[str] = None) -> List[str]:
    # Use override if provided, else use module-level client if key was available, else fallback
    current_api_key = openai_api_key_override or os.getenv("OPENAI_API_KEY")
    
    if not current_api_key:
        logging.warning("[NET_PREPROCESS] No OpenAI API Key for LLM intention detection. Falling back to keyword-based.")
        return [detect_intention_keywords(query)]

    try:
        # Instantiate client with the determined API key for this call
        temp_client = OpenAI(api_key=current_api_key)
        prompt = f"""
Tu es un classifieur intelligent d’intentions utilisateur. Ta tâche est de détecter toutes les intentions présentes dans cette requête.
Voici les types possibles : ["question_factuelle", "demande_resume", "explication", "commande_generation", "autre"].

Requête : {query}

Réponds uniquement avec une liste JSON valide contenant les intentions détectées. Ne commente rien d'autre.
Par exemple : ["explication", "demande_resume"]
"""
        response = temp_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"), # Use a faster model for classification
            messages=[
                {"role": "system", "content": "Tu es un assistant NLP spécialisé en classification d’intentions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"} # Request JSON output if model supports
        )
        content = response.choices[0].message.content.strip()
        logging.info(f"[NET_PREPROCESS] LLM Intent Detection (raw response): {content}")
        
        # Try to parse the JSON
        try:
            # The response might be a string containing a JSON object,
            # or the model might directly return a dict if response_format works perfectly.
            if isinstance(content, str):
                # Look for a JSON list within the string
                match = re.search(r'\[.*?\]', content)
                if match:
                    intent_list_str = match.group(0)
                    parsed_intentions = json.loads(intent_list_str)
                    if isinstance(parsed_intentions, list):
                        return parsed_intentions
                    else:
                        logging.warning(f"[NET_PREPROCESS] LLM returned JSON but not a list: {parsed_intentions}")
                else:
                    logging.warning(f"[NET_PREPROCESS] LLM response for intent does not contain a recognizable JSON list: {content}")
            
            elif isinstance(content, dict) and "intentions" in content and isinstance(content["intentions"], list) : # if model returns {"intentions": ["a", "b"]}
                 return content["intentions"]


        except json.JSONDecodeError as e:
            logging.warning(f"[NET_PREPROCESS] Failed to parse JSON from LLM for intent: {e}. Raw content: {content}")
        
        # Fallback if JSON parsing fails or content is not as expected
        logging.warning("[NET_PREPROCESS] LLM intent detection failed to produce valid JSON list, falling back to keyword.")
        return [detect_intention_keywords(query)]

    except Exception as e:
        logging.error(f"[NET_PREPROCESS] Error calling LLM for intent detection: {e}")
        return [detect_intention_keywords(query)] # Fallback on any error

# === Nettoyage (from your net.py - good as is)
def clean_query_text(text: str) -> str:
    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8", "ignore")
    text = ''.join(c for c in text if c.isprintable()) # Remove non-printable
    text = re.sub(r"[^\w\s.,!?-]", "", text) # Keep basic punctuation relevant for queries
    text = text.lower() # Convert to lowercase
    text = re.sub(r"\s+", " ", text).strip() # Normalize whitespace
    # Optional: remove repetitive words (be careful with this, might alter meaning)
    # text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text) 
    return text

# === Pipeline principal (adapted)
def preprocess_user_query(
    raw_query: str,
    detect_intent_flag: bool = True,
    use_llm_for_intent: bool = False, # Default to keyword for speed/cost unless specified
    openai_api_key_for_intent: Optional[str] = None # Allow passing API key for intent
) -> Tuple[str, Optional[List[str]]]:
    logging.info(f"[NET_PREPROCESS] Raw user query: {raw_query}")
    cleaned = clean_query_text(raw_query)
    logging.info(f"[NET_PREPROCESS] Cleaned query: {cleaned}")

    intentions = None
    if detect_intent_flag:
        if use_llm_for_intent:
            logging.info("[NET_PREPROCESS] Detecting intention using LLM.")
            intentions = detect_intention_llm(cleaned, openai_api_key_override=openai_api_key_for_intent)
        else:
            logging.info("[NET_PREPROCESS] Detecting intention using keywords.")
            intentions = [detect_intention_keywords(cleaned)]
        logging.info(f"[NET_PREPROCESS] Detected Intent(s): {intentions}")
    
    return cleaned, intentions