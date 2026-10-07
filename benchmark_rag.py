import os
import re
import csv
import json
import argparse
import asyncio
import aiohttp
import numpy as np
import torch

# Prevent PyTorch threading conflicts on macOS ARM64
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
torch.set_num_threads(1)

from sentence_transformers import SentenceTransformer
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

# =====================================================================
# BLOCK 1: CLI ARGUMENTS & CONFIGURATION
# =====================================================================
parser = argparse.ArgumentParser(description="Tropical Disease Diagnosis - LightRAG SLM Benchmark")
parser.add_argument(
    "--tier",
    type=int,
    choices=[1, 2],
    default=int(os.getenv("RAG_TIER", "1")),
    help="1: Graph-Only RAG (Entities + Triples), 2: Hybrid RAG (Graph + Text Chunks)"
)
parser.add_argument(
    "--top-chunks",
    type=int,
    default=int(os.getenv("TOP_CHUNKS", "2")),
    help="Number of document chunks to include in Tier 2 (default: 2)"
)
parser.add_argument(
    "--max-relations",
    type=int,
    default=int(os.getenv("MAX_RELATIONS", "30")),
    help="Maximum graph relational triples to inject into prompt (default: 30)"
)
parser.add_argument(
    "--model",
    type=str,
    default=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
    help="Ollama model name (default: qwen2.5:3b)"
)
parser.add_argument(
    "--keyword-mode",
    type=str,
    choices=["ollama", "clues"],
    default=os.getenv("KEYWORD_MODE", "ollama"),
    help="Keyword extraction mode for LightRAG: 'ollama' or 'clues'"
)
parser.add_argument(
    "--max-cases",
    type=int,
    default=int(os.getenv("MAX_TEST_CASES", "0")),
    help="Limit number of test cases (0 = all 365)"
)
parser.add_argument(
    "--output-csv",
    type=str,
    default=os.getenv("OUTPUT_CSV", ""),
    help="Custom path for output CSV"
)

args, _ = parser.parse_known_args()

PROJECT_DIR = "/Users/khoale/Downloads/Project - SLM for Disease Diagnosis"
WORKING_DIR = os.path.join(PROJECT_DIR, "test_kg_output")
TEST_FILE = os.path.join(PROJECT_DIR, "test_masked_cases.jsonl")

TIER = args.tier
TOP_CHUNKS = args.top_chunks
MAX_RELATIONS = args.max_relations
OLLAMA_MODEL = args.model
KEYWORD_MODE = args.keyword_mode
MAX_TEST_CASES = args.max_cases if args.max_cases > 0 else None
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

if args.output_csv:
    OUTPUT_CSV = args.output_csv
else:
    chunk_tag = f"_{TOP_CHUNKS}chunks" if TIER == 2 and TOP_CHUNKS != 2 else ""
    OUTPUT_CSV = os.path.join(
        PROJECT_DIR,
        f"rag_tier{TIER}_{'graph_only' if TIER == 1 else 'hybrid'}{chunk_tag}_results.csv"
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
# BLOCK 3: EMBEDDING FUNCTION & KEYWORD LLM FOR LIGHTRAG
# =====================================================================
embed_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
embed_lock = asyncio.Lock()

async def my_embed_func(texts: list[str], **kwargs) -> np.ndarray:
    async with embed_lock:
        return embed_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=16,
        )

embedding_wrapper = EmbeddingFunc(
    embedding_dim=384,
    func=my_embed_func,
    model_name="all-MiniLM-L6-v2",
)

current_clues = ""

