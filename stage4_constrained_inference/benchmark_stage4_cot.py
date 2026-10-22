"""
benchmark_stage4_cot.py
Stage 4: Constrained Diagnostic Chain-of-Thought (CoT) Benchmark Runner
========================================================================
Integrates the Dual-Brain Architecture:
1. Semantic Brain: Canonical Knowledge Graph (Stage 1) + Clinical Triple Ranker (Stage 3 Soft-Weighting)
2. Episodic Brain: Vector Case Memory (Stage 2 Patient Precedent Cards)
3. Constrained CoT: Enforces structured differential elimination (differentials -> rule-out -> rule-in -> final_diagnosis)
   on local Ollama (qwen2.5:3b) across all 365 masked admission test cases.

Key Capabilities:
- Instant disk-flush logging to CSV on every completed case.
- Automatic resume capability (skips already evaluated cases).
- Real-time diagnostic accuracy, differential coverage, and attractor monitoring.
"""

import os
import re
import sys
import csv
import json
import time
import argparse
import asyncio
import aiohttp
import numpy as np
# Prevent PyTorch threading conflicts on macOS ARM64
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
try:
    import torch
    torch.set_num_threads(1)
except ImportError:
    pass

# Dynamically resolve project directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE1_DIR = os.path.join(PROJECT_ROOT, "stage1_disease_guides")
STAGE2_DIR = os.path.join(PROJECT_ROOT, "stage2_medcase_distillation")
STAGE3_DIR = os.path.join(PROJECT_ROOT, "stage3_graph_weighting")
STAGE4_DIR = os.path.join(PROJECT_ROOT, "stage4_constrained_inference")

sys.path.insert(0, STAGE2_DIR)
sys.path.insert(0, STAGE3_DIR)

from case_memory_retriever import VectorCaseMemory
from triple_ranker import ClinicalTripleRanker
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

# =====================================================================
# BLOCK 1: CLI ARGUMENTS & CONFIGURATION
# =====================================================================
parser = argparse.ArgumentParser(
    description="Stage 4: Constrained Diagnostic CoT Benchmark for Qwen2.5-3B"
)
parser.add_argument(
    "--model",
    type=str,
    default=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
    help="Ollama model name (default: qwen2.5:3b)"
)
parser.add_argument(
    "--ollama-url",
    type=str,
    default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
    help="Ollama API generate endpoint (default: http://127.0.0.1:11434/api/generate)"
)
parser.add_argument(
    "--max-cases",
    type=int,
    default=int(os.getenv("MAX_TEST_CASES", "0")),
    help="Limit number of test cases for smoke testing (0 = evaluate all 365)"
)
parser.add_argument(
    "--output-csv",
    type=str,
    default=os.path.join(STAGE4_DIR, "stage4_results.csv"),
    help="Path for output results CSV (default: stage4_constrained_inference/stage4_results.csv)"
)
parser.add_argument(
    "--top-k-triples",
    type=int,
    default=15,
    help="Top-k pathognomonic graph triples from Stage 3 ranker (default: 15)"
)
parser.add_argument(
    "--top-k-twins",
    type=int,
    default=2,
    help="Top-k patient precedent twins from Stage 2 memory (default: 2)"
)
parser.add_argument(
    "--min-triple-score",
    type=float,
    default=float(os.getenv("MIN_TRIPLE_SCORE", "2.0")),
    help="Minimum score threshold for Stage 3 graph triples to filter distractors (default: 2.0)"
)
parser.add_argument(
    "--keyword-mode",
    type=str,
    choices=["clues", "ollama"],
    default=os.getenv("KEYWORD_MODE", "clues"),
    help="LightRAG keyword extraction mode: 'clues' (instant, uses case clues) or 'ollama' (calls local LLM)"
)
parser.add_argument(
    "--temperature",
    type=float,
    default=0.0,
    help="Sampling temperature for greedy deterministic decoding (default: 0.0)"
)
parser.add_argument(
    "--num-ctx",
    type=int,
    default=int(os.getenv("NUM_CTX", "8192")),
    help="Context window size (default: 8192)"
)

args, _ = parser.parse_known_args()

