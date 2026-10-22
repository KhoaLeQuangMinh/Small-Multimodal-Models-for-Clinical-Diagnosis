import json
import os

# =====================================================================
# PATHS
# =====================================================================
BENCHMARK_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BENCHMARK_DIR, ".."))
PROJECT_DIR = PROJECT_ROOT
PART_A_MASKED_FILE = os.getenv("PART_A_MASKED_FILE", os.path.join(PROJECT_ROOT, "partA_masked.jsonl"))
TEST_CASES_FILE = os.getenv("TEST_CASES_FILE", os.path.join(PROJECT_ROOT, "test_cases.jsonl"))
OUTPUT_FILE = os.getenv("OUTPUT_FILE", os.path.join(PROJECT_ROOT, "data", "test_masked_cases.jsonl"))

# =====================================================================
# EXTRACTION & MERGE LOGIC
# =====================================================================
CANONICAL_22_DISEASES = [
    "Amebiasis", "Cholera", "Dengue", "Echinococcosis", "Foodborne Trematodes",
    "Leishmaniasis", "Leprosy", "Leptospirosis", "Malaria", "Melioidosis",
    "Mycetoma", "Neurocysticercosis", "Paracoccidioidomycosis", "Scabies",
    "Schistosomiasis", "Scrub Typhus", "Soil-Transmitted Helminths", "Talaromycosis",
    "Trypanosomiasis", "Tuberculosis", "Viral Hemorrhagic Fevers", "Zika Virus"
]

def main():
    extracted_records = []
    skipped = 0

    if os.path.exists(PART_A_MASKED_FILE) and os.path.exists(TEST_CASES_FILE):
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
    else:
        import csv, sys
        pipeline_dir = os.path.join(PROJECT_DIR, "data_pipeline", "llm")
        if pipeline_dir not in sys.path:
            sys.path.insert(0, pipeline_dir)
        try:
            from mask_regex import mask_terms
        except ImportError:
            def mask_terms(t): return t

        csv_candidates = [
            os.path.join(BENCHMARK_DIR, "results", "rag_tier1_graph_only_results.csv"),
            os.path.join(BENCHMARK_DIR, "results", "rag_tier2_hybrid_results.csv"),
            os.path.join(BENCHMARK_DIR, "results", "baseline_results.csv"),
            os.path.join(PROJECT_ROOT, "rag_tier1_graph_only_results.csv"),
            os.path.join(PROJECT_ROOT, "rag_tier2_hybrid_results.csv"),
            os.path.join(PROJECT_ROOT, "baseline_results.csv")
        ]
        benchmark_csv = next((p for p in csv_candidates if os.path.exists(p)), None)
        if not benchmark_csv:
            raise FileNotFoundError("Cannot prepare test cases: neither partA_masked.jsonl nor benchmark CSV found.")

        print(f"Extracting 365 test cohort ground truths from: {benchmark_csv}")
        test_meta = {}
        with open(benchmark_csv, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                test_meta[row["case_id"]] = row["ground_truth"]

        gold_path = os.path.join(PROJECT_DIR, "Custom_Tropical_Project", "2_Clinical_Verification", "dataset_gold_1236.jsonl")
        gold_lookup = {}
        if os.path.exists(gold_path):
            with open(gold_path, "r", encoding="utf-8") as f:
                for line in f:
                    d = json.loads(line)
                    cid = d.get("case_id")
                    if cid in test_meta:
                        gold_lookup[cid] = d.get("triage_prompt", "")

        missing_cids = [cid for cid in test_meta if cid not in gold_lookup]
        parquet_lookup = {}
        if missing_cids:
            parquet_path = os.path.join(PROJECT_DIR, "Official_MultiCaRe", "whole_multicare_dataset", "cases.parquet")
            if os.path.exists(parquet_path):
                try:
                    import pyarrow.parquet as pq
                    table = pq.read_table(parquet_path, columns=["article_id", "cases"])
                    for row in table.to_pylist():
                        for c in (row.get("cases") or []):
                            cid = c.get("case_id")
                            if cid in missing_cids:
                                parquet_lookup[cid] = c.get("case_text", "")
                except ImportError:
                    print("Warning: pyarrow is not installed (run with .venv/bin/python or pip install pyarrow); skipping parquet fallback lookup.", file=sys.stderr)

        for cid, ground_truth in test_meta.items():
            raw_text = gold_lookup.get(cid) or parquet_lookup.get(cid, "")
            if not raw_text:
                skipped += 1
                continue
            masked = mask_terms(raw_text)
            extracted_records.append({
                "case_id": cid,
                "masked_text": masked,
                "ground_truth": [ground_truth] if isinstance(ground_truth, str) else ground_truth,
                "candidates": CANONICAL_22_DISEASES,
                "remaining_clues": "",
            })

    # =====================================================================
    # SAVE OUTPUT
    # =====================================================================
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for rec in extracted_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Extraction complete!")
    print(f"  Total test cases evaluated : {len(extracted_records) + skipped}")
    print(f"  Valid complete masked cases: {len(extracted_records)}")
    print(f"  Skipped (no ground-truth)  : {skipped}")
    print(f"  Saved output to            : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
