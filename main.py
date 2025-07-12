import streamlit as st


# ⚠️ Doit être le tout premier appel Streamlit
st.set_page_config(page_title="ExamGenius", layout="wide")
import openai
import os
from dotenv import load_dotenv
load_dotenv()
import sys
import pandas as pd
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.parsing.syllabus_parser import extract_text_from_pdf
from src.parsing.extractor import extract_clos_and_weekly_plan
from src.generation.exam_generator import generate_exam_from_custom_config
from src.utils.pdf_generator import create_pdf_from_text

from src.parsing.parse import extract_course_metadata

import openai

# Optional: mapping for heuristic fallback
BLOOMS_LEVELS = {
    "Remember": ["define", "list", "name", "recall", "identify"],
    "Understand": ["explain", "summarize", "describe", "interpret"],
    "Apply": ["use", "solve", "demonstrate", "implement"],
    "Analyze": ["compare", "contrast", "differentiate", "examine"],
    "Evaluate": ["justify", "critique", "defend", "assess"],
    "Create": ["design", "construct", "develop", "formulate"]
}


load_dotenv()

import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load GROQ_API_KEY from .env

def classify_bloom_level(question_text):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "❌ GROQ_API_KEY missing"

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {
                "role": "user",
                "content": f"""Given the question: "{question_text}", classify its Bloom's taxonomy level. 
The possible levels are: Remember, Understand, Apply, Analyze, Evaluate, Create.
Return ONLY the level."""
            }
        ],
        "temperature": 0
    }

    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("❌ Groq API error:", e)
        return "LLM Error"


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


    # --- SIDEBAR ---
st.sidebar.title("ExamGenius Options")
st.sidebar.markdown("---")
exam_title = st.sidebar.text_input("Titre de l'examen", value="Examen personnalisé")
show_help = st.sidebar.checkbox("Afficher l'aide", value=False)
theme = st.sidebar.radio("Thème", ["Clair", "Sombre"], index=0)
reset = st.sidebar.button(" Réinitialiser la configuration")

if reset:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

st.title(f" {exam_title}")

if show_help:
        st.info("""
        **Instructions :**
        1. Téléchargez un syllabus PDF.
        2. Configurez la répartition des sujets et des questions.
        3. Personnalisez le type et la difficulté de chaque question.
        4. Générez et téléchargez l'examen.
        """)

