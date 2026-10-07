import os
import json
import csv
import aiohttp
import asyncio

# =====================================================================
# BLOCK 1: PATHS & CONFIGURATION
# =====================================================================
PROJECT_DIR = "/Users/khoale/Downloads/Project - SLM for Disease Diagnosis"
TEST_FILE = os.path.join(PROJECT_DIR, "test_masked_cases.jsonl")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", os.path.join(PROJECT_DIR, "baseline_results.csv"))

# Model configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Set MAX_TEST_CASES = None to run all 365 cases, or integer (e.g. 5) for quick trial
MAX_TEST_CASES = int(os.getenv("MAX_TEST_CASES", "0")) or None

# The 22 Canonical Tropical Disease Classes
CANDIDATE_DISEASES = [
    "Amebiasis",
    "Cholera",
    "Dengue",
    "Echinococcosis",
    "Foodborne Trematodes",
    "Leishmaniasis",
    "Leprosy",
    "Leptospirosis",
    "Malaria",
    "Melioidosis",
    "Mycetoma",
    "Neurocysticercosis",
    "Paracoccidioidomycosis",
    "Scabies",
    "Schistosomiasis",
    "Scrub Typhus",
    "Soil-Transmitted Helminths",
    "Talaromycosis",
    "Trypanosomiasis",
    "Tuberculosis",
    "Viral Hemorrhagic Fevers",
    "Zika Virus",
]

# =====================================================================
# BLOCK 2: LOAD DATA
# =====================================================================
print(f"Loading masked test cases from: {TEST_FILE}")
test_cases = []
with open(TEST_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            test_cases.append(json.loads(line))

if MAX_TEST_CASES:
    test_cases = test_cases[:MAX_TEST_CASES]
    print(f"Running on first {len(test_cases)} cases (test trial).")
else:
    print(f"Loaded {len(test_cases)} test cases.")

# =====================================================================
# BLOCK 3: PROMPT TEMPLATES
# =====================================================================
SYSTEM_PROMPT = """You are an expert Infectious Disease Physician specializing in Tropical Medicine.
Your task is to analyze an admission clinical case presentation where final diagnostic confirmations have been masked.

Based solely on the patient's symptoms, physical examination findings, exposure history, vital signs, and preliminary laboratory/imaging results, formulate a clinical diagnosis.

CONSTRAINTS:
1. You MUST select your primary diagnosis strictly from the provided list of 22 tropical disease candidates.
2. Output ONLY a valid JSON object matching the requested schema. No conversational filler."""

def build_user_prompt(masked_case_text: str) -> str:
    candidates_formatted = "\n".join([f"- {d}" for d in CANDIDATE_DISEASES])
    return f"""### CANDIDATE DISEASES LIST (Choose strictly from these 22 options):
{candidates_formatted}

---
### PATIENT CLINICAL PRESENTATION:
{masked_case_text}

---
### INSTRUCTIONS & OUTPUT FORMAT:
Identify the single most likely primary diagnosis and up to two differential diagnoses.
Return your response strictly as a JSON object with this exact schema:

{{
  "primary_diagnosis": "<Exact disease name from the 22 candidate list>",
  "confidence": "<high | medium | low>",
  "differential_diagnoses": [
    "<Second most likely disease from the candidate list>",
    "<Third most likely disease from the candidate list>"
  ],
  "key_clinical_clues": [
    "<Key clinical findings that led to this decision>"
  ]
}}"""

# =====================================================================
# BLOCK 4: EVALUATION & CANONICAL MATCHING
# =====================================================================
def canonical_key(term: str) -> str:
    """Deterministic normalizer: lowercase, strip punctuation, remove hyphens."""
    if not term or not isinstance(term, str):
        return ""
    term = term.lower().strip()
    term = term.replace("'s", "").replace("’s", "")
    term = term.replace("-", "").replace("–", "")
    return " ".join(term.split())

def evaluate_prediction(pred_data: dict, ground_truth_list: list[str]):
    canonical_targets = [canonical_key(t) for t in ground_truth_list if t]
    
    primary = pred_data.get("primary_diagnosis", "")
    diffs = pred_data.get("differential_diagnoses", [])
    if not isinstance(diffs, list):
        diffs = []
        
    canonical_primary = canonical_key(primary)
    canonical_diffs = [canonical_key(d) for d in diffs if d]

    # Top-1 Accuracy: is primary diagnosis in ground truth?
    top1_hit = 1 if any(t in canonical_primary or canonical_primary in t for t in canonical_targets) else 0

    # Top-3 Accuracy: is ground truth in primary + differentials?
    all_top3 = [canonical_primary] + canonical_diffs[:2]
    top3_hit = 1 if any(any(t in cand or cand in t for t in canonical_targets) for cand in all_top3 if cand) else 0

    return {
        "predicted_primary": primary,
        "predicted_diffs": " | ".join(diffs[:2]),
        "confidence": pred_data.get("confidence", "unknown"),
        "top1_acc": top1_hit,
        "top3_acc": top3_hit,
    }

# =====================================================================
# BLOCK 5: LLM QUERY & EXECUTION PIPELINE
# =====================================================================
async def query_ollama(session: aiohttp.ClientSession, masked_text: str) -> dict:
    prompt = build_user_prompt(masked_text)
    payload = {
        "model": OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0,  # Deterministic greedy decoding
        }
    }
    try:
        async with session.post(OLLAMA_URL, json=payload, timeout=aiohttp.ClientTimeout(total=90)) as resp:
            data = await resp.json()
            raw_response = data.get("response", "{}")
            return json.loads(raw_response)
    except Exception as e:
        return {"error": str(e), "primary_diagnosis": "", "differential_diagnoses": []}