MODEL_NAME = args.model
OLLAMA_URL = args.ollama_url
MAX_CASES = args.max_cases if args.max_cases > 0 else None
OUTPUT_CSV = args.output_csv
TOP_K_TRIPLES = args.top_k_triples
TOP_K_TWINS = args.top_k_twins
MIN_TRIPLE_SCORE = args.min_triple_score
KEYWORD_MODE = args.keyword_mode
TEMPERATURE = args.temperature
NUM_CTX = args.num_ctx

CANONICAL_KG_DIR = os.path.join(STAGE1_DIR, "canonical_kg")
_data_test_file = os.path.join(PROJECT_ROOT, "data", "test_masked_cases.jsonl")
TEST_CASES_FILE = os.getenv(
    "TEST_FILE",
    _data_test_file if os.path.exists(_data_test_file) else os.path.join(PROJECT_ROOT, "test_masked_cases.jsonl")
)

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
# BLOCK 2: CONSTRAINED CoT PROMPTING TEMPLATES
# =====================================================================
SYSTEM_PROMPT = """You are an expert Infectious Disease Physician specializing in Tropical and Neglected Diseases.
Your task is to analyze an admission clinical case presentation where final diagnostic tests are masked.
You are equipped with a Dual-Brain Clinical Retrieval System:
1. Historical Clinical Precedents: Closest real-world confirmed cases from episodic patient memory.
2. Canonical Knowledge Graph Evidence: Pathognomonic clinical hallmarks, triage labs, and exclusion rules.

CLINICAL REASONING PROCESS:
1. Cross-examine the Historical Clinical Precedents against the patient's admission presentation and Knowledge Graph anchors.
2. Check which candidate disease accounts for the patient's pathognomonic physical signs, exposure history, and triage lab pattern.
3. Anchor your primary diagnosis and eliminate look-alike alternatives using pertinent negatives.

CONSTRAINTS:
1. You MUST choose your final diagnosis strictly from the 22 canonical tropical disease classes.
2. Place the final_diagnosis at the top of your JSON response to anchor your diagnostic decision firmly.
3. Output strictly a valid JSON object matching the requested schema. No conversational preamble."""

def build_cot_prompt(
    masked_presentation: str,
    graph_triples_context: str,
    patient_twins_context: str
) -> str:
    candidate_list_str = "\n".join([f"- {d}" for d in CANDIDATE_DISEASES])

    prompt = f"""### CANDIDATE DISEASES LIST (Choose strictly from these 22 options):
{candidate_list_str}

---
### PATIENT CLINICAL PRESENTATION (Admission Findings, Diagnostics Masked):
{masked_presentation}

---
{patient_twins_context}

---
### RETRIEVED CANONICAL KNOWLEDGE GRAPH EVIDENCE:
{graph_triples_context}

---
### CLINICAL DIAGNOSTIC DECISION SCHEMA:
Synthesize the clinical presentation with the historical precedents and knowledge graph evidence:
1. matched_precedent: State which Precedent (Precedent 1, Precedent 2, or Neither) best matches the patient presentation.
2. final_diagnosis: Output the exact primary disease name (must strictly be one of the 22 classes).
3. differential_hypotheses: List your top 3 differential candidates [Primary Candidate matching final_diagnosis, Second Candidate, Third Candidate] strictly from the 22 classes.
4. rule_out_rationale: Provide exactly 2 concise sentences:
   - Sentence 1: Rule out Second Candidate citing pertinent negative or mismatched finding.
   - Sentence 2: Rule out Third Candidate citing pertinent negative or mismatched finding.
5. rule_in_anchor: 1 concise sentence anchoring your final diagnosis citing pathognomonic hallmark, cardinal triad, or triage lab pattern.

Expected JSON Schema:
{{
  "matched_precedent": "<Precedent 1 | Precedent 2 | Neither>",
  "final_diagnosis": "<Exact primary disease name strictly from the 22 classes>",
  "differential_hypotheses": [
    "<Primary Candidate matching final_diagnosis>",
    "<Second Candidate from the 22 classes>",
    "<Third Candidate from the 22 classes>"
  ],
  "rule_out_rationale": [
    "Rule out <Second Candidate>: [1 concise sentence citing pertinent negative, lab contradiction, or incubation discrepancy]",
    "Rule out <Third Candidate>: [1 concise sentence citing pertinent negative, lab contradiction, or incubation discrepancy]"
  ],
  "rule_in_anchor": "Anchor <final_diagnosis>: [1 concise sentence citing pathognomonic sign, lab finding, or exposure anchor]"
}}

Return your response strictly as a valid JSON object adhering to this schema."""
    return prompt

