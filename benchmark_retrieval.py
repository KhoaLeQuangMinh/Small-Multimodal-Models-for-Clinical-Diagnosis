import os
import re
import csv
import json
import asyncio
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
# BLOCK 1: PATHS & CONFIGURATION
# =====================================================================
PROJECT_DIR = "/Users/khoale/Downloads/Project - SLM for Disease Diagnosis"
WORKING_DIR = os.path.join(PROJECT_DIR, "test_kg_output")
TEST_FILE = os.path.join(PROJECT_DIR, "test_masked_cases.jsonl")
# Keyword extraction mode:
#   "clues"  : Uses the case's remaining clinical clues (instant, offline, no GPU/Ollama needed)
#   "ollama" : Queries local Ollama model (e.g. qwen2.5:3b)
KEYWORD_MODE = os.getenv("KEYWORD_MODE", "clues")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

OUTPUT_CSV = os.getenv(
    "OUTPUT_CSV",
    os.path.join(
        PROJECT_DIR,
        f"retrieval_benchmark_{KEYWORD_MODE}_results.csv" if KEYWORD_MODE != "clues" else "retrieval_benchmark_results.csv"
    )
)

# Set MAX_TEST_CASES = None to run all 365 cases, or an integer (e.g. 5) for a quick trial
MAX_TEST_CASES = int(os.getenv("MAX_TEST_CASES", "0")) or None

