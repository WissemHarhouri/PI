import numpy as np
import faiss # Ensure faiss is imported
from typing import List, Dict, Optional

# --- FAISS Similarity Search (adapted from Streamlit app) ---
def retrieve_top_k_chunks_from_memory(
    query_embedding: Optional[List[float]],
    faiss_index_in_memory: Optional[faiss.Index],
    chunk_store_in_memory: List[Dict],
    top_k: int = 3,
    similarity_threshold: float = 0.7 # from Streamlit app
) -> List[Dict]:
    if query_embedding is None:
        print("Retriever: Query embedding is None. Cannot perform search.")
        return []
    if faiss_index_in_memory is None or faiss_index_in_memory.ntotal == 0:
        print("Retriever: FAISS index is empty or not initialized. No documents to search.")
        return []
    if not chunk_store_in_memory:
        print("Retriever: Chunk metadata store is empty.")
        return []

    query_embedding_np = np.array([query_embedding], dtype='float32')

    # Ensure query embedding dimension matches index dimension
    if query_embedding_np.shape[1] != faiss_index_in_memory.d:
        print(f"Retriever: Query embedding dimension ({query_embedding_np.shape[1]}) "
              f"does not match FAISS index dimension ({faiss_index_in_memory.d}). Cannot search.")
        return []

    try:
        # For IndexFlatIP, D are inner products (cosine similarities for normalized vectors)
        scores, indices = faiss_index_in_memory.search(query_embedding_np, top_k)
    except Exception as e:
        print(f"Retriever: Error during FAISS search: {e}")
        return []

    results = []
    if indices.size > 0:
        for i in range(indices.shape[1]):
            faiss_id = indices[0, i]
            score = float(scores[0, i]) # This is the inner product score

            if faiss_id == -1: # FAISS can return -1 if fewer than k results are found
                continue

            
            if score >= similarity_threshold:
                if 0 <= faiss_id < len(chunk_store_in_memory):
                    # Important: Retrieve metadata based on the actual index in chunk_store_in_memory
                    # FAISS indices are 0-based and correspond to the order items were added.
                    chunk_data = chunk_store_in_memory[faiss_id].copy() # Return a copy
                    chunk_data['similarity_score'] = score # Add score to the retrieved chunk
                    results.append(chunk_data)
                else:
                    print(f"Retriever: Warning - FAISS returned ID {faiss_id} which is out of bounds "
                          f"for chunk_store (size {len(chunk_store_in_memory)}). Skipping.")
    
    print(f"Retriever: Found {len(results)} relevant chunks matching similarity criteria.")
    return results