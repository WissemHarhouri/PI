# acq_agent/build_faiss.py
import os
import json
import uuid
from datetime import datetime
import numpy as np
import faiss
from langdetect import detect, LangDetectException
from openai import OpenAI, APIError, AuthenticationError, RateLimitError

# --- File Processing Libs (ensure these are available in your environment) ---
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup
from PIL import Image # For OCR
import easyocr # For OCR
import requests # For URL fetching

# --- Constants ---
EMBEDDING_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-ada-002": 1536,
    "text-embedding-3-large": 3072,
}
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

# --- Global OCR Reader (initialize once) ---
easyocr_reader_instance = None

def get_easyocr_reader():
    global easyocr_reader_instance
    if easyocr_reader_instance is None:
        try:
            easyocr_reader_instance = easyocr.Reader(['en', 'fr'], gpu=False) # Add more languages if needed
        except Exception as e:
            print(f"Warning: Could not initialize EasyOCR reader: {e}")
            easyocr_reader_instance = "unavailable" # Mark as unavailable
    return easyocr_reader_instance if easyocr_reader_instance != "unavailable" else None

# --- Text Preprocessing and Chunking (from Streamlit app) ---
def preprocess_text_for_rag(text):
    import re
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'<[^>]+>', '', text) # Basic HTML tag stripping
    return text

def simple_chunker(text, chunk_size=200, overlap=50):
    words = text.split()
    chunks = []
    current_pos = 0
    while current_pos < len(words):
        end_pos = min(current_pos + chunk_size, len(words))
        chunk_words = words[current_pos:end_pos]
        chunks.append(" ".join(chunk_words))
        if end_pos == len(words):
            break
        current_pos += (chunk_size - overlap)
        if current_pos >= len(words):
            break
    return [c for c in chunks if c.strip()]

# --- Document Text Extraction ---
def extract_text_from_pdf_bytes(file_bytes):
    from io import BytesIO
    try:
        pdf_reader = PdfReader(BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None

def extract_text_from_docx_bytes(file_bytes):
    from io import BytesIO
    try:
        doc = Document(BytesIO(file_bytes))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return None

def extract_text_from_html_bytes(file_bytes):
    try:
        # Assuming file_bytes is actual HTML content, not a path
        soup = BeautifulSoup(file_bytes, "html.parser")
        for script_or_style in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script_or_style.decompose()
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"Error extracting HTML: {e}")
        return None

def extract_text_from_image_bytes(file_bytes):
    from io import BytesIO
    reader = get_easyocr_reader()
    if not reader:
        print("EasyOCR reader not available for image extraction.")
        return None
    try:
        image_np = np.array(Image.open(BytesIO(file_bytes)))
        result = reader.readtext(image_np, detail=0, paragraph=True)
        return "\n".join(result)
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return None

