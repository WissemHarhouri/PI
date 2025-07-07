from dotenv import load_dotenv
load_dotenv()
import os
import re
import logging
import json
import faiss
from typing import List, Dict, Tuple

from guardrails import Guard
from conli_guard.main import CONLIGuard
from conli_guard.error import conli_fail, FixInterrupt as ConliFixInterrupt
from conli_guard.success import conli_success 

# === Définition du LLM callable via LiteLLM ===
from litellm import completion
model_name = os.getenv("MODEL")
api_key = os.getenv("API_KEY")

def llm(prompt: str) -> str:
    response = completion(model=model_name, messages=[{"role": "user", "content": prompt}], api_base="https://api.groq.com/openai/v1", api_key=api_key)
    return response["choices"][0]["message"]["content"]


# --- Mise en forme Markdown
def format_response_with_markdown(response: str, keywords: List[str] = None) -> str:
    if keywords:
        for kw in keywords:
            if kw.strip():
                try:
                    response = re.sub(f"\\b({re.escape(kw.strip())})\\b", r"**\\1**", response, flags=re.IGNORECASE)
                except re.error:
                    logging.warning(f"[POSTPROCESS] Invalid regex pattern for keyword: {kw}")
    return response

# --- Ajout des sources à la fin
def append_sources_to_response(response: str, retrieved_chunks: List[Dict]) -> str:
    sources = sorted(list(set(
        chunk.get('doc_name', chunk.get('source', 'Source inconnue'))
        for chunk in retrieved_chunks if chunk
    )))
    if sources:
        unique_formatted_sources = []
        seen_sources = set()
        for src in sources:
            if src not in seen_sources:
                unique_formatted_sources.append(f"- {src}")
                seen_sources.add(src)

        citation_block = "\n\n---\n**Sources Consultées:**\n" + "\n".join(unique_formatted_sources)
        return response.strip() + citation_block
    return response

# --- Pipeline complet de post-traitement
def postprocess_llm_response(
    raw_llm_response: str,
    user_query: str,
    retrieved_chunks: List[Dict] = None,
    faiss_index_path: str = "data/index.faiss",
    metadata_path: str = "data/chunks_metadata.json",
    guardrails_enabled: dict = None
) -> Tuple[str, Dict[str, any]]:

    logging.info(f"[POSTPROCESS] Raw LLM response: '{raw_llm_response[:100]}...'")

    processing_flags = {}  

    if retrieved_chunks is None:
        logging.debug("[POSTPROCESS] Aucune liste de chunks fournie, recalcul depuis l'index.")
        query_embedding = vectorize_query_text(user_query, os.getenv("OPENAI_API_KEY"))
        faiss_index = faiss.read_index(faiss_index_path)
        with open(metadata_path, "r", encoding="utf-8") as f:
            chunk_store = json.load(f)

        retrieved_chunks_fallback = retrieve_top_k_chunks_from_memory(
            query_embedding=query_embedding,
            faiss_index_in_memory=faiss_index,
            chunk_store_in_memory=chunk_store,
            top_k=3,
            similarity_threshold=0.7
        )
        retrieved_chunks = retrieved_chunks_fallback


    if guardrails_enabled is None:
        raise ValueError("guardrails_enabled must be provided (dict from Streamlit UI)")
  
    # Always define context_premise for both guards
    context_premise = " ".join(chunk["text"] for chunk in retrieved_chunks if "text" in chunk and isinstance(chunk["text"], str))

# --- CoNLI Validator ---
    if guardrails_enabled.get("conli", False):
        conli_guard = Guard().use(CONLIGuard(llm_callable=model_name, on_fail=conli_fail, on_success=conli_success))
        try:
            conli_guard.validate(
                raw_llm_response,
                metadata={
                    "question": user_query,
                    "samples": context_premise,
                    "pass_on_invalid": False,
                    "fail_type": "fix"
                }
            )
            processing_flags["conli_detected_hallucination"] = False
        except ConliFixInterrupt as e:
            processing_flags["conli_detected_hallucination"] = True
            processing_flags["conli_fix_value"] = e.fix_value
            logging.warning("[POSTPROCESS] === FixInterrupt déclenché (CoNLI) ===")
            logging.warning(f"[POSTPROCESS] Question : {user_query}")
            logging.warning(f"[POSTPROCESS] Réponse brute du LLM : {raw_llm_response}")
            logging.warning(f"[POSTPROCESS] Correction CoNLI : {e.fix_value}")
            logging.warning("[POSTPROCESS] Chunks utilisés pour la validation :")
            for i, chunk in enumerate(retrieved_chunks):
                chunk_text = chunk.get("text", "").replace("\n", " ")
                logging.warning(f"  - Chunk {i+1}: Doc = '{chunk.get('doc_name', 'Inconnu')}', Score = {chunk.get('similarity_score', 0.0):.4f}")
                logging.warning(f"    Texte = '{chunk_text[:150]}...'")
            return e.fix_value, processing_flags

    # Si aucune correction n'a été appliquée, on considère que la réponse est valide
    processing_flags["conli_detected_hallucination"] = False

    # --- Post-traitement supplémentaire (si nécessaire) ---
    response_postprocessed = raw_llm_response

    # Ajout des sources si des chunks ont été récupérés
    if retrieved_chunks and len(retrieved_chunks) > 0:
        response_postprocessed = append_sources_to_response(response_postprocessed, retrieved_chunks)

    # Mise en forme Markdown avec les mots-clés en gras
    response_postprocessed = format_response_with_markdown(response_postprocessed, keywords=["TODO", "IMPORTANT", "NOTE"])

    logging.info(f"[POSTPROCESS] Réponse post-traitée : '{response_postprocessed[:100]}...'")
    return response_postprocessed, processing_flags