async def keyword_llm_func(prompt: str, **kwargs) -> str:
    """LightRAG calls this function strictly to extract search keywords."""
    if "high_level_keywords" in prompt and "low_level_keywords" in prompt:
        if KEYWORD_MODE == "clues" and current_clues:
            words = [w.strip(".,;:()\"'") for w in current_clues.split() if len(w) > 4]
            selected = list(dict.fromkeys(words))[:8]
            return json.dumps({
                "high_level_keywords": ["infectious disease", "clinical diagnosis"],
                "low_level_keywords": selected
            })
        elif KEYWORD_MODE == "ollama":
            url = "http://127.0.0.1:11434/api/generate"
            payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"}
            try:
                timeout = aiohttp.ClientTimeout(total=45)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=payload) as resp:
                        data = await resp.json()
                        resp_text = data.get("response", "{}")
                        if resp_text and "high_level_keywords" in resp_text:
                            return resp_text
            except Exception:
                pass

            # Fallback to clues if Ollama call fails/times out
            if current_clues:
                words = [w.strip(".,;:()\"'") for w in current_clues.split() if len(w) > 4]
                selected = list(dict.fromkeys(words))[:8]
                return json.dumps({
                    "high_level_keywords": ["infectious disease", "clinical diagnosis"],
                    "low_level_keywords": selected
                })
    return "{}"

# =====================================================================
# BLOCK 4: CONTEXT FORMATTER (GRAPH TRIPLES & CHUNKS)
# =====================================================================
def format_graph_triples(entities: list[dict], relationships: list[dict], max_relations: int = 30) -> str:
    """Formats retrieved entities and relationships into concise clinical facts."""
    lines = []
    
    # 1. Format Key Clinical Entities
    entity_lines = []
    for e in entities[:15]:
        name = e.get("entity_name", "").strip()
        etype = e.get("entity_type", "").strip()
        desc = e.get("description", "").strip()
        # Truncate long descriptions to first sentence
        if "<SEP>" in desc:
            desc = desc.split("<SEP>")[0].strip()
        if len(desc) > 120:
            desc = desc[:117] + "..."
        if name:
            if desc:
                entity_lines.append(f"- {name} [{etype}]: {desc}")
            else:
                entity_lines.append(f"- {name} [{etype}]")
    
    if entity_lines:
        lines.append("Key Medical Entities:")
        lines.extend(entity_lines)
        lines.append("")

    # 2. Format Clinical Relational Triples
    # Prioritize relationships connecting to known candidate diseases or symptoms
    cand_lower = [c.lower() for c in CANDIDATE_DISEASES]
    
    def rel_priority(rel):
        s = rel.get("src_id", "").lower()
        t = rel.get("tgt_id", "").lower()
        score = 0
        if any(c in s or c in t for c in cand_lower):
            score += 2
        if rel.get("description", "").strip():
            score += 1
        return score

    sorted_relations = sorted(relationships, key=rel_priority, reverse=True)
    
    triple_lines = []
    seen_pairs = set()
    for r in sorted_relations:
        src = r.get("src_id", "").strip()
        tgt = r.get("tgt_id", "").strip()
        desc = r.get("description", "").strip()
        
        pair_key = tuple(sorted([src.lower(), tgt.lower()]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)
        
        if "<SEP>" in desc:
            desc = desc.split("<SEP>")[0].strip()
        if len(desc) > 140:
            desc = desc[:137] + "..."
            
        if src and tgt:
            if desc:
                triple_lines.append(f"- ({src}) ──[{desc}]──► ({tgt})")
            else:
                triple_lines.append(f"- ({src}) ◄──► ({tgt})")
                
        if len(triple_lines) >= max_relations:
            break

    if triple_lines:
        lines.append("Clinical Knowledge Triples:")
        lines.extend(triple_lines)
    elif not entity_lines:
        lines.append("No specific graph connections identified.")

    return "\n".join(lines)


def format_chunks(chunks: list[dict], max_chunks: int = 2) -> str:
    """Formats top-N document chunks into clean reference excerpts."""
    chunk_lines = []
    for idx, c in enumerate(chunks[:max_chunks], start=1):
        content = c.get("content", "").strip()
        # Cap chunk length to ~1200 characters to prevent context bloat
        if len(content) > 1200:
            content = content[:1197] + "..."
        chunk_lines.append(f"[Excerpt {idx}]:\n{content}\n")
    return "\n".join(chunk_lines)

# =====================================================================
# BLOCK 5: PROMPT TEMPLATES
# =====================================================================
SYSTEM_PROMPT = """You are an expert Infectious Disease Physician specializing in Tropical Medicine.
Your task is to analyze an admission clinical case presentation where final diagnostic confirmations have been masked.
You are augmented with retrieved medical knowledge graph evidence from a clinical knowledge base.

Synthesize the patient's presentation with the retrieved medical facts to formulate the correct diagnosis.

CONSTRAINTS:
1. You MUST select your primary diagnosis strictly from the provided list of 22 tropical disease candidates.
2. Output ONLY a valid JSON object matching the requested schema. No conversational filler."""

def build_rag_prompt(masked_case_text: str, graph_text: str, chunks_text: str = None) -> str:
    candidates_formatted = "\n".join([f"- {d}" for d in CANDIDATE_DISEASES])
    
    prompt = f"""### CANDIDATE DISEASES LIST (Choose strictly from these 22 options):
{candidates_formatted}

---
### PATIENT CLINICAL PRESENTATION:
{masked_case_text}

---
### RETRIEVED MEDICAL KNOWLEDGE GRAPH EVIDENCE:
{graph_text}
"""

    if chunks_text:
        prompt += f"""
---
### RETRIEVED CLINICAL CASE EXCERPTS:
{chunks_text}
"""

    prompt += """
---
### INSTRUCTIONS & OUTPUT FORMAT:
Identify the single most likely primary diagnosis and up to two differential diagnoses.
Return your response strictly as a JSON object with this exact schema:

{
  "primary_diagnosis": "<Exact disease name from the 22 candidate list>",
  "confidence": "<high | medium | low>",
  "differential_diagnoses": [
    "<Second most likely disease from the candidate list>",
    "<Third most likely disease from the candidate list>"
  ],
  "key_evidence": [
    "<Key clinical findings or graph evidence supporting this decision>"
  ]
}"""
    return prompt

# =====================================================================
# BLOCK 6: EVALUATION & CANONICAL MATCHING
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
    return {"primary_diagnosis": "", "differential_diagnoses": [], "confidence": "unknown"}

# =====================================================================
# BLOCK 7: LLM QUERY VIA OLLAMA
# =====================================================================
async def query_ollama(session: aiohttp.ClientSession, user_prompt: str) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "system": SYSTEM_PROMPT,
        "prompt": user_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0,  # Deterministic greedy decoding
            "num_ctx": int(os.getenv("NUM_CTX", "8192")),
        }
    }
    try:
        async with session.post(OLLAMA_URL, json=payload, timeout=aiohttp.ClientTimeout(total=90)) as resp:
            data = await resp.json()
            raw_response = data.get("response", "{}")
            return clean_json_response(raw_response)
    except Exception as e:
        return {"error": str(e), "primary_diagnosis": "", "differential_diagnoses": []}

