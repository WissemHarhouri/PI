
import os
import logging
import tiktoken  # Assuming tiktoken is used as in your original vect.py
from typing import List
from sentence_transformers import SentenceTransformer

# --- Constants ---
DEFAULT_EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
MAX_TOKENS_FOR_EMBEDDING = int(os.getenv("MAX_EMBEDDING_TOKENS", 8191)) 

# --- Token Counting and Truncation (from your original vect.py) ---
def count_tokens(text: str, model_name_for_tiktoken: str = None) -> int:
    if model_name_for_tiktoken is None:
        model_name_for_tiktoken = os.getenv("TIKTOKEN_MODEL", "cl100k_base")
    try:
        enc = tiktoken.encoding_for_model(model_name_for_tiktoken) 
    except KeyError:
        logging.warning(f"Tiktoken model {model_name_for_tiktoken} not found, using cl100k_base.")
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def truncate_if_needed(text: str, max_tokens: int = MAX_TOKENS_FOR_EMBEDDING, model_name_for_tiktoken: str = None) -> str:
    if model_name_for_tiktoken is None:
        model_name_for_tiktoken = os.getenv("TIKTOKEN_MODEL", "cl100k_base")
    try:
        enc = tiktoken.encoding_for_model(model_name_for_tiktoken)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    
    tokens = enc.encode(text)
    if len(tokens) > max_tokens:
        logging.warning(f"[VECTOR] Truncating input from {len(tokens)} to {max_tokens} tokens for embedding.")
        tokens = tokens[:max_tokens]
        return enc.decode(tokens)
    return text


# --- Embedding Function for Queries (local, using sentence-transformers) ---
_embedding_model_instance = None
def get_query_embedding(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    global _embedding_model_instance
    if _embedding_model_instance is None or getattr(_embedding_model_instance, 'model_name', None) != model:
        logging.info(f"[VECTOR] Loading embedding model: {model}")
        _embedding_model_instance = SentenceTransformer(model)
        _embedding_model_instance.model_name = model
    prepared_text = truncate_if_needed(text.replace("\n", " "))
    embedding = _embedding_model_instance.encode([prepared_text])[0]
    logging.info(f"[VECTOR] Query embedding generated successfully using {model}.")
    return embedding

# --- Main pipeline for vectorizing a query (local) ---
def vectorize_query_text(cleaned_query_text: str, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    if not cleaned_query_text:
        logging.warning("[VECTOR] Empty query text provided for vectorization.")
        return None
    logging.info(f"[VECTOR] Vectorizing query: '{cleaned_query_text[:50]}...'")
    return get_query_embedding(cleaned_query_text, model=embedding_model)