# =====================================================================
# BLOCK 3: EVALUATION & CANONICAL MATCHING
# =====================================================================
def canonical_key(term: str) -> str:
    """Deterministic normalizer: lowercase, strip punctuation, remove hyphens."""
    if not term or not isinstance(term, str):
        return ""
    term = term.lower().strip()
    term = term.replace("'s", "").replace("’s", "")
    term = term.replace("-", " ").replace("–", " ")
    term = re.sub(r"[^\w\s]", " ", term)
    return " ".join(term.split())

def clean_json_response(raw_text: str) -> dict:
    """Safely extracts JSON even if LLM surrounds it with markdown codeblocks."""
    raw_text = raw_text.strip()
    try:
        return json.loads(raw_text)
    except Exception:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {
        "matched_precedent": "",
        "final_diagnosis": "",
        "differential_hypotheses": [],
        "rule_out_rationale": [],
        "rule_in_anchor": ""
    }

def evaluate_prediction(pred_data: dict, ground_truth_list: list[str]) -> dict:
    canonical_targets = [canonical_key(t) for t in ground_truth_list if t]

    final_diag = str(pred_data.get("final_diagnosis") or pred_data.get("primary_diagnosis") or "").strip()
    diffs = pred_data.get("differential_hypotheses", [])
    if not isinstance(diffs, list):
        diffs = [str(diffs)]

    canonical_final = canonical_key(final_diag)
    canonical_diffs = [canonical_key(str(d)) for d in diffs if d]

    # Top-1 Accuracy: is final_diagnosis matching ground truth?
    top1_hit = 1 if (canonical_final and any(t in canonical_final or canonical_final in t for t in canonical_targets)) else 0

    # Top-3 Accuracy: is ground truth present in final_diagnosis or differential hypotheses?
    all_candidates = [canonical_final] + canonical_diffs[:3]
    top3_hit = 1 if any(any(t in cand or cand in t for t in canonical_targets) for cand in all_candidates if cand) else 0

    # Attractor trap tracking
    is_melioidosis = 1 if "melioidosis" in canonical_final else 0

    return {
        "predicted_final": final_diag,
        "matched_precedent": str(pred_data.get("matched_precedent", "")),
        "differential_hypotheses": " | ".join(str(d) for d in diffs),
        "rule_out_rationale": " | ".join(str(r) for r in pred_data.get("rule_out_rationale", [])),
        "rule_in_anchor": str(pred_data.get("rule_in_anchor", "")),
        "top1_acc": top1_hit,
        "top3_acc": top3_hit,
        "is_melioidosis": is_melioidosis,
    }

