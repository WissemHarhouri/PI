import re

def extract_course_metadata(text):
    metadata = {
        "course_title": "N/A",
        "course_code": "N/A",
        "program": "N/A",
        "cohort": "N/A",
        "instructor": "N/A",
        "academic_year": "N/A",
        "semester": "N/A",
        "duration": "N/A",
        "description": "N/A"
    }

    # Nettoyer les espaces
    lines = text.splitlines()
    lines = [l.strip() for l in lines if l.strip()]

    for i, line in enumerate(lines):
        if "Course Title" in line or "Course Code" in line:
            match = re.findall(r"(ECUEF|[\w]+)\s+Deep Learning and AI", line)
            if match:
                metadata["course_code"] = match[0]
                metadata["course_title"] = "Deep Learning and AI"
        if "Academic Year" in line:
            match = re.search(r"Academic Year\s+([0-9\-]+)", line)
            if match:
                metadata["academic_year"] = match.group(1)
        if "Semester" in line:
            match = re.search(r"Semester\s+([A-Za-z]+)", line)
            if match:
                metadata["semester"] = match.group(1)
        if "Program" in line:
            metadata["program"] = line.split("Program")[-1].strip()
        if "Cohort" in line:
            metadata["cohort"] = line.split("Cohort")[-1].strip()
        if "Instructor" in line:
            metadata["instructor"] = line.split("Instructor")[-1].strip()
        if "weeks" in line.lower() and "hours" in line.lower():
            match = re.search(r"(\d+)\s*hours", line)
            if match:
                metadata["duration"] = match.group(1) + " min"  # ou "1h30" si conversion

        if "Brief Course Description" in line:
            desc_lines = []
            for j in range(i+1, min(i+10, len(lines))):
                if lines[j].startswith("This course") or lines[j].startswith("Students"):
                    desc_lines.append(lines[j])
                if len(desc_lines) >= 4:
                    break
            metadata["description"] = " ".join(desc_lines)

    return metadata
