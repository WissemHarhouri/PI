import re
import unicodedata
import logging
import os
import json
from typing import Tuple, Optional, List
from openai import OpenAI
from guardrails import Guard

# === Import des validateurs input ===
from unusual_prompt_guard.main import UnusualPromptGuard
from unusual_prompt_guard.error import unusual_prompt_fail, ChainInterrupt
from unusual_prompt_guard.success import unusual_prompt_success

from detectpii_guard.main import DetectPII
from detectpii_guard.error import detect_pii_fail, FixInterrupt as PIIInterrupt
from detectpii_guard.success import detect_pii_success

# from contextcheck_guard.main import ContextCheckGuard
# from contextcheck_guard.error import context_fail, FixInterrupt as ContextInterrupt
# from contextcheck_guard.success import context_success


# === Init OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    OPENAI_API_KEY_AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))
except Exception as e:
    client = None
    OPENAI_API_KEY_AVAILABLE = False
    logging.error(f"[NET_PREPROCESS] Failed to initialize OpenAI client: {e}")
    

# === Nettoyage texte
def clean_query_text(text: str) -> str:
    # Normalize Unicode to ASCII
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8", "ignore")   
    # Remove non-printable characters
    text = ''.join(c for c in text if c.isprintable())   
    # Keep word characters, spaces, basic punctuation, and @
    text = re.sub(r"[^\w\s.,!?@-]", "", text)    
    # Convert to lowercase
    text = text.lower()
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip() 
    return text



# === Détection d’intention (LLM uniquement)
def detect_intention_llm(query: str, openai_api_key_override: Optional[str] = None) -> List[str]:
    current_api_key = openai_api_key_override or os.getenv("OPENAI_API_KEY")
    if not current_api_key:
        logging.warning("[NET_PREPROCESS] No OpenAI API Key for LLM intention detection.")
        return []

    try:
        temp_client = OpenAI(api_key=current_api_key)
        prompt = f"""
Tu es un classifieur intelligent d’intentions utilisateur. Ta tâche est de détecter toutes les intentions présentes dans cette requête.
Voici les types possibles : ["question_factuelle", "demande_resume", "explication", "commande_generation", "autre"].

Requête : {query}

Réponds uniquement avec une liste JSON valide contenant les intentions détectées. Ne commente rien d'autre.
Par exemple : ["explication", "demande_resume"]
"""
        response = temp_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": "Tu es un assistant NLP spécialisé en classification d’intentions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        logging.info(f"[NET_PREPROCESS] LLM Intent Detection (raw response): {content}")

        try:
            match = re.search(r'\[.*?\]', content)
            if match:
                intent_list_str = match.group(0)
                parsed_intentions = json.loads(intent_list_str)
                if isinstance(parsed_intentions, list):
                    return parsed_intentions
            elif isinstance(content, dict) and "intentions" in content and isinstance(content["intentions"], list):
                return content["intentions"]
        except json.JSONDecodeError as e:
            logging.warning(f"[NET_PREPROCESS] Failed to parse JSON from LLM for intent: {e}. Raw content: {content}")

        logging.warning("[NET_PREPROCESS] LLM intent detection failed to produce valid JSON list.")
        return []

    except Exception as e:
        logging.error(f"[NET_PREPROCESS] Error calling LLM for intent detection: {e}")
        return []


# === Pipeline principal avec validateurs input
def preprocess_user_query(
    raw_query: str,
    detect_intent_flag: bool = True,
    openai_api_key_for_intent: Optional[str] = None,
    guardrails_enabled: dict = None
) -> Tuple[str, Optional[List[str]], List[str]]:
    if guardrails_enabled is None:
        guardrails_enabled = {}

    logging.info(f"[NET_PREPROCESS] Raw user query: {raw_query}")
    cleaned = clean_query_text(raw_query)
    logging.info(f"[NET_PREPROCESS] Cleaned query: {cleaned}")

    flags = []  # Pour indiquer les validateurs activés

    # === 1. Unusual Prompt Guard
    if guardrails_enabled.get("unusual_prompt", False):
        try:
            guard = Guard().use(UnusualPromptGuard(
                llm_callable=os.getenv("OPENAI_MODEL"),
                on_fail=unusual_prompt_fail,
                on_success=unusual_prompt_success
            ))
            guard.validate(
                cleaned,
                metadata={
                    "context": "QA chatbot is made to answer user questions and generate responses based on data that we have.",
                    "pass_on_invalid": False,
                }
            )
        except ChainInterrupt:
            logging.warning("[PREPROCESS] UnusualPromptValidator chain interrupted.")
            flags.append("unusual_prompt")

    # === 2. Detect PII Guard
    if guardrails_enabled.get("detectpii", False):
        try:
            guard = Guard().use(DetectPII(
                pii_entities=["EMAIL_ADDRESS", "IP_ADDRESS", "IBAN"],
                on_fail=detect_pii_fail,
                on_success=detect_pii_success
            ))
            result = guard.validate(
                cleaned,
                metadata={
                    "context": "Test for PII detection",
                    "pass_on_invalid": False,
                    "fail_type": "fix"
                }
            )
            if hasattr(result, "validated_output") and result.validated_output:
                cleaned = result.validated_output
                flags.append("pii_violation")
        except PIIInterrupt as e:
            logging.warning("[PREPROCESS] DetectPIIValidator triggered fix. Applying fix_value.")
            cleaned = e.fix_value
            flags.append("pii_violation")
        except Exception as e:
            logging.warning(f"[PREPROCESS] DetectPIIValidator failed: {e}")
            flags.append("pii_violation")

    # # === 3. Context Check Guard
    # try:
    #     guard = Guard().use(ContextCheckGuard(
    #         llm_callable=os.getenv("OPENAI_MODEL"),
    #         on_fail=context_fail,
    #         on_success=context_success
    #     ))
    #     guard.validate(
    #         cleaned,
    #         metadata={
    #             "context": "Python programming and software engineering",
    #             "pass_on_invalid": False,
    #         }
    #     )
    # except ContextInterrupt:
    #     logging.warning("[PREPROCESS] ContextCheckValidator interrupted the chain.")
    #     return cleaned, ["context_issue"]
    # except Exception as e:
    #     logging.warning(f"[PREPROCESS] ContextCheckValidator failed: {e}")
    #     return cleaned, ["context_issue"]

    # === 3. Détection d’intention
    intentions = None
    if detect_intent_flag:
        logging.info("[NET_PREPROCESS] Detecting intention using LLM.")
        intentions = detect_intention_llm(cleaned, openai_api_key_override=openai_api_key_for_intent)
        logging.info(f"[NET_PREPROCESS] Detected Intent(s): {intentions}")

    return cleaned, intentions, flags