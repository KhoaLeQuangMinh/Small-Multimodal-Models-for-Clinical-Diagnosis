import os
import json
import asyncio
import numpy as np
import torch

# Prevent PyTorch threading conflicts on macOS ARM64
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
torch.set_num_threads(1)

from sentence_transformers import SentenceTransformer
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc

# =====================================================================
# BLOCK 1: PATH CONFIGURATION
# =====================================================================
PROJECT_DIR = "/Users/khoale/Downloads/Project - SLM for Disease Diagnosis"
EXTRACTED_TRIPLES_FILE = os.path.join(PROJECT_DIR, "test-batch", "extracted_triples.jsonl")
TRAIN_CASES_FILE = os.path.join(PROJECT_DIR, "train_kg_cases.jsonl")
WORKING_DIR = os.path.join(PROJECT_DIR, "test_kg_output")

# =====================================================================
# BLOCK 2: LOAD DATA
# =====================================================================
with open(EXTRACTED_TRIPLES_FILE, "r", encoding="utf-8") as f:
    extracted_data = {item["case_id"]: item for line in f if (item := json.loads(line))}

with open(TRAIN_CASES_FILE, "r", encoding="utf-8") as f:
    cases_dict = {
        item["case_id"]: item
        for line in f
        if (item := json.loads(line))["case_id"] in extracted_data
    }

# =====================================================================
# BLOCK 3: ENTITY NAME NORMALISATION
# =====================================================================
# Normalises entity names to a canonical form before ingestion so that
# LightRAG's exact-match merge collapses near-duplicates into single nodes.
# Rules applied (in order):
#   1. Lowercase             — "Chest X-Ray" == "chest x-ray"
#   2. Strip apostrophes     — "Sabouraud's" == "sabouraud"
#   3. Strip hyphens/dashes  — "Anti-Tuberculosis" == "antituberculosis"
#   4. Collapse whitespace   — normalises any gaps left by stripping
#   5. Singularise           — "Seizures" == "seizure", "Lungs" == "lung"
#
# NOT applied: fuzzy/semantic merge — too risky for clinical terms
# (e.g. "Acalculous" vs "Calculous" look similar but are different diseases)
# NOT applied: singularise — strips trailing 's' which corrupts Latin pathogen
# names like "Aspergillus", "Staphylococcus", "Streptococcus", "Bacillus", etc.

def normalise_entity_name(name: str) -> str:
    name = name.lower().strip()
    name = name.replace("'s", "").replace("\u2019s", "")
    name = name.replace("-", "").replace("\u2013", "")
    name = " ".join(name.split())
    return name

def normalise_extraction(extraction: dict) -> dict:
    name_map = {}
    normalised_entities = []
    for entity in extraction.get("entities", []):
        original = entity["name"]
        normalised = normalise_entity_name(original)
        name_map[original] = normalised
        normalised_entities.append({**entity, "name": normalised})

    normalised_relationships = []
    for rel in extraction.get("relationships", []):
        normalised_relationships.append({
            **rel,
            "source": name_map.get(rel["source"], normalise_entity_name(rel["source"])),
            "target": name_map.get(rel["target"], normalise_entity_name(rel["target"])),
        })

    return {"entities": normalised_entities, "relationships": normalised_relationships}

for cid in extracted_data:
    extracted_data[cid]["extraction"] = normalise_extraction(extracted_data[cid]["extraction"])

# =====================================================================
# BLOCK 4: EMBEDDING FUNCTION
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
# BLOCK 5: DETERMINISTIC LLM LOOKUP
# =====================================================================
current_case_id = None

async def my_llm_func(prompt: str, **kwargs) -> str:
    if "---Input Text---" in prompt:
        return json.dumps(extracted_data[current_case_id]["extraction"])
    return ""

# =====================================================================
# BLOCK 6: LIGHTRAG INGESTION PIPELINE
# =====================================================================
async def main():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=my_llm_func,
        embedding_func=embedding_wrapper,
        entity_extraction_use_json=True,
        entity_extract_max_gleaning=0,
        chunk_token_size=8192,
        max_parallel_insert=1,
        embedding_func_max_async=1,
    )

    await rag.initialize_storages()

    global current_case_id
    for cid, case_data in cases_dict.items():
        current_case_id = cid
        await rag.ainsert(
            input=case_data["case_text"],
            ids=cid,
            file_paths=f"{cid}.txt"
        )

    await rag.finalize_storages()

if __name__ == "__main__":
    asyncio.run(main())