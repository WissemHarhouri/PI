import streamlit as st

# ⚠️ Doit être le tout premier appel Streamlit
st.set_page_config(page_title="ExamGenius", layout="wide")

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import pandas as pd
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.parsing.syllabus_parser import extract_text_from_pdf
from src.parsing.extractor import extract_clos_and_weekly_plan
from src.generation.exam_generator import generate_exam_from_custom_config
from src.utils.pdf_generator import create_pdf_from_text


def compute_clo_weights(topic_weights, topic_to_clos):
    clo_weights = defaultdict(float)
    for topic, weight in topic_weights.items():
        clos = topic_to_clos.get(topic, [])
        if not clos:
            continue
        weight_per_clo = weight / len(clos)
        for clo in clos:
            clo_weights[clo] += weight_per_clo
    return clo_weights


def distribute_questions_by_weight(weights_dict, total_questions):
    distributed = []
    total_weight = sum(weights_dict.values())

    for key, weight in weights_dict.items():
        n = round((weight / total_weight) * total_questions)
        distributed.extend([key] * n)

    while len(distributed) < total_questions:
        distributed.append(max(weights_dict, key=weights_dict.get))
    while len(distributed) > total_questions:
        distributed.pop()

    return distributed


st.title("📚 ExamGenius — Generate Exams from Syllabuses")

uploaded_file = st.file_uploader("📄 Upload a Syllabus (PDF)", type="pdf")