# =====================================================================
# BLOCK 4: OLLAMA QUERY WITH RETRY LOGIC
# =====================================================================
async def query_ollama(session: aiohttp.ClientSession, user_prompt: str, max_retries: int = 2) -> dict:
    payload = {
        "model": MODEL_NAME,
        "system": SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
        }
    }

    for attempt in range(max_retries + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=120)
            async with session.post(OLLAMA_URL, json=payload, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw_resp = data.get("response", "{}")
                    return clean_json_response(raw_resp)
                else:
                    await asyncio.sleep(2 ** attempt)
        except Exception as e:
            if attempt == max_retries:
                return {
                    "error": str(e),
                    "differential_hypotheses": [],
                    "rule_out_rationale": [],
                    "rule_in_anchor": "",
                    "final_diagnosis": ""
                }
            await asyncio.sleep(2 ** attempt)

    return {
        "differential_hypotheses": [],
        "rule_out_rationale": [],
        "rule_in_anchor": "",
        "final_diagnosis": ""
    }

# =====================================================================
# BLOCK 5: MAIN BENCHMARK EXECUTION PIPELINE
# =====================================================================
async def main():
    print("=" * 75)
    print("STAGE 4: DUAL-BRAIN CONSTRAINED DIAGNOSTIC CoT BENCHMARK")
    print("=" * 75)
    print(f"  Model               : {MODEL_NAME}")
    print(f"  Ollama URL          : {OLLAMA_URL}")
    print(f"  Keyword Mode        : {KEYWORD_MODE.upper()}")
    print(f"  Max Graph Triples   : {TOP_K_TRIPLES}")
    print(f"  Max Patient Twins   : {TOP_K_TWINS}")
    print(f"  Output CSV          : {OUTPUT_CSV}")
    print(f"  Canonical KG Dir    : {CANONICAL_KG_DIR}")
    print("=" * 75)

    # 1. Load Masked Test Cases
    assert os.path.exists(TEST_CASES_FILE), f"Test cases file not found: {TEST_CASES_FILE}"
    test_cases = []
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_cases.append(json.loads(line))

    if MAX_CASES:
        test_cases = test_cases[:MAX_CASES]
        print(f"Smoke test mode: Evaluating first {len(test_cases)} case(s).\n")
    else:
        print(f"Loaded full cohort of {len(test_cases)} masked admission cases.\n")

    # 2. Initialize Stage 2 Vector Case Memory (Episodic Brain)
    print("--> Initializing Stage 2 Vector Case Memory...")
    case_memory = VectorCaseMemory()

    # 3. Initialize Stage 3 Clinical Triple Ranker (Soft Weight Discounting)
    print("--> Initializing Stage 3 Clinical Triple Ranker...")
    triple_ranker = ClinicalTripleRanker()

    # 4. Initialize LightRAG on Stage 1 Canonical KG (Sharing embedding model)
    print("--> Initializing LightRAG on Stage 1 Canonical Knowledge Graph...")
    embed_lock = asyncio.Lock()

    async def shared_embed_func(texts: list[str], **kwargs) -> np.ndarray:
        async with embed_lock:
            return case_memory.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=16
            )

    embedding_wrapper = EmbeddingFunc(
        embedding_dim=768,
        func=shared_embed_func,
        model_name="NeuML/pubmedbert-base-embeddings"
    )

    current_case_clues = ""
    current_twin_diseases = []

    CLINICAL_STOPWORDS = {
        "young", "female", "male", "patient", "presenting", "history", "with", "from",
        "area", "endemic", "rural", "urban", "year", "old", "adult", "child", "infant",
        "months", "days", "weeks", "hospital", "admission", "following", "known", "contact",
        "that", "this", "have", "been", "were", "after", "which", "also", "there", "their",
        "month", "mother", "father", "resident", "returning", "traveled", "traveler",
        "western", "eastern", "southern", "northern"
    }

    def extract_syndrome_anchor(clues_text: str) -> str:
        tokens = re.findall(r"\b[a-zA-Z]{4,}\b", clues_text.lower())
        salient = [t for t in tokens if t not in CLINICAL_STOPWORDS]
        return " ".join(salient[:3]) if salient else ""

    async def keyword_llm_func(prompt: str, **kwargs) -> str:
        """LightRAG calls this function strictly to extract search keywords."""
        if "high_level_keywords" in prompt and "low_level_keywords" in prompt:
            # 1. Twin disease candidates from episodic memory
            hl_keywords = [d for d in current_twin_diseases if d]
            
            # 2. Case syndromic anchor from actual presentation clues (Hybrid Strategy)
            if current_case_clues:
                syndrome_anchor = extract_syndrome_anchor(current_case_clues)
                if syndrome_anchor and syndrome_anchor not in hl_keywords:
                    hl_keywords.append(syndrome_anchor)

            hl_keywords = list(dict.fromkeys(hl_keywords))
            if not hl_keywords:
                hl_keywords = ["infectious disease", "tropical infection"]

            if KEYWORD_MODE == "clues" and current_case_clues:
                words = [w.strip(".,;:()\"'") for w in current_case_clues.split() if len(w) > 4]
                selected = list(dict.fromkeys(words))[:8]
                return json.dumps({
                    "high_level_keywords": hl_keywords,
                    "low_level_keywords": selected
                })
            elif KEYWORD_MODE == "ollama":
                payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False, "format": "json"}
                try:
                    timeout = aiohttp.ClientTimeout(total=45)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.post(OLLAMA_URL, json=payload) as resp:
                            data = await resp.json()
                            resp_text = data.get("response", "{}")
                            if resp_text and "high_level_keywords" in resp_text:
                                parsed = json.loads(resp_text)
                                combined_hl = list(dict.fromkeys(hl_keywords + parsed.get("high_level_keywords", [])))
                                parsed["high_level_keywords"] = combined_hl
                                return json.dumps(parsed)
                except Exception:
                    pass

                # Fallback to clues if Ollama keyword call times out
                if current_case_clues:
                    words = [w.strip(".,;:()\"'") for w in current_case_clues.split() if len(w) > 4]
                    selected = list(dict.fromkeys(words))[:8]
                    return json.dumps({
                        "high_level_keywords": hl_keywords,
                        "low_level_keywords": selected
                    })
                return json.dumps({
                    "high_level_keywords": hl_keywords,
                    "low_level_keywords": []
                })
        return "{}"

    rag = LightRAG(
        working_dir=CANONICAL_KG_DIR,
        llm_model_func=keyword_llm_func,
        embedding_func=embedding_wrapper,
        entity_extraction_use_json=True,
        entity_extract_max_gleaning=0,
        chunk_token_size=8192,
        max_parallel_insert=1,
        embedding_func_max_async=1,
        llm_model_max_async=1,
        enable_llm_cache=False,
    )
    await rag.initialize_storages()
    print("LightRAG storages initialized. Ready for benchmark execution!\n")

    # 5. Checkpoint & Auto-Resume Setup
    completed_case_ids = set()
    results_log = []

    fieldnames = [
        "case_id",
        "ground_truth",
        "predicted_final",
        "differential_hypotheses",
        "rule_out_rationale",
        "rule_in_anchor",
        "top1_acc",
        "top3_acc",
        "is_melioidosis",
        "num_graph_triples",
        "num_patient_twins",
        "raw_response",
    ]

    if os.path.exists(OUTPUT_CSV):
        try:
            with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    completed_case_ids.add(row["case_id"])
                    row["top1_acc"] = int(row.get("top1_acc", 0))
                    row["top3_acc"] = int(row.get("top3_acc", 0))
                    row["is_melioidosis"] = int(row.get("is_melioidosis", 0))
                    results_log.append(row)
            if completed_case_ids:
                print(f"--> [AUTO-RESUME] Found existing CSV with {len(completed_case_ids)} completed case(s).")
                print(f"    Resuming from case {len(completed_case_ids) + 1}...\n")
        except Exception as e:
            print(f"Warning reading existing CSV: {e}")

    # Write CSV header if file doesn't exist
    if not os.path.exists(OUTPUT_CSV) or len(completed_case_ids) == 0:
        os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    # 6. Evaluation Loop
    async with aiohttp.ClientSession() as session:
        for i, tc in enumerate(test_cases, start=1):
            cid = tc["case_id"]

            # Skip completed cases for auto-resume
            if cid in completed_case_ids:
                continue

            masked_text = tc["masked_text"]
            ground_truth = tc["ground_truth"]
            current_case_clues = tc.get("remaining_clues", "")

            # A. Retrieve Top-k Patient Twins from Stage 2 Vector Memory (Episodic Brain)
            # Fast cosine similarity (<2ms) identifies the top twin precedent diseases to guide semantic graph search
            twins = case_memory.retrieve(masked_text, top_k=TOP_K_TWINS)
            current_twin_diseases.clear()
            current_twin_diseases.extend(list(dict.fromkeys([t["disease"] for t in twins if t.get("disease")])))
            patient_twins_str = case_memory.format_precedent_cards(
                masked_text,
                top_k=TOP_K_TWINS
            )

            # B. Retrieve from LightRAG Canonical KG (guided by twin disease hypotheses)
            param = QueryParam(mode="hybrid", top_k=25)
            try:
                retrieved_res = await rag.aquery_data(masked_text, param=param)
                data_payload = retrieved_res.get("data", {})
                retrieved_relations = data_payload.get("relationships", [])
            except Exception as e:
                print(f"  [Case {cid}] LightRAG retrieval exception: {e}")
                retrieved_relations = []

            # C. Format candidate triples for Stage 3 Ranker
            candidate_triples = []
            for r in retrieved_relations:
                desc = r.get("description", "").strip()
                rel = "associated_with"
                if desc.startswith("[") and "]" in desc:
                    rel = desc[1:desc.index("]")]
                    desc = desc[desc.index("]") + 1:].strip()
                candidate_triples.append({
                    "source": r.get("src_id", ""),
                    "relation": rel,
                    "target": r.get("tgt_id", ""),
                    "description": desc,
                    "weight": float(r.get("weight", 1.0))
                })

            graph_context_str = triple_ranker.format_triples_for_prompt(
                candidate_triples,
                patient_text=masked_text,
                top_k=TOP_K_TRIPLES,
                min_score=MIN_TRIPLE_SCORE
            )

            # D. Synthesize Constrained CoT Prompt
            user_prompt = build_cot_prompt(
                masked_presentation=masked_text,
                graph_triples_context=graph_context_str,
                patient_twins_context=patient_twins_str
            )

            # E. Query Ollama (qwen2.5:3b)
            pred_json = await query_ollama(session, user_prompt)

            # F. Evaluate Prediction
            eval_metrics = evaluate_prediction(pred_json, ground_truth)

            row = {
                "case_id": cid,
                "ground_truth": "|".join(ground_truth),
                "predicted_final": eval_metrics["predicted_final"],
                "differential_hypotheses": eval_metrics["differential_hypotheses"],
                "rule_out_rationale": eval_metrics["rule_out_rationale"],
                "rule_in_anchor": eval_metrics["rule_in_anchor"],
                "top1_acc": eval_metrics["top1_acc"],
                "top3_acc": eval_metrics["top3_acc"],
                "is_melioidosis": eval_metrics["is_melioidosis"],
                "num_graph_triples": len(candidate_triples),
                "num_patient_twins": TOP_K_TWINS,
                "raw_response": json.dumps(pred_json, ensure_ascii=False),
            }
            results_log.append(row)
            completed_case_ids.add(cid)

            # G. Instant Disk Flush (Crash-proof)
            with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(row)
                f.flush()

            # H. Real-time Progress Output
            total_done = len(results_log)
            running_top1 = sum(int(r["top1_acc"]) for r in results_log) / total_done * 100
            running_top3 = sum(int(r["top3_acc"]) for r in results_log) / total_done * 100
            running_melioidosis = sum(int(r["is_melioidosis"]) for r in results_log) / total_done * 100

            print(
                f"  [{total_done:>3}/{len(test_cases)}] Case: {cid} | "
                f"Top-1: {eval_metrics['top1_acc']} (Acc: {running_top1:4.1f}%) | "
                f"Top-3: {eval_metrics['top3_acc']} (Cov: {running_top3:4.1f}%) | "
                f"Melioidosis: {eval_metrics['is_melioidosis']} ({running_melioidosis:4.1f}%) | "
                f"Pred: {eval_metrics['predicted_final'][:18]:<18} | "
                f"True: {ground_truth[0][:18]}"
            )

    # =====================================================================
    # BLOCK 6: FINAL MASTER REPORT
    # =====================================================================
    total = len(results_log)
    if total > 0:
        final_top1 = sum(int(r["top1_acc"]) for r in results_log) / total * 100
        final_top3 = sum(int(r["top3_acc"]) for r in results_log) / total * 100
        final_melio = sum(int(r["is_melioidosis"]) for r in results_log) / total * 100

        print("\n" + "=" * 70)
        print("          STAGE 4 DUAL-BRAIN CoT BENCHMARK REPORT")
        print("=" * 70)
        print(f"  Model Evaluated             : {MODEL_NAME}")
        print(f"  Total Test Cases Evaluated  : {total}")
        print(f"  Top-1 Diagnostic Accuracy   : {final_top1:.2f}%")
        print(f"  Top-3 Differential Coverage : {final_top3:.2f}%")
        print(f"  Melioidosis Attractor Rate  : {final_melio:.2f}% (Baseline was 55.34%)")
        print("=" * 70)
        print(f"  Results saved to: {OUTPUT_CSV}\n")

if __name__ == "__main__":
    asyncio.run(main())
