import pdfplumber
import re
import json
from collections import defaultdict

def extract_text_from_pdf(path):
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

def parse_course_info(text):
    info = {}
    info["course_title"] = re.search(r"Course Title\s+(.+)", text).group(1).strip()
    info["instructor_name"] = re.search(r"Course Instructor\s+(.+)", text).group(1).strip()
    info["program_name"] = re.search(r"Program\s+(.+)", text).group(1).strip()
    info["academic_year"] = re.search(r"Academic Year\s+(.+?)\s", text).group(1).strip()
    info["semester"] = re.search(r"Semester\s+(.+)", text).group(1).strip()
    info["duration"] = re.search(r"(\d+)\s*weeks\s*/\s*(\d+)\s*hours", text).group(2)
    info["weeks"] = re.search(r"(\d+)\s*weeks\s*/\s*(\d+)\s*hours", text).group(1)
    return info

def parse_frameworks_and_domains(text):
    frameworks = []
    domains = []
    if "TensorFlow" in text:
        frameworks.append("TensorFlow")
    if "PyTorch" in text:
        frameworks.append("PyTorch")
    if "Computer Vision" in text:
        domains.append("Computer Vision")
    if "Natural Language Processing" in text or "NLP" in text:
        domains.append("Natural Language Processing")
    return frameworks, domains

def parse_clos(text):
    clo_section = re.search(r"Course Learning Outcomes \(CLOs\):(.+?)CLO Assessment Scheme", text, re.DOTALL)
    if not clo_section:
        return []
    clo_lines = [line.strip() for line in clo_section.group(1).splitlines() if line.strip()]
    clos = []
    for line in clo_lines:
        match = re.match(r"(\d+)\s+(.+?)\s+(\d+(?:,\d+)*)", line)
        if match:
            _, desc, plos = match.groups()
            clos.append({
                "description": desc.strip(),
                "plos": plos
            })
    return clos

def parse_weeks(text):
    week_section = re.search(r"Course weekly plan:(.+?)Educational Resources", text, re.DOTALL)
    if not week_section:
        return []
    lines = [line.strip() for line in week_section.group(1).splitlines() if line.strip()]
    week_blocks = []
    current_week = {}
    for line in lines:
        week_match = re.match(r"(\d+)\s+(.*)", line)
        if week_match:
            if current_week:
                week_blocks.append(current_week)
            current_week = {"number": week_match.group(1), "title": week_match.group(2)}
        elif "objectives" in line.lower() or "Understand" in line:
            current_week["objectives"] = line
        elif re.search(r"\b\d(,\d)*\b", line):
            clo_match = re.search(r"(\d(?:,\d)*)", line)
            if clo_match:
                current_week["clos"] = clo_match.group(1)
    if current_week:
        week_blocks.append(current_week)
    return week_blocks

def build_json_structure(text):
    info = parse_course_info(text)
    frameworks, domains = parse_frameworks_and_domains(text)
    clos = parse_clos(text)
    weeks = parse_weeks(text)

    return {
        **info,
        "frameworks": frameworks,
        "application_domains": domains,
        "course_learning_objectives": clos,
        "course_weeks": weeks,
        "key_topics": extract_keywords_from_weeks(weeks)
    }

def extract_keywords_from_weeks(weeks):
    keywords = set()
    for week in weeks:
        for word in re.findall(r'\b[A-Z][a-zA-Z]+\b', week.get("title", "") + " " + week.get("objectives", "")):
            if len(word) > 2:
                keywords.add(word)
    return sorted(list(keywords))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Parse syllabus PDF to JSON")
    parser.add_argument("pdf_path", help="Path to the syllabus PDF")
    parser.add_argument("--output", default="syllabus_parsed.json", help="Output JSON file name")
    args = parser.parse_args()

    raw_text = extract_text_from_pdf(args.pdf_path)
    result = build_json_structure(raw_text)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✅ Syllabus parsed and saved to {args.output}")
