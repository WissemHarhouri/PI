from exp_agent.response_postprocessor import postprocess_llm_response
from dotenv import load_dotenv
import os

# Chargement des variables d'environnement
load_dotenv()

# === FAKE LLM qui renvoie une réponse JSON correcte
def fake_llm(prompt):
    return """
{
  "is_toxic": false,
  "is_uncertain": false,
  "has_hallucination": false,
  "is_factually_incorrect": false,
  "is_answer_acceptable": true
}
"""

# Simule un appel
if __name__ == "__main__":
    raw_response = "The Hobbit was written by J.R.R. Tolkien."
    user_query = "Who wrote The Hobbit?"
    keywords = ["Hobbit", "Tolkien"]

    final_response, flags = postprocess_llm_response(
        raw_llm_response=raw_response,
        user_query=user_query,
        query_keywords=keywords,
        llm=fake_llm,
        faiss_index_path="data/index.faiss",
        metadata_path="data/chunks_metadata.json"
    )

    print("=== FINAL RESPONSE ===")
    print(final_response)
    print("=== FLAGS ===")
    print(flags)
