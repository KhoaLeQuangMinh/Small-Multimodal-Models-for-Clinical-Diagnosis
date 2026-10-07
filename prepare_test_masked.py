import json
import os

# =====================================================================
# PATHS
# =====================================================================
PROJECT_DIR = "/Users/khoale/Downloads/Project - SLM for Disease Diagnosis"
PART_A_MASKED_FILE = os.path.join(PROJECT_DIR, "partA_masked.jsonl")
TEST_CASES_FILE = os.path.join(PROJECT_DIR, "test_cases.jsonl")
OUTPUT_FILE = os.path.join(PROJECT_DIR, "test_masked_cases.jsonl")

# =====================================================================
# EXTRACTION & MERGE LOGIC
# =====================================================================
print(f"Loading masked dataset from: {PART_A_MASKED_FILE}")
masked_lookup = {}
with open(PART_A_MASKED_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            item = json.loads(line)
            masked_lookup[item["case_id"]] = item

print(f"Loading test split from: {TEST_CASES_FILE}")
test_cases = []
with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            test_cases.append(json.loads(line))

extracted_records = []
skipped = 0

for tc in test_cases:
    cid = tc["case_id"]
    if cid not in masked_lookup:
        skipped += 1
        continue

    m_data = masked_lookup[cid]
    text_b = m_data.get("text_b", "").strip()
    present = tc.get("present", [])
    candidates = list(tc.get("candidates", {}).keys())
    remaining_clues = m_data.get("remaining_clues", "").strip()

    # Skip cases without a verified ground-truth diagnosis
    if not text_b or not present or not candidates:
        skipped += 1
        continue

    record = {
        "case_id": cid,
        "masked_text": text_b,
        "ground_truth": present,
        "candidates": candidates,
        "remaining_clues": remaining_clues,
    }
    extracted_records.append(record)

# =====================================================================
# SAVE OUTPUT
# =====================================================================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for rec in extracted_records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

print(f"Extraction complete!")
print(f"  Total test cases evaluated : {len(test_cases)}")
print(f"  Valid complete masked cases: {len(extracted_records)}")
print(f"  Skipped (no ground-truth)  : {skipped}")
print(f"  Saved output to            : {OUTPUT_FILE}")
