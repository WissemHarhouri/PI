# exp_agent/post.py
import re
import logging
from typing import List, Dict, Tuple

# Simuler vérification de toxicité (your basic example)
def is_response_toxic(response: str) -> bool:
    lower_response = response.lower()
    # Basic keywords, a real system would use a dedicated API or more sophisticated model
    toxic_terms = ["idiot", "stupid", "nazi", "racist", "dumb", "hate"] # Expanded slightly
    return any(term in lower_response for term in toxic_terms)

# Vérification de "hallucination probable" / uncertain language (your heuristic)
def detect_uncertain_language_in_response(response: str) -> bool:
    uncertain_patterns = [
        r"\bil semble que\b", r"\bpeut[- ]?être\b", r"\bprobablement\b",
        r"\bselon certaines sources\b", r"\bà ma connaissance\b", r"\bje crois que\b",
        r"\bje pense que\b", r"\bil est possible que\b"
    ]
    return any(re.search(pat, response.lower()) for pat in uncertain_patterns)

# Enrichir visuellement la réponse (ex. Markdown for keywords)
def format_response_with_markdown(response: str, keywords: List[str] = None) -> str:
    if keywords:
        for kw in keywords:
            # Ensure keyword is not empty and is treated as a whole word
            if kw.strip():
                try:
                    # Case-insensitive highlighting of whole words
                    response = re.sub(f"\\b({re.escape(kw.strip())})\\b", r"**\1**", response, flags=re.IGNORECASE)
                except re.error:
                    logging.warning(f"[POSTPROCESS] Invalid regex pattern for keyword: {kw}") # Log regex errors
    return response

# Ajoute les citations à la fin si metadata chunks fournies
def append_sources_to_response(response: str, retrieved_chunks: List[Dict]) -> str:
    # Use 'doc_name' from the main part of the chunk dict, or 'source' as fallback
    sources = sorted(list(set(
        chunk.get('doc_name', chunk.get('source', 'Source inconnue')) 
        for chunk in retrieved_chunks if chunk # Ensure chunk is not None
    )))
    
    if sources:
        # Deduplicate and format sources
        unique_formatted_sources = []
        seen_sources = set()
        for src in sources:
            if src not in seen_sources:
                unique_formatted_sources.append(f"- {src}")
                seen_sources.add(src)
        
        if unique_formatted_sources:
            citation_block = "\n\n---\n**Sources Consultées:**\n" + "\n".join(unique_formatted_sources)
            return response.strip() + citation_block # Ensure no trailing space before appending
    return response

# --- Conceptual Guardrail Application (Placeholder) ---
# This is where you'd call specific guardrail validator functions
# The guardrail logic itself would live in a separate guardrails.py or be integrated
# from the Streamlit app's conceptual guardrail functions.
def apply_conceptual_guardrails(
    response_text: str,
    # context_chunks: List[Dict], # For context-aware guardrails
    # query: str, # For query-aware guardrails
    # guardrails_enabled_flags: Dict # From st.session_state
) -> Tuple[str, Dict[str, bool]]:
    
    # These would call the actual validator functions like conli_guard_validator, etc.
    # from your Streamlit app, or a dedicated guardrails module.
    # For now, these are just illustrative.
    applied_flags = {}
    modified_response = response_text

    # Example: if guardrails_enabled_flags.get("detectpii_on_response"):
    #   is_pii_ok, pii_msg = detectpii_guard_validator(modified_response)
    #   applied_flags["pii_check"] = {"passed": is_pii_ok, "message": pii_msg}
    #   if not is_pii_ok: modified_response = "[Réponse modifiée pour PII]"

    return modified_response, applied_flags


# Pipeline complet de post-traitement
def postprocess_llm_response(
    raw_llm_response: str,
    retrieved_chunks: List[Dict], # Used for appending sources
    query_keywords: List[str] = None, # Keywords from the user's query for highlighting
    block_on_toxic_flag: bool = True,
    # guardrails_enabled_flags: Dict = None # Pass guardrail config if applying them here
) -> Tuple[str, Dict[str, any]]: # Return response and a dict of flags/checks

    logging.info(f"[POSTPROCESS] Raw LLM response: '{raw_llm_response[:100]}...'")

    processing_flags = {
        "initial_toxic_check": is_response_toxic(raw_llm_response),
        "initial_uncertain_lang_check": detect_uncertain_language_in_response(raw_llm_response),
        "guardrail_checks": {} # To store results from conceptual guardrails
    }

    if block_on_toxic_flag and processing_flags["initial_toxic_check"]:
        logging.warning("[POSTPROCESS] Réponse initialement détectée comme toxique — rejet.")
        final_response_text = "⚠️ La réponse générée a été bloquée car son contenu a été jugé inapproprié."
        processing_flags["final_response_blocked_toxic"] = True
        return final_response_text, processing_flags

    # Apply conceptual guardrails that might modify the response or add flags
    # guarded_response, guardrail_flags = apply_conceptual_guardrails(
    #     raw_llm_response,
    #     # retrieved_chunks, user_query, guardrails_enabled_flags
    # )
    # processing_flags["guardrail_checks"] = guardrail_flags
    # current_response_text = guarded_response 
    current_response_text = raw_llm_response # If not using guardrails directly here

    # Format (e.g., Markdown) and append sources
    formatted_response = format_response_with_markdown(current_response_text, query_keywords)
    final_response_text = append_sources_to_response(formatted_response, retrieved_chunks)
    
    logging.info(f"[POSTPROCESS] Final processed response: '{final_response_text[:100]}...'")
    return final_response_text, processing_flags