def fetch_and_extract_text_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        doc_name = url
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.title and soup.title.string:
            doc_name = soup.title.string.strip()
        for tag in soup(["script", "style", "header", "footer", "nav", "aside", "form", "meta", "link"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text, doc_name
    except Exception as e:
        print(f"Error fetching/extracting URL '{url}': {e}")
        return None, None

# --- Embedding Function (from Streamlit app, adapted) ---
def get_document_embedding(text, openai_api_key, model=DEFAULT_EMBEDDING_MODEL):
    if not openai_api_key:
        print("Error: OpenAI API Key not provided for embedding.")
        return None
    try:
        client = OpenAI(api_key=openai_api_key)
        text_to_embed = text.replace("\n", " ") # OpenAI recommendation
        response = client.embeddings.create(input=[text_to_embed], model=model)
        return response.data[0].embedding
    except AuthenticationError:
        print("Error: OpenAI API Key is invalid.")
        return None
    except RateLimitError:
        print("Error: Rate limit exceeded for OpenAI Embeddings API.")
        return None
    except APIError as e:
        print(f"Error: OpenAI API error during embedding: {e}")
        return None
    except Exception as e:
        print(f"Error: An unexpected error occurred during embedding: {str(e)}")
        return None

# --- Language Detection (more robust) ---
def detect_document_language(text_sample):
    try:
        if text_sample and len(text_sample) > 10: # Need some text to detect
            return detect(text_sample)
        return "unknown"
    except LangDetectException:
        return "unknown"
    except Exception as e:
        print(f"Language detection error: {e}")
        return "unknown"

# --- Core Index Building Logic for Streamlit (In-Memory) ---
def process_and_index_document_in_memory(
    doc_text_to_process,
    doc_name_for_processing,
    source_type_for_processing,
    openai_api_key,
    embedding_model_name,
    chunk_method,
    # Parameters without defaults now come first after required ones
    current_faiss_index,
    current_chunk_store,
    doc_counter,
    # Parameters with defaults come last
    chunk_size_words=150, # if fixed size
    chunk_overlap_words=20 # if fixed size
):
    if not doc_text_to_process or not doc_text_to_process.strip():
        print(f"Warning: No text to process for '{doc_name_for_processing}'.")
        return current_faiss_index, current_chunk_store, 0 # 0 chunks added

    cleaned_text = preprocess_text_for_rag(doc_text_to_process)
    detected_lang = detect_document_language(cleaned_text[:500])

    new_chunks_text = []
    if chunk_method == "Paragraphe ('\\n\\n')":
        new_chunks_text = [p.strip() for p in cleaned_text.split('\n\n') if p.strip()]
    elif chunk_method == "Taille Fixe (Mots)":
        new_chunks_text = simple_chunker(cleaned_text, chunk_size=chunk_size_words, overlap=chunk_overlap_words)
    else:
        print(f"Warning: Unknown chunk method '{chunk_method}'. Defaulting to paragraph.")
        new_chunks_text = [p.strip() for p in cleaned_text.split('\n\n') if p.strip()]

    if not new_chunks_text:
        print(f"Warning: No chunks generated for '{doc_name_for_processing}'.")
        return current_faiss_index, current_chunk_store, 0

    doc_id = f"doc_{doc_counter}_{str(uuid.uuid4())[:8]}" # Use the passed doc_counter
    doc_chunk_count = 0
    embeddings_for_faiss = []

    # Get embedding dimension
    embedding_dim = EMBEDDING_DIMS.get(embedding_model_name)
    if not embedding_dim:
        print(f"Error: Unknown embedding dimension for model {embedding_model_name}. Using default.")
        embedding_dim = EMBEDDING_DIMS[DEFAULT_EMBEDDING_MODEL]

    # Initialize FAISS index if it's None or dimension mismatch
    if current_faiss_index is None or current_faiss_index.d != embedding_dim:
        print(f"Initializing new FAISS index for dimension {embedding_dim} (model: {embedding_model_name}).")
        current_faiss_index = faiss.IndexFlatIP(embedding_dim) # Inner Product for cosine similarity with normalized vectors
        current_chunk_store.clear() # Clear metadata if index changes

    for i_chunk, chunk_text in enumerate(new_chunks_text):
        if not chunk_text:
            continue
        embedding = get_document_embedding(chunk_text, openai_api_key, model=embedding_model_name)
        if embedding:
            embeddings_for_faiss.append(np.array(embedding, dtype='float32'))
            chunk_metadata_item = {
                'id': str(uuid.uuid4()), 'doc_id': doc_id, 'doc_name': doc_name_for_processing,
                'chunk_index_in_doc': i_chunk, 'text': chunk_text,
                'metadata': {
                    'source_doc_id': doc_id, 'source_doc_name': doc_name_for_processing,
                    'source_type': source_type_for_processing, 'char_length': len(chunk_text),
                    'word_count': len(chunk_text.split()), 'lang': detected_lang, # Lang of whole doc for now
                    'created_at': datetime.now().isoformat()
                }
            }
            current_chunk_store.append(chunk_metadata_item)
            doc_chunk_count += 1
        else:
            print(f"Warning: Failed to get embedding for chunk {i_chunk} of '{doc_name_for_processing}'. Skipping.")

    if embeddings_for_faiss:
        try:
            current_faiss_index.add(np.array(embeddings_for_faiss))
            print(f"Successfully added {doc_chunk_count} chunks from '{doc_name_for_processing}' to FAISS. Total in index: {current_faiss_index.ntotal}")
        except Exception as e_faiss:
            print(f"Error adding embeddings to FAISS: {e_faiss}")
            # Potentially rollback additions to chunk_store for this document if FAISS add fails
            # For simplicity, not implemented here.
            return current_faiss_index, current_chunk_store, 0 # Or handle partial success

    return current_faiss_index, current_chunk_store, doc_chunk_count

# --- Functions to save/load FAISS index and metadata to/from files (from your original build_faiss.py) ---
def save_faiss_index_and_metadata(faiss_index, chunk_store, output_dir="data/"):
    if faiss_index is None or not chunk_store:
        print("Nothing to save: FAISS index or metadata is empty.")
        return
    try:
        os.makedirs(output_dir, exist_ok=True)
        faiss_index_path = os.path.join(output_dir, "index.faiss")
        metadata_path = os.path.join(output_dir, "chunks_metadata.json")

        faiss.write_index(faiss_index, faiss_index_path)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(chunk_store, f, indent=2, ensure_ascii=False)
        print(f"FAISS index saved to {faiss_index_path}")
        print(f"Metadata saved to {metadata_path}")
    except Exception as e:
        print(f"Error saving FAISS index/metadata: {e}")

def load_faiss_index_and_metadata_from_files(index_path="data/index.faiss", metadata_path="data/chunks_metadata.json"):
    loaded_index = None
    loaded_metadata = []
    if os.path.exists(index_path) and os.path.exists(metadata_path):
        try:
            loaded_index = faiss.read_index(index_path)
            with open(metadata_path, "r", encoding="utf-8") as f:
                loaded_metadata = json.load(f)
            print(f"FAISS index loaded from {index_path} ({loaded_index.ntotal} vectors, dim {loaded_index.d}).")
            print(f"Metadata loaded from {metadata_path} ({len(loaded_metadata)} items).")
        except Exception as e:
            print(f"Error loading FAISS index/metadata from files: {e}")
            return None, []
        return loaded_index, loaded_metadata
    else:
        print("FAISS index or metadata file not found. Starting fresh.")
        return None, []