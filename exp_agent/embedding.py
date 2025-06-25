import os
import logging
import tiktoken # Assuming tiktoken is used as in your original vect.py
from openai import OpenAI, APIError, AuthenticationError, RateLimitError
from typing import List

# --- Constants ---
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small" # Match acq_agent
MAX_TOKENS_FOR_EMBEDDING = 8191 # OpenAI's limit for text-embedding-ada-002 and 3-small

# --- Token Counting and Truncation (from your original vect.py) ---
def count_tokens(text: str, model_name_for_tiktoken: str = "gpt-3.5-turbo") -> int:
   
    try:
        enc = tiktoken.encoding_for_model(model_name_for_tiktoken) 
    except KeyError:
        logging.warning(f"Tiktoken model {model_name_for_tiktoken} not found, using cl100k_base.")
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def truncate_if_needed(text: str, max_tokens: int = MAX_TOKENS_FOR_EMBEDDING, model_name_for_tiktoken: str = "gpt-3.5-turbo") -> str:
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

# --- Embedding Function for Queries (adapted from Streamlit app's get_embedding) ---
def get_query_embedding(text: str, openai_api_key: str, model: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    if not openai_api_key:
        logging.error("[VECTOR] OpenAI API Key not provided for query embedding.")
        # In Streamlit, you'd use st.error. Here, we log and return None.
        return None
    
    prepared_text = truncate_if_needed(text.replace("\n", " ")) # OpenAI recommends replacing newlines

    try:
        client = OpenAI(api_key=openai_api_key)
        response = client.embeddings.create(input=[prepared_text], model=model)
        embedding = response.data[0].embedding
        logging.info(f"[VECTOR] Query embedding generated successfully using {model}.")
        return embedding
    except AuthenticationError:
        logging.error("[VECTOR] OpenAI API Key is invalid for query embedding.")
        return None
    except RateLimitError:
        logging.error("[VECTOR] Rate limit exceeded for OpenAI Embeddings API during query embedding.")
        return None
    except APIError as e:
        logging.error(f"[VECTOR] OpenAI API error during query embedding: {e}")
        return None
    except Exception as e:
        logging.error(f"[VECTOR] An unexpected error occurred during query embedding: {str(e)}")
        return None

# --- Main pipeline for vectorizing a query (combines your logic) ---
def vectorize_query_text(cleaned_query_text: str, openai_api_key: str, embedding_model: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    if not cleaned_query_text:
        logging.warning("[VECTOR] Empty query text provided for vectorization.")
        return None
    logging.info(f"[VECTOR] Vectorizing query: '{cleaned_query_text[:50]}...'")
    return get_query_embedding(cleaned_query_text, openai_api_key, model=embedding_model)