# =====================================================================
# BLOCK 8: BENCHMARK EXECUTION PIPELINE
# =====================================================================
async def main():
    tier_name = "TIER 1 (GRAPH-ONLY RAG)" if TIER == 1 else f"TIER 2 (HYBRID RAG: GRAPH + {TOP_CHUNKS} CHUNKS)"
    print(f"\n=============================================================")
    print(f"      {tier_name}")
    print(f"=============================================================")
    print(f"  Model               : {OLLAMA_MODEL}")
    print(f"  Total Cases         : {len(test_cases)}")
    print(f"  Candidate Classes   : {len(CANDIDATE_DISEASES)} tropical diseases")
    print(f"  Keyword Mode        : {KEYWORD_MODE.upper()}")
    print(f"  Max Graph Triples   : {MAX_RELATIONS}")
    if TIER == 2:
        print(f"  Top Chunks Included : {TOP_CHUNKS}")
    print(f"  Output CSV          : {OUTPUT_CSV}")
    print(f"=============================================================\n")

    # Initialize LightRAG
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=keyword_llm_func,
        embedding_func=embedding_wrapper,
        entity_extraction_use_json=True,
        entity_extract_max_gleaning=0,
        chunk_token_size=8192,
        max_parallel_insert=1,
        embedding_func_max_async=1,
        llm_model_max_async=1,
    )

    print("Initializing LightRAG storages...")
    await rag.initialize_storages()
    print("LightRAG storages ready. Commencing benchmark...\n")

    results_log = []
    global current_clues

    async with aiohttp.ClientSession() as session:
        for i, tc in enumerate(test_cases, start=1):
            cid = tc["case_id"]
            masked_text = tc["masked_text"]
            ground_truth = tc["ground_truth"]
            current_clues = tc.get("remaining_clues", "")

            # 1. Retrieve structured data from LightRAG
            param = QueryParam(mode="hybrid", top_k=20)
            try:
                retrieved_res = await rag.aquery_data(masked_text, param=param)
                data_payload = retrieved_res.get("data", {})
                retrieved_entities = data_payload.get("entities", [])
                retrieved_relations = data_payload.get("relationships", [])
                retrieved_chunks = data_payload.get("chunks", [])
            except Exception as e:
                print(f"  [Case {cid}] LightRAG retrieval failed: {e}")
                retrieved_entities, retrieved_relations, retrieved_chunks = [], [], []

            # 2. Format context according to selected Tier
            graph_context_str = format_graph_triples(
                retrieved_entities,
                retrieved_relations,
                max_relations=MAX_RELATIONS
            )

            chunks_context_str = None
            if TIER == 2 and retrieved_chunks:
                chunks_context_str = format_chunks(retrieved_chunks, max_chunks=TOP_CHUNKS)

            # 3. Build diagnostic prompt
            user_prompt = build_rag_prompt(
                masked_case_text=masked_text,
                graph_text=graph_context_str,
                chunks_text=chunks_context_str
            )

            # 4. Query Ollama
            prediction = await query_ollama(session, user_prompt)

            # 5. Evaluate prediction
            eval_metrics = evaluate_prediction(prediction, ground_truth)

            row = {
                "case_id": cid,
                "ground_truth": "|".join(ground_truth),
                "predicted_primary": eval_metrics["predicted_primary"],
                "predicted_diffs": eval_metrics["predicted_diffs"],
                "confidence": eval_metrics["confidence"],
                "top1_acc": eval_metrics["top1_acc"],
                "top3_acc": eval_metrics["top3_acc"],
                "num_entities": len(retrieved_entities),
                "num_relations": len(retrieved_relations),
                "num_chunks": len(retrieved_chunks) if TIER == 2 else 0,
                "raw_response": json.dumps(prediction, ensure_ascii=False),
            }
            results_log.append(row)

            # Progress log every 10 cases (or final)
            if i % 10 == 0 or i == len(test_cases):
                running_top1 = sum(r["top1_acc"] for r in results_log) / len(results_log) * 100
                running_top3 = sum(r["top3_acc"] for r in results_log) / len(results_log) * 100
                print(
                    f"  [{i:>3}/{len(test_cases)}] Case: {cid} | "
                    f"Top-1: {eval_metrics['top1_acc']} (Acc: {running_top1:4.1f}%) | "
                    f"Top-3: {eval_metrics['top3_acc']} (Acc: {running_top3:4.1f}%) | "
                    f"Pred: {eval_metrics['predicted_primary'][:22]}"
                )

    # =====================================================================
    # BLOCK 9: SAVE CSV & SUMMARY REPORT
    # =====================================================================
    fieldnames = [
        "case_id",
        "ground_truth",
        "predicted_primary",
        "predicted_diffs",
        "confidence",
        "top1_acc",
        "top3_acc",
        "num_entities",
        "num_relations",
        "num_chunks",
        "raw_response"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results_log)

    total = len(results_log)
    final_top1 = sum(r["top1_acc"] for r in results_log) / total * 100 if total > 0 else 0
    final_top3 = sum(r["top3_acc"] for r in results_log) / total * 100 if total > 0 else 0

    print("\n" + "=" * 65)
    print(f"         {tier_name} REPORT")
    print("=" * 65)
    print(f"  Model Evaluated             : {OLLAMA_MODEL}")
    print(f"  Total Test Cases Evaluated  : {total}")
    print(f"  Candidate Classes           : 22 Tropical Diseases")
    print(f"  Top-1 Diagnostic Accuracy   : {final_top1:.2f}%")
    print(f"  Top-3 Differential Accuracy : {final_top3:.2f}%")
    print("=" * 65)
    print(f"Detailed per-case results saved to: {OUTPUT_CSV}\n")

if __name__ == "__main__":
    asyncio.run(main())
