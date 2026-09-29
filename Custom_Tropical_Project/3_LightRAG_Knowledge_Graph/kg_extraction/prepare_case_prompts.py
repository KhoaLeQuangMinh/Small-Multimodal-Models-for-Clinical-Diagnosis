#!/usr/bin/env python3
"""
prepare_case_prompts.py

Reads partA_final.jsonl and generates 1,797 self-contained prompt files
in kg_extraction/case_prompts/ ready for parallel extraction by Antigravity subagents.
"""

import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_PROMPTS_DIR = os.path.join(SCRIPT_DIR, "case_prompts")
EXTRACTED_TRIPLETS_DIR = os.path.join(SCRIPT_DIR, "extracted_triplets")

POSSIBLE_JSONL_PATHS = [
    os.path.join(SCRIPT_DIR, "../2_Clinical_Verification/kaggle_partA/partA_final.jsonl"),
    os.path.join(SCRIPT_DIR, "../../2_Clinical_Verification/kaggle_partA/partA_final.jsonl"),
    "/Users/apple/VGU/Year 4 2026-2027/Project_Dr. Tran Duc Khanh/Datasets/Custom_Tropical_Project/2_Clinical_Verification/kaggle_partA/partA_final.jsonl",
    "/content/partA_final.jsonl",
]

PROMPT_HEADER = """You extract medical entities and relationships from clinical case reports to build a Knowledge Graph.

Your output MUST be a valid JSON object with exactly two arrays: "entities" and "relationships".
Do NOT include markdown fences (```json), introductory prose, or conversational remarks before or after the JSON.

---Task---
Extract entities and relationships from the `---Input Text---` section below.

---Instructions---
1. Strict Adherence to JSON Format: Your output MUST be a valid JSON object with `entities` and `relationships` arrays only.
2. Quantity Limits: Output at most 100 total records and at most 40 entity objects. Output fewer records if fewer high-value items are present. Only output relationship objects whose `source` and `target` are both included in the `entities` array.
3. Prioritize High-Signal Medical Triples:
   - Identify the primary pathogen / organism (e.g., Mycobacterium tuberculosis, Paragonimus kellicotti, Sarcoptes scabiei).
   - Identify active clinical diagnoses, complications, and symptoms (e.g., Spontaneous Pneumothorax, Hemoptysis, Hydrocephalus, Norwegian scabies).
   - Identify diagnostic modalities and key imaging findings (e.g., Chest X-ray, Contrast-Enhanced CT, Skin Scraping, Pus Culture).
   - Identify treatments and medications (e.g., Ivermectin, Permethrin, Praziquantel, Dexamethasone).
   - Link these into meaningful relationship triples (e.g., Pathogen -> CAUSES -> Condition, Procedure -> REVEALED -> Finding, Patient -> TREATED_WITH -> Drug).
4. Output Language: The entire output must be in English. Proper nouns, species names, and anatomical terms must be kept in their standard scientific terminology.
5. Entity Object Schema:
   - `name`: Clean, concise entity name (avoid pronouns like "he", "she", "the patient").
   - `type`: One of the types listed below.
   - `description`: 1-2 sentence description grounded specifically in this patient's case.
6. Relationship Object Schema:
   - `source`: Must match an entity `name` exactly.
   - `target`: Must match an entity `name` exactly.
   - `keywords`: 1-3 comma-separated theme keywords summarizing the relation (e.g., "parasitic etiology, pulmonary complication").
   - `description`: A clear, objective sentence explaining how source and target interact in this patient.

---Entity Types---
Classify each entity using one of the following standard types:
- Person: Human individuals, specific patient demographics
- Creature: Non-human living beings, parasites, bacteria, viruses, fungi
- Organization: Hospitals, healthcare teams, research institutions
- Location: Geographic regions, endemic countries, specific body locations
- Event: Occurrences, disease episodes, surgical procedures, clinical visits
- Concept: Clinical concepts, pathological states, pathophysiological theories
- Method: Diagnostic techniques, laboratory tests, imaging modalities, staining
- Content: Formal clinical guidelines, scoring systems, reports
- Data: Vital signs, lab values, measurements, counts
- Artifact: Devices, catheters, surgical tools, chest tubes, medications
- NaturalObject: Anatomical organs, tissues, arteries, biological specimens
- Other: Use only if no other category applies

---Output Format Template---
{
  "entities": [
    {
      "name": "Paragonimus kellicotti",
      "type": "Creature",
      "description": "North American lung fluke parasite that caused secondary spontaneous pneumothorax."
    },
    {
      "name": "Spontaneous Pneumothorax",
      "type": "Event",
      "description": "Abrupt pleural air leak and left lung collapse requiring chest tube placement."
    }
  ],
  "relationships": [
    {
      "source": "Paragonimus kellicotti",
      "target": "Spontaneous Pneumothorax",
      "keywords": "pulmonary complication, parasitic etiology",
      "description": "Larval migration and cavitation in the left lung caused secondary spontaneous pneumothorax."
    }
  ]
}

---Input Text---
"""

def main():
    os.makedirs(CASE_PROMPTS_DIR, exist_ok=True)
    os.makedirs(EXTRACTED_TRIPLETS_DIR, exist_ok=True)

    jsonl_file = next((p for p in POSSIBLE_JSONL_PATHS if os.path.exists(p)), None)
    if not jsonl_file:
        raise FileNotFoundError(f"Could not locate partA_final.jsonl in candidate paths: {POSSIBLE_JSONL_PATHS}")

    print(f"Reading dataset: {jsonl_file}")
    cases = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    total = len(cases)
    print(f"Loaded {total} cases. Generating prompt files in {CASE_PROMPTS_DIR}...")

    for idx, row in enumerate(cases):
        case_id = row["case_id"]
        title = row.get("title", "")
        present_diseases = ", ".join(row.get("present", [])) or "Unknown"
        main_problem = row.get("main_problem", "N/A")

        evidence_quotes = []
        for d, info in row.get("candidates", {}).items():
            if info.get("status") == "present" and info.get("evidence"):
                evidence_quotes.extend(info["evidence"])
        evidence_str = " ".join(evidence_quotes) if evidence_quotes else "N/A"

        img_findings = [
            f"[{img.get('image_type', 'image')}/{img.get('image_subtype', 'finding')}]: {img.get('caption', '')}"
            for img in row.get("images", []) if img.get("caption")
        ]
        img_str = " | ".join(img_findings) if img_findings else "No imaging panels."

        case_document = (
            f"Case ID: {case_id} - {title}\n"
            f"Confirmed Diagnosis: {present_diseases}\n"
            f"Primary Clinical Problem: {main_problem}\n"
            f"Diagnostic Evidence: {evidence_str}\n"
            f"Imaging Findings: {img_str}\n\n"
            f"Clinical Narrative:\n{row.get('case_text', '')}"
        )

        full_prompt_text = PROMPT_HEADER + case_document.strip() + "\n"
        out_filename = f"{idx+1:04d}_{case_id}.txt"
        out_path = os.path.join(CASE_PROMPTS_DIR, out_filename)

        with open(out_path, "w", encoding="utf-8") as out_f:
            out_f.write(full_prompt_text)

    print(f"✅ Successfully generated {total} case prompt files in:\n   {CASE_PROMPTS_DIR}")

if __name__ == "__main__":
    main()