# =====================================================================
# BLOCK 2: LOAD DATA
# =====================================================================
print(f"Loading test cases from: {TEST_FILE}")
test_cases = []
with open(TEST_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            test_cases.append(json.loads(line))

if MAX_TEST_CASES:
    test_cases = test_cases[:MAX_TEST_CASES]
    print(f"Running on first {len(test_cases)} cases (test run).")
else:
    print(f"Loaded {len(test_cases)} test cases.")

# =====================================================================
# BLOCK 3: EMBEDDING FUNCTION (384-DIM all-MiniLM-L6-v2)
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

# =====================================================================
# BLOCK 4: LIGHTRAG KEYWORD LLM HANDLER
# =====================================================================
current_clues = ""

async def keyword_llm_func(prompt: str, **kwargs) -> str:
    """LightRAG calls this function only to extract search keywords."""
    if "high_level_keywords" in prompt and "low_level_keywords" in prompt:
        if KEYWORD_MODE == "clues" and current_clues:
            # Extract clinical keywords directly from the remaining clues
            words = [w.strip(".,;:()\"'") for w in current_clues.split() if len(w) > 4]
            selected = list(dict.fromkeys(words))[:8]
            return json.dumps({
                "high_level_keywords": ["infectious disease", "clinical diagnosis"],
                "low_level_keywords": selected
            })
        elif KEYWORD_MODE == "ollama":
            import aiohttp
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
            except Exception as e:
                pass

            # Graceful fallback to clinical clues if Ollama call fails/times out
            if current_clues:
                words = [w.strip(".,;:()\"'") for w in current_clues.split() if len(w) > 4]
                selected = list(dict.fromkeys(words))[:8]
                return json.dumps({
                    "high_level_keywords": ["infectious disease", "clinical diagnosis"],
                    "low_level_keywords": selected
                })
    return "{}"

# =====================================================================
# BLOCK 5: DETERMINISTIC EVALUATION METRICS
# =====================================================================
def canonical_key(term: str) -> str:
    """Deterministic normalizer: lowercase, strip punctuation, remove hyphens."""
    term = term.lower().strip()
    term = term.replace("'s", "").replace("’s", "")
    term = term.replace("-", "").replace("–", "")
    return " ".join(term.split())

def parse_retrieved_context(context_text: str):
    """Parses raw LightRAG context into discrete entities, relations, and text."""
    if not context_text or not isinstance(context_text, str):
        return [], [], ""

    entities = []
    relations = []

    # Parse entities
    for line in context_text.splitlines():
        line = line.strip()
        if line.startswith('{"entity":'):
            try:
                obj = json.loads(line)
                entities.append(canonical_key(obj.get("entity", "")))
            except Exception:
                pass
        elif line.startswith('{"source":'):
            try:
                obj = json.loads(line)
                src = canonical_key(obj.get("source", ""))
                tgt = canonical_key(obj.get("target", ""))
                relations.append((src, tgt))
            except Exception:
                pass

    return entities, relations, context_text.lower()

def evaluate_case(retrieved_text: str, ground_truth_list: list[str], candidates_list: list[str]):
    """
    Computes 100% deterministic mathematical metrics:
      - Hit@1, Hit@5, Hit@20
      - Reciprocal Rank (RR)
      - Candidate Evidence Scores & Differential Selection
      - Evidence Margin
    """
    entities, relations, raw_text_lower = parse_retrieved_context(retrieved_text)

    # 1. Target Disease Ground Truth
    canonical_targets = [canonical_key(t) for t in ground_truth_list]
    primary_target = canonical_targets[0] if canonical_targets else ""

    # 2. Hit@K and Rank
    hit_1 = 0
    hit_5 = 0
    hit_20 = 0
    rank = 0
    rr = 0.0

    for idx, e in enumerate(entities, start=1):
        if any(t in e or e in t for t in canonical_targets):
            if rank == 0:
                rank = idx
                rr = 1.0 / rank
            if idx <= 1:
                hit_1 = 1
            if idx <= 5:
                hit_5 = 1
            if idx <= 20:
                hit_20 = 1

    # Fallback: if not in entity list, check if mentioned in retrieved relations or chunks
    if hit_20 == 0:
        for src, tgt in relations:
            if any(t in src or t in tgt for t in canonical_targets):
                hit_20 = 1
                break

    # 3. Candidate Differential Discrimination (Metric 3)
    candidate_scores = {}
    for cand in candidates_list:
        c_key = canonical_key(cand)
        # Layer 1: Entity mention
        node_pts = sum(1 for e in entities if c_key in e or e in c_key)
        # Layer 2: Connected edges
        edge_pts = sum(1 for s, t in relations if c_key in s or c_key in t)
        # Layer 3: Text occurrences in retrieved chunks
        chunk_pts = raw_text_lower.count(c_key)
        
        total_pts = (node_pts * 2) + edge_pts + chunk_pts
        candidate_scores[cand] = total_pts

    # Pick top candidate deterministically
    sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
    top_cand, top_score = sorted_candidates[0] if sorted_candidates else ("", 0)
    second_score = sorted_candidates[1][1] if len(sorted_candidates) > 1 else 0

    # Was the true disease selected as top candidate?
    canonical_top = canonical_key(top_cand)
    candidate_acc = 1 if any(t in canonical_top or canonical_top in t for t in canonical_targets) else 0

    # Evidence Margin
    target_score = candidate_scores.get(ground_truth_list[0], 0)
    margin = target_score - second_score if candidate_acc == 1 else target_score - top_score

    # Number of connected edges for target
    target_edges = sum(1 for s, t in relations if any(tg in s or tg in t for tg in canonical_targets))

    return {
        "hit_1": hit_1,
        "hit_5": hit_5,
        "hit_20": hit_20,
        "rank": rank,
        "rr": rr,
        "candidate_acc": candidate_acc,
        "top_candidate": top_cand,
        "top_score": top_score,
        "margin": margin,
        "target_edges": target_edges,
        "total_entities_retrieved": len(entities),
        "total_relations_retrieved": len(relations),
    }

# =====================================================================
# BLOCK 6: BENCHMARK EXECUTION PIPELINE
# =====================================================================
async def main():
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

    print(f"\nStarting Deterministic Retrieval Benchmark on {len(test_cases)} cases...")
    print(f"Keyword extraction mode: {KEYWORD_MODE.upper()}\n")

    results_log = []
    global current_clues

    for i, tc in enumerate(test_cases, start=1):
        cid = tc["case_id"]
        masked_text = tc["masked_text"]
        ground_truth = tc["ground_truth"]
        candidates = tc["candidates"]
        current_clues = tc.get("remaining_clues", "")

        # Query LightRAG in hybrid mode, fetching ONLY the retrieved context
        param = QueryParam(
            mode="hybrid",
            only_need_context=True,
            top_k=20,
        )

        try:
            retrieved_context = await rag.aquery(masked_text, param=param)
        except Exception as e:
            print(f"[{i}/{len(test_cases)}] Case {cid} query failed: {e}")
            retrieved_context = ""

        if not retrieved_context or not isinstance(retrieved_context, str):
            retrieved_context = ""

        # Compute deterministic metrics
        metrics = evaluate_case(retrieved_context, ground_truth, candidates)
        row = {
            "case_id": cid,
            "ground_truth": "|".join(ground_truth),
            **metrics,
        }
        results_log.append(row)

        # Print progress every 10 cases
        if i % 10 == 0 or i == len(test_cases):
            print(f"  Processed [{i:>3}/{len(test_cases)}] | Latest: {cid} | Hit@5: {metrics['hit_5']} | Candidate Acc: {metrics['candidate_acc']}")

    await rag.finalize_storages()

    # =====================================================================
    # BLOCK 7: SAVE CSV & PRINT SUMMARY REPORT
    # =====================================================================
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results_log[0].keys()))
        writer.writeheader()
        writer.writerows(results_log)

    total = len(results_log)
    hit1_rate = sum(r["hit_1"] for r in results_log) / total * 100
    hit5_rate = sum(r["hit_5"] for r in results_log) / total * 100
    hit20_rate = sum(r["hit_20"] for r in results_log) / total * 100
    mrr = sum(r["rr"] for r in results_log) / total
    cand_acc = sum(r["candidate_acc"] for r in results_log) / total * 100

    print("\n" + "=" * 65)
    print("      DETERMINISTIC RETRIEVAL BENCHMARK REPORT")
    print("=" * 65)
    print(f"  Total Masked Test Cases Evaluated : {total}")
    print(f"  Target Disease Hit@1 (Rank 1)     : {hit1_rate:.2f}%")
    print(f"  Target Disease Hit@5 (Top 5)      : {hit5_rate:.2f}%")
    print(f"  Target Disease Hit@20 (Subgraph)  : {hit20_rate:.2f}%")
    print(f"  Mean Reciprocal Rank (MRR)        : {mrr:.4f}")
    print(f"  Candidate Discrimination Accuracy : {cand_acc:.2f}% (Graph-Only)")
    print("=" * 65)
    print(f"Detailed per-case results saved to: {OUTPUT_CSV}\n")

if __name__ == "__main__":
    asyncio.run(main())
