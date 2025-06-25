
from dotenv import load_dotenv
load_dotenv()
import os
import re
import logging
import json
import faiss
from typing import List, Dict, Tuple

from guardrails import Guard
from exp_agent.chunk_retriever import retrieve_top_k_chunks_from_memory
from exp_agent.embedding import vectorize_query_text

from conli_guard.main import CONLIGuard
from conli_guard.error import conli_fail, FixInterrupt as ConliFixInterrupt
from conli_guard.success import conli_success 
from cove_guard.main import COVEGuard
from cove_guard.error import cove_fail, FixInterrupt as CoveFixInterrupt

from cove_guard.success import cove_success

# === Définition du LLM callable via LiteLLM ===
from litellm import completion
model_name = os.getenv("OPENAI_MODEL") or "gpt-4"

def llm(prompt: str) -> str:
    response = completion(model=model_name, messages=[{"role": "user", "content": prompt}])
    return response["choices"][0]["message"]["content"]

# --- Analyse qualité LLM via prompt
def analyze_response_with_llm(response: str, llm) -> Dict[str, bool]:
    import re
    prompt = f"""
Tu es un vérificateur de qualité pour des réponses d'assistant IA. Analyse attentivement la réponse suivante :

--- Réponse ---
{response}
--- Fin de réponse ---

Dis-moi si les points suivants sont vrais ou faux. Réponds uniquement en JSON, sans aucun commentaire :

{{
  \"is_toxic\": true | false,
  \"is_uncertain\": true | false,
  \"has_hallucination\": true | false,
  \"is_factually_incorrect\": true | false,
  \"is_answer_acceptable\": true | false
}}
Exemple de réponse attendue :
{{"is_toxic": false, "is_uncertain": false, "has_hallucination": false, "is_factually_incorrect": false, "is_answer_acceptable": true}}
"""
    try:
        result = llm(prompt).strip()
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as e_json:
                logging.error(f"[LLM ANALYSIS] LLM returned invalid JSON: {json_str} | Error: {e_json}")
        else:
            logging.error(f"[LLM ANALYSIS] LLM did not return JSON. Output: {result}")
        return {
            "is_toxic": False,
            "is_uncertain": False,
            "has_hallucination": False,
            "is_factually_incorrect": False,
            "is_answer_acceptable": True
        }
    except Exception as e:
        logging.error(f"[LLM ANALYSIS] Failed to analyze response: {e}")
        return {
            "is_toxic": False,
            "is_uncertain": False,
            "has_hallucination": False,
            "is_factually_incorrect": False,
            "is_answer_acceptable": True
        }

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
    query_keywords: List[str] = None,
    retrieved_chunks: List[Dict] = None,
    block_on_toxic_flag: bool = True,
    llm=llm,
    faiss_index_path: str = "data/index.faiss",
    metadata_path: str = "data/chunks_metadata.json",
    guardrails_enabled: dict = None
) -> Tuple[str, Dict[str, any]]:

    logging.info(f"[POSTPROCESS] Raw LLM response: '{raw_llm_response[:100]}...'")

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

    # Analyse qualité simple
    analysis_flags = analyze_response_with_llm(raw_llm_response, llm)
    processing_flags = dict(analysis_flags)

    if block_on_toxic_flag and analysis_flags.get("is_toxic", False):
        logging.warning("[POSTPROCESS] Réponse jugée toxique par le LLM — blocage.")
        final_response_text = "⚠️ La réponse générée a été bloquée car elle a été jugée inappropriée."
        processing_flags["final_response_blocked_toxic"] = True
        return final_response_text, processing_flags

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
    
    
    
    
    
    # --- CoVE Validator ---
    if guardrails_enabled.get("cove", False):
        cove_guard = Guard().use(COVEGuard(llm_callable=model_name, on_fail=cove_fail, on_success=cove_success))
        try:
            cove_guard.validate(
                raw_llm_response,
                metadata={
                    "question": user_query,
                    "samples": context_premise,
                    "pass_on_invalid": False,
                    "fail_type": "fix"
                }
            )
            processing_flags["cove_detected_hallucination"] = True
        except CoveFixInterrupt as e:
            processing_flags["cove_detected_hallucination"] = True
            processing_flags["cove_fix_value"] = e.fix_value
            logging.warning("[POSTPROCESS] === FixInterrupt déclenché (CoVE) ===")
            logging.warning(f"[POSTPROCESS] Question : {user_query}")
            logging.warning(f"[POSTPROCESS] Réponse brute du LLM : {raw_llm_response}")
            logging.warning(f"[POSTPROCESS] Correction CoVE : {e.fix_value}")
            logging.warning("[POSTPROCESS] Chunks utilisés pour la validation :")
            for i, chunk in enumerate(retrieved_chunks):
                chunk_text = chunk.get("text", "").replace("\n", " ")
                logging.warning(f"  - Chunk {i+1}: Doc = '{chunk.get('doc_name', 'Inconnu')}', Score = {chunk.get('similarity_score', 0.0):.4f}")
                logging.warning(f"    Texte = '{chunk_text[:150]}...'")
            return e.fix_value, processing_flags

    return raw_llm_response, processing_flags
