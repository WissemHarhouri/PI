# main.py (Streamlit App)
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True' # Add this line AT THE VERY TOP
import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

# --- Import RAG Modules ---
from acq_agent.build_faiss import (
    extract_text_from_pdf_bytes, extract_text_from_docx_bytes,
    extract_text_from_html_bytes, extract_text_from_image_bytes,
    fetch_and_extract_text_from_url,
    process_and_index_document_in_memory,
    save_faiss_index_and_metadata, load_faiss_index_and_metadata_from_files,
    EMBEDDING_DIMS, DEFAULT_EMBEDDING_MODEL
)
from exp_agent.preprocess import preprocess_user_query
from exp_agent.embedding import vectorize_query_text
from exp_agent.chunk_retriever import retrieve_top_k_chunks_from_memory
from exp_agent.generator import build_augmented_prompt, generate_llm_response
from exp_agent.response_postprocessor import postprocess_llm_response

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Assistant RAG Modulaire", page_icon="🧩", layout="wide")
st.markdown("<h1 style='text-align: center;'>Assistant RAG Modulaire</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- Initialize Session State (more comprehensive) ---
def init_session_state():
    defaults = {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "rag_enabled": True,
        "faiss_index": None, # Will hold the FAISS index object
        "faiss_index_dim": None, # Stores dimension of the current index
        "chunk_store": [],   # List of dicts, metadata for each chunk
        "doc_counter": 0,    # For generating unique doc IDs
        "chat_history": [],  # For storing conversation
        # Keys for resetting file uploaders/inputs
        "file_uploader_key": 0,
        "url_input_key": 0,
        "text_area_key": 0,
        # Conceptual Guardrails (as in your single Streamlit app)
        "guardrails_enabled": {
            "conli": False, "cove": False, "contextcheck": False,
            "detectpii": False, "unusual_prompt": False
        },
        # For loading/saving index (optional)
        "index_loaded_from_file": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")

    # API Key
    api_key_input = st.text_input(
        "Clé API OpenAI:",
        type="password",
        value=st.session_state.openai_api_key or "",
        help="Votre clé API OpenAI. Peut aussi être définie via la variable d'environnement OPENAI_API_KEY."
    )
    if api_key_input:
        st.session_state.openai_api_key = api_key_input

    # Embedding Model
    prev_embedding_model = st.session_state.embedding_model
    st.session_state.embedding_model = st.selectbox(
        "Modèle d'Embedding OpenAI:",
        list(EMBEDDING_DIMS.keys()),
        index=list(EMBEDDING_DIMS.keys()).index(st.session_state.embedding_model),
        help="Changer de modèle effacera l'index existant si les dimensions diffèrent."
    )
    if st.session_state.embedding_model != prev_embedding_model:
        st.warning("Modèle d'embedding changé. L'index FAISS sera réinitialisé au prochain traitement de document.")
        st.session_state.faiss_index = None
        st.session_state.chunk_store = []
        st.session_state.faiss_index_dim = None
        st.session_state.index_loaded_from_file = False # Reset flag

    st.info(f"Modèle actif : `{st.session_state.embedding_model}`")

    # RAG Toggle
    st.session_state.rag_enabled = st.checkbox("Activer RAG (Recherche Augmentée)", value=st.session_state.rag_enabled)

    # Conceptual Guardrails
    st.subheader("Validateurs Guardrails (Conceptuel)")
    for guard_key, guard_label in {
        "conli": "conli-guard (cohérence LLM/connaissances)",
        "cove": "cove-guard (justification logique)",
        "detectpii": "detectpii-guard (détection PII)",
        "unusual_prompt": "unusual-prompt-guard (requêtes suspectes)"
    }.items():
        st.session_state.guardrails_enabled[guard_key] = st.checkbox(
            guard_label, value=st.session_state.guardrails_enabled[guard_key]
        )
    st.divider()
    # --- Load/Save Index (Optional) ---
    st.subheader("Gestion de l'Index FAISS")
    if st.button("Sauvegarder l'Index Actif", help="Sauvegarde l'index en mémoire vers data/index.faiss et data/chunks_metadata.json"):
        if st.session_state.faiss_index and st.session_state.chunk_store:
            save_faiss_index_and_metadata(st.session_state.faiss_index, st.session_state.chunk_store)
            st.success("Index et métadonnées sauvegardés dans `data/`.")
        else:
            st.warning("Aucun index en mémoire à sauvegarder.")

    if st.button("Charger l'Index depuis Fichiers", help="Charge data/index.faiss et data/chunks_metadata.json. Écrase l'index en mémoire."):
        loaded_index, loaded_metadata = load_faiss_index_and_metadata_from_files()
        if loaded_index and loaded_metadata:
            st.session_state.faiss_index = loaded_index
            st.session_state.chunk_store = loaded_metadata
            st.session_state.faiss_index_dim = loaded_index.d
            # Try to infer embedding model from dimension, or warn user
            matched_model = False
            for model, dim in EMBEDDING_DIMS.items():
                if dim == loaded_index.d:
                    st.session_state.embedding_model = model
                    matched_model = True
                    break
            if matched_model:
                st.success(f"Index chargé. Modèle d'embedding ajusté à '{st.session_state.embedding_model}'.")
            else:
                st.warning(f"Index chargé (dim: {loaded_index.d}), mais aucun modèle d'embedding correspondant trouvé. Veuillez sélectionner un modèle compatible.")
            st.session_state.index_loaded_from_file = True
            st.rerun() # Refresh UI with new index info
        else:
            st.error("Échec du chargement de l'index depuis les fichiers.")
    st.caption(f"Index en mémoire: {'Chargé depuis fichier' if st.session_state.index_loaded_from_file else 'Construit dynamiquement'}")


# --- Main Application Area ---

# 1. Agent d'Acquisition
st.header("1. Acquisition de Documents")
doc_acquisition_tabs = st.tabs(["📁 Fichier", "📝 Texte Brut", "🌐 URL Web", "🖼️ Image (OCR)"])

doc_text_to_process = None
doc_name = "Document Inconnu"
source_type = "inconnu"
input_source_used = None # For resetting inputs

with doc_acquisition_tabs[0]: # File Upload
    uploaded_file = st.file_uploader(
        "Choisissez un fichier (PDF, DOCX, HTML, TXT):",
        type=["pdf", "docx", "html", "txt"],
        key=f"file_uploader_{st.session_state.file_uploader_key}"
    )
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        doc_name = uploaded_file.name
        source_type = f"fichier: {uploaded_file.type}"
        input_source_used = "file"
        if uploaded_file.type == "application/pdf":
            doc_text_to_process = extract_text_from_pdf_bytes(file_bytes)
        elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
            doc_text_to_process = extract_text_from_docx_bytes(file_bytes)
        elif uploaded_file.type == "text/html":
            doc_text_to_process = extract_text_from_html_bytes(file_bytes.decode('utf-8', errors='ignore')) # Assuming html is text
        elif uploaded_file.type == "text/plain":
            doc_text_to_process = file_bytes.decode('utf-8', errors='ignore')
        else:
            st.warning(f"Type de fichier non supporté pour l'extraction directe: {uploaded_file.type}")

with doc_acquisition_tabs[1]: # Text Area
    manual_doc_name = st.text_input("Nom du document (optionnel):", key=f"manual_doc_name_{st.session_state.text_area_key}")
    text_area_content = st.text_area("Collez le texte ici:", height=200, key=f"text_area_{st.session_state.text_area_key}")
    if text_area_content and not uploaded_file: # Prioritize file upload
        doc_text_to_process = text_area_content
        doc_name = manual_doc_name.strip() or f"Texte Collé {st.session_state.doc_counter + 1}"
        source_type = "texte collé"
        input_source_used = "text_area"

with doc_acquisition_tabs[2]: # URL
    url_input = st.text_input("Entrez l'URL d'une page web:", key=f"url_input_{st.session_state.url_input_key}")
    if url_input and not uploaded_file and not text_area_content: # Prioritize other inputs
        with st.spinner(f"Récupération et extraction de {url_input}..."):
            fetched_text, fetched_doc_name = fetch_and_extract_text_from_url(url_input)
        if fetched_text:
            doc_text_to_process = fetched_text
            doc_name = fetched_doc_name or url_input
            source_type = f"URL: {url_input}"
            input_source_used = "url"
        elif url_input: # if url_input was provided but fetch failed
            st.error("Impossible de récupérer ou d'extraire le contenu de l'URL.")

with doc_acquisition_tabs[3]: # Image OCR
    uploaded_image_file = st.file_uploader(
        "Choisissez une image (PNG, JPG, JPEG):",
        type=["png", "jpg", "jpeg"],
        key=f"image_uploader_{st.session_state.file_uploader_key}" # Can share key if only one type of file uploader is active per tab
    )
    if uploaded_image_file and not uploaded_file and not text_area_content and not url_input : # Prioritize other inputs
        file_bytes = uploaded_image_file.getvalue()
        doc_name = uploaded_image_file.name
        source_type = f"image (OCR): {uploaded_image_file.type}"
        input_source_used = "image_file"
        with st.spinner("Extraction du texte de l'image (OCR)..."):
            doc_text_to_process = extract_text_from_image_bytes(file_bytes)
        if not doc_text_to_process and uploaded_image_file:
            st.error("Impossible d'extraire le texte de l'image.")


# Chunking Method
col_chunk1, col_chunk2 = st.columns(2)
with col_chunk1:
    chunk_method_selected = st.selectbox("Méthode de Découpage:", ["Paragraphe ('\\n\\n')", "Taille Fixe (Mots)"])
with col_chunk2:
    chunk_size_words_val = 150
    chunk_overlap_words_val = 20
    if chunk_method_selected == "Taille Fixe (Mots)":
        chunk_size_words_val = st.slider("Taille Chunks (mots):", 50, 500, 150)
        chunk_overlap_words_val = st.slider("Chevauchement (mots):", 0, 100, 20)

if st.button("✨ Traiter et Indexer le Document"):
    if not st.session_state.openai_api_key:
        st.error("Veuillez configurer votre clé API OpenAI dans la barre latérale.")
    elif doc_text_to_process and doc_text_to_process.strip():
        st.session_state.doc_counter += 1
        with st.spinner(f"Traitement de '{doc_name}' et indexation FAISS..."):
            new_faiss_index, new_chunk_store, chunks_added = process_and_index_document_in_memory(
                doc_text_to_process=doc_text_to_process,
                doc_name_for_processing=doc_name,
                source_type_for_processing=source_type,
                openai_api_key=st.session_state.openai_api_key,
                embedding_model_name=st.session_state.embedding_model,
                chunk_method=chunk_method_selected,
                chunk_size_words=chunk_size_words_val,
                chunk_overlap_words=chunk_overlap_words_val,
                current_faiss_index=st.session_state.faiss_index,
                current_chunk_store=st.session_state.chunk_store,
                doc_counter=st.session_state.doc_counter
            )
            if chunks_added > 0:
                st.session_state.faiss_index = new_faiss_index
                st.session_state.chunk_store = new_chunk_store # process_and_index appends, so this is fine
                st.session_state.faiss_index_dim = new_faiss_index.d
                # --- Save index and metadata to disk ---
                save_faiss_index_and_metadata(new_faiss_index, new_chunk_store)
                st.success(f"{chunks_added} chunks de '{doc_name}' ajoutés à l'index. Total : {st.session_state.faiss_index.ntotal} chunks.")
                # Reset the input that was used
                if input_source_used == "file" or input_source_used == "image_file": st.session_state.file_uploader_key += 1
                elif input_source_used == "url": st.session_state.url_input_key += 1
                elif input_source_used == "text_area": st.session_state.text_area_key += 1
                st.session_state.index_loaded_from_file = False # New content added dynamically
                st.rerun()
            else:
                st.warning(f"Aucun chunk n'a été ajouté pour '{doc_name}'. Vérifiez le contenu ou les logs.")
    else:
        st.warning("Veuillez fournir un document (fichier, texte, URL ou image) à traiter.")

# Display Indexed Chunks Overview
st.subheader(" Aperçu de l'Index")
if st.session_state.faiss_index and st.session_state.faiss_index.ntotal > 0:
    st.info(f"**{st.session_state.faiss_index.ntotal}** chunks indexés (Dimension: {st.session_state.faiss_index_dim}). "
            f"Métadonnées pour **{len(st.session_state.chunk_store)}** chunks.")
    if st.session_state.faiss_index.ntotal != len(st.session_state.chunk_store):
        st.warning("Incohérence: Nombre de vecteurs FAISS != nombre de métadonnées de chunks.")
    
    with st.expander("Voir les derniers chunks indexés (aperçu)"):
        num_to_show = min(5, len(st.session_state.chunk_store))
        if num_to_show > 0:
            preview_data = [{
                "Nom Doc": c.get('doc_name', 'N/A'),
                "Source": c.get('metadata',{}).get('source_type', 'N/A'),
                "Langue (Doc)": c.get('metadata',{}).get('lang','N/A'),
                "Aperçu": c['text'][:100] + "..." if len(c['text']) > 100 else c['text']
            } for c in reversed(st.session_state.chunk_store[-num_to_show:])]
            st.dataframe(preview_data, use_container_width=True)
else:
    st.info("Aucun document n'a encore été indexé. Ajoutez des documents pour commencer.")

st.markdown("---")

# 2. Agent d'Exploitation (RAG Pipeline)
st.header("2. Exploitation RAG et Conversation")

# Chat History Display (moved before input to show history above current interaction)
st.subheader("💬 Conversation")
for i, (sender_type, message_content) in enumerate(st.session_state.chat_history):
    if sender_type == "user":
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(message_content)
    else: # assistant
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(message_content)
            # Optionally, display sources or pipeline details related to this assistant message
            # This would require storing more context with each assistant message in chat_history










# User Input
user_query = st.chat_input("Posez votre question à l'assistant RAG...")

if user_query:
    st.session_state.chat_history.append(("user", user_query)) # Add user query to chat
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(user_query)

    if not st.session_state.openai_api_key:
        st.error("Clé API OpenAI non configurée. Impossible de répondre.")
        st.stop()

    final_response_for_chat = ""
    pipeline_details_md = "###  Détails du Pipeline RAG:\n\n"

    # 1. Prétraitement de la requête (OUTSIDE spinner for early guardrail exit)
    cleaned_query, detected_intent, flags = preprocess_user_query(
        raw_query=user_query,
        detect_intent_flag=True, # Enable intent detection
        openai_api_key_for_intent=st.session_state.openai_api_key,
        guardrails_enabled=st.session_state.guardrails_enabled
    )
    # 2. Afficher un warning simple en cas de guardrail déclenché
    if "pii_violation" in flags:
        st.warning("⚠️ Donnée personnelle détectée et anonymisée automatiquement.")
    elif "unusual_prompt" in flags:
        st.warning("⚠️ Requête jugée inhabituelle ou suspecte.")

    # 2. Ajouter les détails dans pipeline_details_md s'il y a des flags (y compris pii)
    if flags:
        pipeline_details_md += "**Guardrails d'entrée déclenchés :**\n"
        for flag in flags:
            if flag == "pii_violation":
                pipeline_details_md += "- ⚠️ DetectPII : Donnée personnelle détectée et nettoyée.\n"
            elif flag == "unusual_prompt":
                pipeline_details_md += "- ⚠️ UnusualPrompt : Requête jugée inhabituelle ou suspecte.\n"
            else:
                pipeline_details_md += f"- {flag}\n"
        pipeline_details_md += "\n"
    else:
        pipeline_details_md += "Aucun guardrail d'entrée déclenché.\n\n"

    # On continue le pipeline normalement
    pipeline_details_md += f"**1. Prétraitement Requête:**\n   - Nettoyée: `{cleaned_query}`\n   - Intention(s): `{detected_intent}`\n\n"

    
    retrieved_chunks = []
    if st.session_state.rag_enabled:
        with st.spinner("Recherche et génération de la réponse..."):
            # 2. Vectorisation de la requête
            query_embedding = vectorize_query_text(
                cleaned_query_text=cleaned_query,
                openai_api_key=st.session_state.openai_api_key,
                embedding_model=st.session_state.embedding_model
            )
            pipeline_details_md += f"**2. Vectorisation Requête:** {'Succès' if query_embedding else 'Échec'}\n\n"

            if query_embedding:
                top_k_retrieval = 3
                similarity_threshold_val = 0.3  
                retrieved_chunks = retrieve_top_k_chunks_from_memory(
                    query_embedding=query_embedding,
                    faiss_index_in_memory=st.session_state.faiss_index,
                    chunk_store_in_memory=st.session_state.chunk_store,
                    top_k=top_k_retrieval,
                    similarity_threshold=similarity_threshold_val
                )
                pipeline_details_md += f"**3. Récupération Chunks:** {len(retrieved_chunks)} chunk(s) pertinent(s) trouvé(s).\n"
                if retrieved_chunks:
                    for i_rc, rc in enumerate(retrieved_chunks):
                        pipeline_details_md += (f"   - Chunk {i_rc+1}: Doc='{rc.get('doc_name', 'N/A')}', "
                                                f"Score={rc.get('similarity_score', 0.0):.4f}, "
                                                f"Texte='{rc['text'][:60]}...'\n")
                pipeline_details_md += "\n"
            else:
                pipeline_details_md += "**Mode RAG actif, mais aucun document indexé.** La réponse sera basée sur les connaissances générales du LLM.\n\n"

            # 4. Construction du Prompt Augmenté
            augmented_prompt = build_augmented_prompt(cleaned_query, retrieved_chunks)
            pipeline_details_md += f"**4. Prompt Augmenté (aperçu):**\n```markdown\n{augmented_prompt[:500]}...\n```\n\n"

            # 5. Génération de la Réponse LLM
            raw_llm_response = generate_llm_response(
                prompt=augmented_prompt,
                openai_api_key=st.session_state.openai_api_key,
                llm_model="gpt-4o-mini-2024-07-18" 
            )
            pipeline_details_md += f"**5. Réponse Brute LLM (aperçu):**\n`{raw_llm_response[:100]}...`\n\n"

            # 6. Post-traitement de la Réponse
            query_keywords_for_highlight = cleaned_query.split()[:5]

            final_response_for_chat, postprocessing_flags = postprocess_llm_response(
                raw_llm_response=raw_llm_response,
                user_query=cleaned_query,
                query_keywords=query_keywords_for_highlight,
                faiss_index_path="data/index.faiss",
                metadata_path="data/chunks_metadata.json",
                guardrails_enabled=st.session_state.guardrails_enabled
            )

            # Affichage détaillé de toutes les étapes du post-processing
            pipeline_details_md += "### Post-traitement & Analyse Qualité\n\n"

            pipeline_details_md += "**Analyse qualité LLM (Heuristique via prompt)**\n"
            for key in ["is_toxic", "is_uncertain", "has_hallucination", "is_factually_incorrect", "is_answer_acceptable"]:
                value = postprocessing_flags.get(key)
                if value is not None:
                    icon = "✔" if value is False else "⚠️" if value is True else "ℹ️"
                    pipeline_details_md += f"- `{key}`: {icon} `{value}`\n"
            pipeline_details_md += "\n"

            # Analyse CoNLI
            if "conli_detected_hallucination" in postprocessing_flags:
                if postprocessing_flags["conli_detected_hallucination"]:
                    pipeline_details_md += "** CoNLI Validator:** Hallucination détectée ⚠️\n"
                    pipeline_details_md += f"- Correction proposée :\n```markdown\n{postprocessing_flags.get('conli_fix_value', '')}\n```\n"
                else:
                    pipeline_details_md += "** CoNLI Validator:** ✅ Aucun problème détecté.\n"
            pipeline_details_md += "\n"

            # Analyse CoVE
            if "cove_detected_hallucination" in postprocessing_flags:
                if postprocessing_flags["cove_detected_hallucination"]:
                    pipeline_details_md += "** CoVE Validator:** Raisonnement incorrect détecté ⚠️\n"
                    pipeline_details_md += f"- Correction proposée :\n```markdown\n{postprocessing_flags.get('cove_fix_value', '')}\n```\n"
                else:
                    pipeline_details_md += "** CoVE Validator:** ✅ Raisonnement logique correct.\n"
            pipeline_details_md += "\n"

            # Aperçu de la réponse finale avec mise en forme
            pipeline_details_md += "**Réponse Finale Formatée (aperçu):**\n"
            pipeline_details_md += f"```markdown\n{final_response_for_chat[:500]}...\n```\n"
    else:
        pipeline_details_md += "**Mode RAG désactivé.** La réponse sera basée sur les connaissances générales du LLM.\n\n"

    # Display Assistant's response
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(final_response_for_chat)
        with st.expander("Voir les détails du pipeline RAG pour cette réponse"):
            st.markdown(pipeline_details_md)
            
    st.session_state.chat_history.append(("assistant", final_response_for_chat))
    # Note: To store pipeline_details_md with the message, you'd need to adjust chat_history structure.

st.sidebar.divider()
if st.sidebar.button("🗑️ Réinitialiser la Conversation et l'Index", help="Efface l'historique du chat et l'index FAISS en mémoire."):
    init_session_state() # Resets to defaults, including clearing faiss_index and chat_history
    st.session_state.faiss_index = None # Explicitly ensure index is None
    st.session_state.chunk_store = []
    st.session_state.faiss_index_dim = None
    st.session_state.chat_history = []
    st.session_state.doc_counter = 0
    st.session_state.index_loaded_from_file = False
    st.success("Conversation et index en mémoire réinitialisés.")
    st.rerun()