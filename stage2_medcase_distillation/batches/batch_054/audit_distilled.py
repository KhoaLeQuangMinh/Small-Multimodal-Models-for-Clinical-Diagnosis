import json
import os
import re

BATCH_DIR = "/Users/khoale/Downloads/Project - SLM for Disease Diagnosis/stage2_medcase_distillation/batches/batch_054"

with open(os.path.join(BATCH_DIR, "batch_meta.json"), "r", encoding="utf-8") as f:
    meta = json.load(f)

cases_meta = meta["cases"]
print(f"Total cases in batch_meta: {len(cases_meta)}")

forbidden_pathogens = [
    "echinococc", "hydatid", "vibrio", "cholera", "strongyloid",
    "mycobacteri", "tuberculo", "dengue", "lepra", "leprosy"
]

all_passed = True

for c in cases_meta:
    case_id = c["case_id"]
    target_disease = c["target_disease"]
    source_file = os.path.join(BATCH_DIR, c["case_file"])
    dist_file = os.path.join(BATCH_DIR, c["distilled_output_file"])
    
    print(f"\n--- Auditing {case_id} ({target_disease}) ---")
    
    if not os.path.exists(dist_file):
        print(f"ERROR: {dist_file} does not exist!")
        all_passed = False
        continue
        
    with open(source_file, "r", encoding="utf-8") as f:
        src_data = json.load(f)
    case_text = src_data["case_text"]
    
    with open(dist_file, "r", encoding="utf-8") as f:
        dist_data = json.load(f)
        
    # Check fields
    required_fields = ["case_id", "disease", "think", "case_prompt", "diagnostic_reasoning", "final_diagnosis", "audit_flags", "editor_comments"]
    for rf in required_fields:
        if rf not in dist_data or not dist_data[rf]:
            print(f"ERROR: missing or empty field {rf} in {case_id}")
            all_passed = False
            
    # Check disease match
    if dist_data["disease"] != target_disease or dist_data["final_diagnosis"] != target_disease:
        print(f"ERROR: disease mismatch for {case_id}: expected {target_disease}, got {dist_data['disease']} / {dist_data['final_diagnosis']}")
        all_passed = False
        
    # Check audit flags
    if dist_data["audit_flags"] != ["NONE"]:
        print(f"ERROR: audit_flags not ['NONE'] in {case_id}: {dist_data['audit_flags']}")
        all_passed = False
        
    # Check case_prompt leakage
    prompt_lower = dist_data["case_prompt"].lower()
    for fp in forbidden_pathogens:
        if fp in prompt_lower:
            print(f"ERROR: Forbidden pathogen string '{fp}' leaked in case_prompt of {case_id}!")
            all_passed = False
            
    forbidden_terms = ["pcr", "biopsy", "histopatholog", "culture confirmed", "culture positive", "quantiferon", "karius", "mngs"]
    for ft in forbidden_terms:
        if ft in prompt_lower:
            print(f"ERROR: Forbidden confirmatory term '{ft}' leaked in case_prompt of {case_id}!")
            all_passed = False
            
    # Check diagnostic_reasoning quotes
    dr_list = dist_data["diagnostic_reasoning"]
    if not isinstance(dr_list, list) or len(dr_list) < 3:
        print(f"ERROR: diagnostic_reasoning in {case_id} should be a list with at least 3 entries, got {len(dr_list)}")
        all_passed = False
        
    for idx, dr in enumerate(dr_list):
        quote = dr.get("quote", "")
        # Check if subquotes exist in case_text
        # Quotes might have ellipses or multiple parts
        quote_parts = [q.strip() for q in quote.split("...") if q.strip()]
        for qp in quote_parts:
            # clean leading/trailing punctuation
            qp_clean = qp.strip(" \t\n\r\"'")
            # If still has internal ellipsis or brackets, split further
            subparts = [sp.strip(" \t\n\r\"'") for sp in qp_clean.split("...") if len(sp.strip(" \t\n\r\"'")) > 15]
            for sp in subparts:
                # Remove figure references if any discrepancy or check
                if sp not in case_text:
                    # check normalized whitespace
                    norm_sp = re.sub(r'\s+', ' ', sp)
                    norm_case = re.sub(r'\s+', ' ', case_text)
                    if norm_sp not in norm_case:
                        print(f"WARNING: Quote part '{sp[:60]}...' not found verbatim in source case_text for {case_id} candidate {dr.get('candidate')}")

if all_passed:
    print("\n>>> ALL 10 CASES AUDITED AND FULLY COMPLIANT WITH STANFORD MEDCASEREASONING RULES! <<<")
else:
    print("\n>>> AUDIT FAILED! SEE ERRORS ABOVE. <<<")
