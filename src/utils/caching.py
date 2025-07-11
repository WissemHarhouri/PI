# src/utils/caching.py
import streamlit as st
from sentence_transformers import SentenceTransformer
from groq import Groq
import os

@st.cache_resource
def load_embedding_model():
    """
    Loads the sentence transformer model once and caches it.
    """
    print("--- Loading embedding model (this should only happen once) ---")
    # Use an environment variable for the model name for flexibility
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    return SentenceTransformer(model_name)

@st.cache_resource
def get_groq_client():
    """
    Initializes and caches the Groq API client.
    """
    print("--- Initializing Groq client (this should only happen once) ---")
    return Groq(api_key=os.getenv("GROQ_API_KEY"))
