import json
import os
import re

folder = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(folder, "batch_meta.json")) as f:
    meta = json.load(f)

cases = meta["cases"]
all_ok = True

print(f"Total cases in metadata: {len(cases)}")

forbidden_words_by_case = {
    "Tuberculosis": ["tuberculosis", "tuberculoma", "mycobacterium", "tb", "antituberculous"],
    "Malaria": ["malaria", "plasmodium", "falciparum"],
    "Neurocysticercosis": ["cysticercosis", "cysticercus", "taenia", "solium"],
    "Schistosomiasis": ["schistosoma", "schistosomiasis", "bilharzia"],
    "Echinococcosis": ["echinococcus", "echinococcal", "hydatid"],
    "Foodborne Trematodes": ["trematode", "fasciola", "fascioliasis", "fluke"]
}

for c in cases:
    cid = c["case_id"]
    target_dis = c["target_disease"]
    d_filename = c["distilled_output_file"]
    c_filename = c["case_file"]
    
    d_path = os.path.join(folder, d_filename)
    c_path = os.path.join(folder, c_filename)
    
    if not os.path.exists(d_path):
        print(f"FAIL: {d_filename} does not exist!")
        all_ok = False
        continue
        
    with open(d_path) as f:
        distilled = json.load(f)
    with open(c_path) as f:
        orig = json.load(f)
        
    orig_text = orig["case_text"]
    
    # Check fields
    required_keys = ["case_id", "disease", "think", "case_prompt", "diagnostic_reasoning", "final_diagnosis", "audit_flags", "editor_comments"]
    for k in required_keys:
        if k not in distilled:
            print(f"FAIL: {cid} missing key {k}")
            all_ok = False
            
    val_cid = distilled.get("case_id")
    if val_cid != cid:
        print(f"FAIL: {cid} case_id mismatch: {val_cid}")
        all_ok = False
        
    val_dis = distilled.get("disease")
    if val_dis != target_dis:
        print(f"FAIL: {cid} disease mismatch: {val_dis} vs {target_dis}")
        all_ok = False
        
    val_final = distilled.get("final_diagnosis")
    if val_final != target_dis:
        print(f"FAIL: {cid} final_diagnosis mismatch: {val_final} vs {target_dis}")
        all_ok = False
        
    val_flags = distilled.get("audit_flags")
    if val_flags != ["NONE"]:
        print(f"FAIL: {cid} audit_flags: {val_flags}")
        all_ok = False
        
    # Check case_prompt for spoilers
    prompt = distilled.get("case_prompt", "").lower()
    for word in forbidden_words_by_case.get(target_dis, []):
        matches = re.findall(rf"\b{word}\b", prompt)
        if matches:
            print(f"WARNING: {cid} prompt contains forbidden word '{word}': {matches}")
            all_ok = False

    # Check quotes
    d_reasoning = distilled.get("diagnostic_reasoning", [])
    if not isinstance(d_reasoning, list) or len(d_reasoning) < 2:
        print(f"FAIL: {cid} diagnostic_reasoning format invalid")
        all_ok = False
    for i, r in enumerate(d_reasoning):
        q = r.get("quote", "")
        snippets = [s.strip(" \"\n\t") for s in q.split("...") if len(s.strip(" \"\n\t")) > 5]
        for s in snippets:
            s_clean = " ".join(s.split())
            orig_clean = " ".join(orig_text.split())
            if s_clean not in orig_clean:
                print(f"WARNING: {cid} reason {i} snippet not in orig text: '{s_clean[:40]}...'")
                all_ok = False

if all_ok:
    print("ALL 10 CASES VERIFIED PERFECTLY!")
