# main.py
import streamlit as st
import os
import json
import sys
from dotenv import load_dotenv

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.parsing.syllabus_parser import extract_text_from_pdf, build_json_structure
from src.acquisition.document_processing import chunk_and_index_syllabus
from src.generation.exam_generator import generate_exam_from_topics
from src.utils.pdf_generator import create_pdf_from_text

load_dotenv()

st.set_page_config(page_title="ExamGenius", layout="wide")
st.title("📚 ExamGenius — Generate Exams from Syllabuses")

# --- Sidebar for Exam Configuration ---
st.sidebar.title("⚙️ Exam Configuration")
difficulty = st.sidebar.selectbox("Select Difficulty", ["easy", "medium", "hard"], index=1)
num_mcqs = st.sidebar.number_input("Number of MCQs", min_value=1, max_value=20, value=5)
num_short_answers = st.sidebar.number_input("Number of Short Answer Questions", min_value=1, max_value=10, value=3)
# --- End Sidebar ---

uploaded_file = st.file_uploader("Upload a Syllabus (PDF)", type="pdf")

if uploaded_file:
    temp_path = "raw_data/uploaded_syllabus.pdf"

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())

    st.info("Parsing syllabus...")
    raw_text = extract_text_from_pdf(temp_path)
    syllabus_data = build_json_structure(raw_text)

    parsed_json_path = "data/syllabus_parsed.json"
    with open(parsed_json_path, "w") as f:
        json.dump(syllabus_data, f, indent=2)

    st.success("Syllabus successfully parsed!")

    with st.expander("Course Info"):
        st.json(syllabus_data)

    st.info("Indexing syllabus content for exam generation...")
    chunks = chunk_and_index_syllabus(parsed_json_path)

    topics = syllabus_data["key_topics"][:5]  # Limit topics for clarity
    st.subheader("Generate Exam")
    if st.button("Generate Exam"):
        exam = generate_exam_from_topics(topics, num_mcqs=num_mcqs, num_short_answers=num_short_answers, difficulty=difficulty)
        
        st.markdown("### Multiple Choice Questions")
        st.code(exam["mcqs"])
        mcq_pdf = create_pdf_from_text("Multiple Choice Questions", exam["mcqs"])
        st.download_button(
            label="Download MCQs as PDF",
            data=mcq_pdf,
            file_name="mcqs.pdf",
            mime="application/pdf"
        )

        st.markdown("### Short Answer Questions")
        st.code(exam["short_answers"])
        sa_pdf = create_pdf_from_text("Short Answer Questions", exam["short_answers"])
        st.download_button(
            label="Download Short Answers as PDF",
            data=sa_pdf,
            file_name="short_answers.pdf",
            mime="application/pdf"
        )

    if st.checkbox("Download Full Parsed JSON"):
        with open(parsed_json_path, "r") as f:
            st.download_button("Download JSON", f.read(), file_name="syllabus_parsed.json")