if uploaded_file:
    temp_path = "raw_data/uploaded_syllabus.pdf"
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    raw_text = extract_text_from_pdf(temp_path)
    clo_data, weekly_df, merged_df = extract_clos_and_weekly_plan(temp_path)

    st.subheader("🎯 Course Learning Outcomes (CLOs)")
    if not clo_data.empty:
        st.dataframe(clo_data)
    else:
        st.warning("Aucun CLO détecté.")

    st.subheader("📆 Weekly Plan")
    if not weekly_df.empty:
        with st.expander("Afficher le plan hebdomadaire"):
            st.dataframe(weekly_df[["Week", "Topic", "Related CLO#"]])
    else:
        st.warning("Weekly Plan non détecté.")

    st.subheader("🔗 CLOs associés aux sujets hebdomadaires")
    if not merged_df.empty:
        st.dataframe(merged_df)
    else:
        st.info("Aucune correspondance CLO-Topic détectée.")

    st.subheader("🧠 Sélection des sujets et configuration des questions")


    # --- DEBUG: Show all topics and mapping ---
    topics = [str(t).strip() for t in weekly_df["Topic"].unique().tolist() if pd.notnull(t)]

    # Build topic_to_clos with stripped topic names
    topic_to_clos = {str(topic).strip(): clos for topic, clos in zip(weekly_df["Topic"], weekly_df["Related CLO List"])}

    topic_weights = {}

    st.markdown("👉 Sélectionnez les sujets, leur poids (total 100%), et le nombre total de questions.")

    with st.form("exam_config_form"):
        total_percentage = 0
        selected_topics = []

        for topic in topics:
            col1, col2 = st.columns([3, 1])
            with col1:
                selected = st.checkbox(topic, key=f"chk_{topic}")
            with col2:
                weight = st.number_input("Poids %", 0, 100, 0, 5, key=f"weight_{topic}")
            if selected:
                topic_weights[topic] = weight
                selected_topics.append(topic)
                total_percentage += weight

        total_questions = st.number_input("Nombre total de questions", min_value=1, max_value=50, value=10)

        submitted = st.form_submit_button("✅ Valider la sélection")
        auto_distribute = st.form_submit_button("🔄 Auto-distribuer selon fréquence")


        if auto_distribute:
            # Use stripped topic names for counting
            topic_counts = weekly_df["Topic"].apply(lambda x: str(x).strip() if pd.notnull(x) else x).value_counts()
            selected_topics = topic_counts.index.tolist()
            total = topic_counts.sum()
            topic_weights = {topic: 100 * count / total for topic, count in topic_counts.items()}


            clo_weights_raw = compute_clo_weights(topic_weights, topic_to_clos)
            total_clo_weight = sum(clo_weights_raw.values())
            clo_weights = {clo: 100 * w / total_clo_weight for clo, w in clo_weights_raw.items()}

            diff = 100 - sum(clo_weights.values())
            if abs(diff) > 0.01:
                first_key = next(iter(clo_weights))
                clo_weights[first_key] += diff

            topic_weights = clo_weights

            st.success("Poids distribués automatiquement selon fréquence des CLOs.")
            st.dataframe(pd.DataFrame([{"CLO": k, "Weight (%)": round(v, 2)} for k, v in topic_weights.items()]))

    if (submitted or auto_distribute) and topic_weights:
        if round(sum(topic_weights.values()),2) != 100:
            st.error(f"❌ Total = {sum(topic_weights.values())}%. Il doit être 100%.")
        elif not topic_weights:
            st.warning("⚠️ Aucun sujet sélectionné.")
        else:
            st.success("Répartition validée.")
            st.dataframe(pd.DataFrame([{"CLO": t, "Weight (%)": w} for t, w in topic_weights.items()]))

            # Only update distributed_clos and question_config in session_state on submit/auto-distribute
            distributed_clos = distribute_questions_by_weight(topic_weights, total_questions)
            st.session_state.distributed_clos = distributed_clos

            # Reset question_config and type/diff for new distribution
            st.session_state.question_config = []
            question_types = ["QCM", "QCU", "Rédigée", "Vrai/Faux"]
            for i, clo in enumerate(distributed_clos):
                st.session_state[f"type_{i}"] = "QCM"
                st.session_state[f"diff_{i}"] = "medium"

    # Always show the distribution table and question config section if distributed_clos exists in session_state
    if "distributed_clos" in st.session_state:
        distributed_clos = st.session_state.distributed_clos
        # Show the distribution table (CLO/weight) for the current distribution
        st.success("Répartition en cours (CLOs distribués pour chaque question):")
        st.dataframe(pd.DataFrame([
            {"Question": i+1, "CLO": clo}
            for i, clo in enumerate(distributed_clos)
        ]))

        question_types = ["QCM", "QCU", "Rédigée", "Vrai/Faux"]
        question_config = []
        st.subheader("🧩 Définir le type et la difficulté de chaque question")
        for i, clo in enumerate(distributed_clos):
            col1, col2 = st.columns(2)
            with col1:
                # Use session_state for value and update
                q_type = st.selectbox(f"Type Q{i+1}", question_types, key=f"type_{i}", index=question_types.index(st.session_state.get(f"type_{i}", "QCM")))
            with col2:
                difficulty = st.selectbox(f"Difficulté Q{i+1}", ["easy", "medium", "hard"], key=f"diff_{i}", index=["easy", "medium", "hard"].index(st.session_state.get(f"diff_{i}", "medium")))
            question_config.append({
                "type": q_type,
                "difficulty": difficulty,
                "clo": clo
            })
        st.session_state.question_config = question_config

    # Bouton hors formulaire pour générer l'examen
    if st.button("📤 Générer l'examen personnalisé"):
        if "question_config" not in st.session_state or not st.session_state.question_config:
            st.error("⚠️ Configurez les questions avant de générer l'examen.")
        else:
            exam = generate_exam_from_custom_config(st.session_state.question_config, topic_to_clos)

            if exam:
                st.markdown("### 📄 Aperçu de l'examen complet généré")
                combined_text = ""

                for q_type, questions in exam.items():
                    if questions:
                        combined_text += f"### {q_type} Questions\n\n"
                        combined_text += "\n\n".join(questions)
                        combined_text += "\n\n"

                # Affichage dans Streamlit
                st.code(combined_text)

                # Génération d’un seul PDF
                pdf_data = create_pdf_from_text("Exam Complet", combined_text)
                st.download_button(
                    label="📥 Télécharger l'examen complet (PDF)",
                    data=pdf_data,
                    file_name="examen_complet.pdf",
                    mime="application/pdf"
                )
