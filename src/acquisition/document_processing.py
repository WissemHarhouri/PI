# src/acquisition/document_processing.py
import os
import json
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.utils.caching import load_embedding_model
import faiss

def chunk_and_index_syllabus(parsed_data_path):
    """
    Load parsed syllabus JSON, extract topics/weeks,
    create chunks, embed them, and store in FAISS.
    """
    model = load_embedding_model()
    with open(parsed_data_path, "r") as f:
        syllabus = json.load(f)

    # Extract relevant content
    course_title = syllabus["course_title"]
    weeks = syllabus["course_weeks"]

    # Build chunks from weekly topics
    chunks = []
    for week in weeks:
        title = week.get("title", "")
        objectives = week.get("objectives", "")
        chunk_text = f"Week {week.get('number', 'N/A')}: {title}\nObjectives: {objectives}"
        chunks.append(chunk_text)

    # Split into smaller pieces if needed
    splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=50)
    split_chunks = []
    for chunk in chunks:
        split_chunks.extend(splitter.split_text(chunk))

    # Embed chunks
    embeddings = model.encode(split_chunks)

    # Create FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))

    # Save index and metadata
    faiss.write_index(index, os.getenv("FAISS_INDEX_PATH"))

    with open(os.getenv("CHUNKS_METADATA_PATH"), "w") as f:
        json.dump({"chunks": split_chunks}, f)

    return split_chunks