uploaded_file = st.sidebar.file_uploader("📄 Upload a Syllabus (PDF)", type="pdf")
if uploaded_file:
    temp_path = "raw_data/uploaded_syllabus.pdf"
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    result_text = extract_text_from_pdf(temp_path)
    course_metadata = extract_course_metadata(result_text)
    clo_data, weekly_df, merged_df = extract_clos_and_weekly_plan(temp_path)

    st.subheader(" Course Learning Outcomes (CLOs)")
    if not clo_data.empty:
        st.dataframe(clo_data)
    else:
        st.warning("Aucun CLO détecté.")

    st.subheader(" Weekly Plan")
    if not weekly_df.empty:
        with st.expander("Afficher le plan hebdomadaire"):
            st.dataframe(weekly_df[["Week", "Topic", "Related CLO#"]])
    else:
        st.warning("Weekly Plan non détecté.")

    st.subheader(" CLOs associés aux sujets hebdomadaires")
    if not merged_df.empty:
        st.dataframe(merged_df)
    else:
        st.info("Aucune correspondance CLO-Topic détectée.")

    st.subheader(" Sélection des sujets et configuration des questions")
    st.markdown("---")

    # --- DEBUG: Show all topics and mapping ---
    excluded_topics = [
        "Applications in Computer Vision",
        "Final Project Presentation",
        "Course Feedback and Wrap-Up"
    ]
    topics = [
        str(t).strip() for t in weekly_df["Topic"].unique().tolist()
        if pd.notnull(t) and str(t).strip() not in excluded_topics
    ]

    # Build topic_to_clos with stripped topic names
    topic_to_clos = {str(topic).strip(): clos for topic, clos in zip(weekly_df["Topic"], weekly_df["Related CLO List"])}

    topic_weights = {}

    st.markdown(" Sélectionnez les sujets, leur poids (total 100%), et le nombre total de questions.")

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

        submitted = st.form_submit_button(" Valider la sélection")
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

        if (submitted or auto_distribute):
            st.info(f"[DEBUG] total_percentage: {round(sum(topic_weights.values()),2)}%")
            if not topic_weights:
                st.warning("⚠️ Aucun sujet sélectionné. Veuillez cocher au moins un sujet.")
            elif round(sum(topic_weights.values()),2) != 100:
                st.error(f"❌ Total = {sum(topic_weights.values())}% Il doit être 100%. Modifiez les poids pour atteindre 100%.")
            else:
                st.success("Répartition validée.")
                st.dataframe(pd.DataFrame([{"CLO": t, "Weight (%)": w} for t, w in topic_weights.items()]))

                # Only update distributed_clos and question_config in session_state on submit/auto-distribute
                distributed_clos = distribute_questions_by_weight(topic_weights, total_questions)
                st.session_state.distributed_clos = distributed_clos

                # Reset question_config and type/diff for new distribution ONLY if not already set
                st.session_state.question_config = []
                question_types = ["QCM", "QCU", "Rédigée", "Vrai/Faux"]
                for i, clo in enumerate(distributed_clos):
                    if f"type_{i}" not in st.session_state:
                        st.session_state[f"type_{i}"] = "QCM"
                    if f"diff_{i}" not in st.session_state:
                        st.session_state[f"diff_{i}"] = "medium"

        # Always show the distribution table and question config section if distributed_clos exists in session_state
        if "distributed_clos" in st.session_state:
            distributed_clos = st.session_state.distributed_clos
            st.markdown("---")
            st.success("Répartition en cours (CLOs distribués pour chaque question):")
            st.dataframe(pd.DataFrame([
                {"Question": i+1, "CLO": clo}
                for i, clo in enumerate(distributed_clos)
            ]))

            question_types = ["QCM", "QCU", "Rédigée", "Vrai/Faux"]
            question_config = []
            st.subheader(" Définir le type et la difficulté de chaque question")
            for i, clo in enumerate(distributed_clos):
                col1, col2 = st.columns(2)
                with col1:
                    q_type = st.selectbox(f"Type Q{i+1}", question_types, key=f"type_{i}", index=question_types.index(st.session_state.get(f"type_{i}", "QCM")))
                with col2:
                    difficulty = st.selectbox(f"Difficulté Q{i+1}", ["easy", "medium", "hard"], key=f"diff_{i}", index=["easy", "medium", "hard"].index(st.session_state.get(f"diff_{i}", "medium")))

                # 🎯 Trouver la description du CLO
                clo_desc = merged_df[merged_df["CLO#"] == str(clo)]["CLO Description"].values
                clo_desc = clo_desc[0] if len(clo_desc) > 0 else "N/A"

                question_config.append({
                    "type": q_type,
                    "difficulty": difficulty,
                    "clo": clo,
                    "clo_desc": clo_desc
                })

            st.session_state.question_config = question_config

    # Bouton hors formulaire pour générer l'examen
    if "distributed_clos" in st.session_state:
        st.markdown("---")
        if st.button(" Générer l'examen personnalisé"):
            if "question_config" not in st.session_state or not st.session_state.question_config:
                st.error("⚠️ Configurez les questions avant de générer l'examen.")
            else:
                exam = generate_exam_from_custom_config(st.session_state.question_config, topic_to_clos)

                # Regrouper toutes les questions dans un seul PDF, chaque type dans une section
                sections = []
                full_text = ""
                # On récupère la configuration pour chaque question
                question_config = st.session_state.question_config if "question_config" in st.session_state else []
                idx = 0
                for q_type, questions in exam.items():
                    if questions:
                        section_title = f"{q_type} Questions"
                        section_text = "\n\n".join(questions)
                        full_text += f"\n\n=== {section_title} ===\n\n{section_text}\n"
                        question_dicts = []
                        for q in questions:
                            # On utilise la config pour chaque question
                            if idx < len(question_config):
                                q_conf = question_config[idx]
                                question_dicts.append({
                                    "text": q,
                                    "type": q_conf.get("type", q_type),
                                    "difficulty": q_conf.get("difficulty", "medium")
                                })
                            else:
                                question_dicts.append({"text": q, "type": q_type, "difficulty": "medium"})
                            idx += 1
                        sections.append({"title": section_title, "questions": question_dicts})
                st.code(full_text)
                # Get course metadata for PDF
                course_metadata = extract_course_metadata(temp_path) if 'extract_course_metadata' in globals() else {}
                teacher = course_metadata.get("instructor", "") if course_metadata else ""
                duration = course_metadata.get("duration", 0) if course_metadata else 0

                # Bloom's Taxonomy Verification
                st.markdown("---")
                st.subheader("🌱 Bloom's Taxonomy Verification")

                taxonomy_analysis = []
                for section in sections:
                    for q in section["questions"]:
                        bloom_level = classify_bloom_level(q["text"])
                        taxonomy_analysis.append({
                            "Question": q["text"],
                            "Detected Bloom Level": bloom_level,
                            "Type": q["type"],
                            "Difficulty": q["difficulty"]
                        })

                df_bloom = pd.DataFrame(taxonomy_analysis)
                st.dataframe(df_bloom)

                # Optional chart for summary
                try:
                    import plotly.express as px
                    bloom_counts = df_bloom["Detected Bloom Level"].value_counts().reset_index()
                    bloom_counts.columns = ["Bloom Level", "Count"]
                    fig = px.pie(bloom_counts, names="Bloom Level", values="Count", title="Bloom's Taxonomy Distribution")
                    st.plotly_chart(fig)
                except:
                    st.warning("📊 Plotly not installed, skipping Bloom's chart.")


                pdf_data = create_pdf_from_text(
                    title=exam_title,
                    teacher=teacher,
                    duration=duration,
                    sections=sections,
                    course_metadata=course_metadata
                )
                st.download_button(
                    label=" Télécharger l'examen complet (PDF)",
                    data=pdf_data,
                    file_name="examen_complet.pdf",
                    mime="application/pdf"
                )