async def main():
    print(f"\n=============================================================")
    print(f"      ZERO-SHOT BASELINE DIAGNOSTIC BENCHMARK")
    print(f"=============================================================")
    print(f"  Model              : {OLLAMA_MODEL}")
    print(f"  Total Cases        : {len(test_cases)}")
    print(f"  Candidate Classes  : {len(CANDIDATE_DISEASES)} tropical diseases")
    print(f"  Output CSV         : {OUTPUT_CSV}")
    print(f"=============================================================\n")

    results_log = []
    
    async with aiohttp.ClientSession() as session:
        for i, tc in enumerate(test_cases, start=1):
            cid = tc["case_id"]
            masked_text = tc["masked_text"]
            ground_truth = tc["ground_truth"]

            # Query the model
            prediction = await query_ollama(session, masked_text)

            # Evaluate prediction
            eval_metrics = evaluate_prediction(prediction, ground_truth)
            
            row = {
                "case_id": cid,
                "ground_truth": "|".join(ground_truth),
                **eval_metrics,
                "raw_response": json.dumps(prediction, ensure_ascii=False)
            }
            results_log.append(row)

            # Progress log every 10 cases
            if i % 10 == 0 or i == len(test_cases):
                print(f"  Processed [{i:>3}/{len(test_cases)}] | Case: {cid} | Top-1: {eval_metrics['top1_acc']} | Pred: {eval_metrics['predicted_primary'][:25]}")

    # =====================================================================
    # BLOCK 6: SAVE CSV & SUMMARY REPORT
    # =====================================================================
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["case_id", "ground_truth", "predicted_primary", "predicted_diffs", "confidence", "top1_acc", "top3_acc", "raw_response"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results_log)

    total = len(results_log)
    top1_rate = sum(r["top1_acc"] for r in results_log) / total * 100
    top3_rate = sum(r["top3_acc"] for r in results_log) / total * 100

    print("\n" + "=" * 65)
    print("         ZERO-SHOT BASELINE BENCHMARK REPORT")
    print("=" * 65)
    print(f"  Model Evaluated             : {OLLAMA_MODEL} (Zero-Shot / No-RAG)")
    print(f"  Total Test Cases Evaluated  : {total}")
    print(f"  Candidate Classes           : 22 Tropical Diseases")
    print(f"  Top-1 Diagnostic Accuracy   : {top1_rate:.2f}%")
    print(f"  Top-3 Differential Accuracy : {top3_rate:.2f}%")
    print("=" * 65)
    print(f"Detailed per-case results saved to: {OUTPUT_CSV}\n")

if __name__ == "__main__":
    asyncio.run(main())
