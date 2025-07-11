import pdfplumber
import re
import pandas as pd

def extract_clos_and_weekly_plan(pdf_path):
    # --------------------- Étape 1 : Extraction CLOs depuis tableau ---------------------
    clo_data = []
    found_headers = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table_num, table in enumerate(tables):
                if len(table) < 2:
                    continue  # skip tables with no data
                header_row = [str(h).strip().lower().replace(' ', '') for h in table[0]]
                found_headers.append((page_num, table_num, header_row))
                print(f"[DEBUG] Table {table_num+1} on Page {page_num+1} headers: {header_row}")

                # Indices non vides
                non_empty_indices = [i for i, h in enumerate(header_row) if h]
                filtered_headers = [header_row[i] for i in non_empty_indices]

                # Matching souple des colonnes
                clo_num_idx_f = next((i for i, h in enumerate(filtered_headers) if 'clo' in h), None)
                desc_keywords = ['description', 'details', 'learningoutcome', 'outcome', 'objective']
                clo_desc_idx_f = next((i for i, h in enumerate(filtered_headers) if any(k in h for k in desc_keywords)), None)

                if clo_num_idx_f is not None and clo_desc_idx_f is not None:
                    print(f"[DEBUG] Using indices: CLO# = {clo_num_idx_f}, Description = {clo_desc_idx_f}")
                    data_rows = [row for row in table[1:] if len(row) >= len(non_empty_indices)]
                    clo_rows = []
                    for row in data_rows:
                        try:
                            # On utilise les index originaux, pas les filtrés
                            clo_number = row[non_empty_indices[clo_num_idx_f]].strip() if row[non_empty_indices[clo_num_idx_f]] else None
                            clo_desc = row[non_empty_indices[clo_desc_idx_f]].strip() if row[non_empty_indices[clo_desc_idx_f]] else None
                            if clo_number or clo_desc:
                                clo_rows.append([clo_number, clo_desc])
                        except IndexError:
                            print("[DEBUG] Ligne ignorée à cause d'un index invalide")
                            continue

                    clo_data = pd.DataFrame(clo_rows, columns=["CLO#", "CLO Description"])
                    break
            if len(clo_data) > 0:
                break

    # --------------------- Fallback : Extraction depuis texte brut ---------------------
    if len(clo_data) == 0:
        print("[DEBUG] No CLO table found. Trying text fallback...")
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and "Course Learning Outcomes" in text:
                    print(f"[DEBUG] Found CLOs in raw text on page {page_num + 1}")
                    clo_pattern = r'CLO#\s*(\d+)\s*(.*?)\s*(?=CLO#|\Z)'
                    matches = re.findall(clo_pattern, text, re.DOTALL)
                    clo_data = pd.DataFrame(matches, columns=["CLO#", "CLO Description"])
                    clo_data["CLO#"] = clo_data["CLO#"].str.strip()
                    clo_data["CLO Description"] = clo_data["CLO Description"].str.replace(r'\s+', ' ', regex=True).str.strip()
                    break

    if len(clo_data) == 0:
        print("[DEBUG] CLOs not found in table or text. Headers seen:")
        for page_num, table_num, headers in found_headers:
            print(f"  Page {page_num+1}, Table {table_num+1}: {headers}")
    else:
        print("[DEBUG] CLO Data Extracted:")

    # --------------------- Nettoyage CLOs ---------------------
    # Remplir CLO# si vide
    clo_data["CLO#"] = clo_data["CLO#"].fillna("").astype(str).str.strip()
    if clo_data["CLO#"].replace("", pd.NA).isna().all():
        clo_data["CLO#"] = [str(i + 1) for i in range(len(clo_data))]

    # Nettoyage final
    clo_data["CLO#"] = clo_data["CLO#"].str.replace(r"[^\d]", "", regex=True)
    clo_data = clo_data[clo_data["CLO#"] != ""]

    # --------------------- Étape 2 : Extraction Weekly Plan ---------------------
    weekly_data = []
    with pdfplumber.open(pdf_path) as pdf:
        try:
            table1 = pdf.pages[3].extract_tables()[0]
            table2 = pdf.pages[4].extract_tables()[0]
            combined = table1 + table2
        except Exception as e:
            print(f"[DEBUG] Error reading weekly tables: {e}")
            combined = []

        for row in combined:
            if len(row) >= 4:
                week = row[0]
                topic = row[1]
                related = row[3]
                weekly_data.append({
                    "Week": week.strip() if week else "",
                    "Topic": topic.strip().replace("\n", " ") if topic else "",
                    "Related CLO#": related.strip().replace("\n", ",") if related else ""
                })

    weekly_df = pd.DataFrame(weekly_data)

    # Nettoyage des CLO liés (corrige la fusion des numéros)
    weekly_df["Related CLO#"] = (
        weekly_df["Related CLO#"]
        .str.replace(r"[^\d,]", ",", regex=True)  # remplace tout sauf chiffres/virgule par une virgule
        .str.replace(r",+", ",", regex=True)      # évite les virgules multiples
        .str.strip(",")                             # retire les virgules en début/fin
    )
    weekly_df["Related CLO List"] = weekly_df["Related CLO#"].str.split(",")

    # --------------------- Étape 3 : Jointure CLOs x Weekly ---------------------
    expanded_rows = []
    for _, row in weekly_df.iterrows():
        for clo in row["Related CLO List"]:
            clo = clo.strip()
            if clo:
                expanded_rows.append({
                    "Week": row["Week"],
                    "Topic": row["Topic"],
                    "CLO#": clo
                })

    merged_df = pd.DataFrame(expanded_rows).merge(clo_data, on="CLO#", how="left")

    return clo_data, weekly_df, merged_df
