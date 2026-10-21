"""
build_stage1_kg.py: Stage 1 Canonical Semantic Knowledge Graph Ingestion Pipeline
==================================================================================
This script builds the Golden Semantic Knowledge Graph for the 22 Canonical
Tropical Diseases using LightRAG with pre-extracted clinical cognition triples.

Key Highlights:
1. Biomedical Embeddings: Uses `NeuML/pubmedbert-base-embeddings` (768 dimensions),
   built on Microsoft PubMedBERT with dedicated biomedical vocabulary.
2. Deterministic LLM Mocking: Intercepts LightRAG's entity extraction calls and
   serves our 22 pre-extracted, clinically validated JSON profiles directly from
   `canonical_triples.jsonl`. Zero live LLM calls during build!
3. Canonical Monograph Grounding: Ingests all 22 authoritative monographs
   (`canonical_guide.md`) as single document chunks (chunk_token_size=8192) to preserve
   unbroken clinical context.
4. Cross-Disease Bridge Unification: Normalizes look-alike references
   (e.g., "Dengue Fever" -> "Dengue", "Pulmonary Tuberculosis" -> "Tuberculosis") so that
   differential diagnosis edges create direct bridges between disease hubs.

Usage:
  conda activate smm
  python stage1_disease_guides/build_stage1_kg.py [--clean]
  # Or with optional custom model:
  # python stage1_disease_guides/build_stage1_kg.py --model all-MiniLM-L6-v2
"""

import os
import sys
import json
import shutil
import asyncio
import argparse
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
# BLOCK 1: PATH CONFIGURATION (STAGE 1 FOLDER CONTEXT)
# =====================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) == "stage1_disease_guides":
    STAGE1_DIR = SCRIPT_DIR
    PROJECT_DIR = os.path.dirname(STAGE1_DIR)
else:
    PROJECT_DIR = SCRIPT_DIR
    STAGE1_DIR = os.path.join(PROJECT_DIR, "stage1_disease_guides")

EXTRACTED_TRIPLES_FILE = os.path.join(STAGE1_DIR, "canonical_triples.jsonl")
DISEASES_DIR = os.path.join(STAGE1_DIR, "diseases")
WORKING_DIR = os.path.join(STAGE1_DIR, "canonical_kg")

# Automatically load HF_TOKEN from project .env if present
env_file = os.path.join(PROJECT_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# Canonical 22 Disease Names
CANONICAL_22_DISEASES = {
    "Amebiasis", "Cholera", "Dengue", "Echinococcosis", "Foodborne Trematodes",
    "Leishmaniasis", "Leprosy", "Leptospirosis", "Malaria", "Melioidosis",
    "Mycetoma", "Neurocysticercosis", "Paracoccidioidomycosis", "Scabies",
    "Schistosomiasis", "Scrub Typhus", "Soil-Transmitted Helminths", "Talaromycosis",
    "Trypanosomiasis", "Tuberculosis", "Viral Hemorrhagic Fevers", "Zika Virus"
}

# Cross-Disease Look-Alike Canonical Normalization Map
# Collapses variant strings in DIFFERENTIATED_FROM onto the 22 canonical hubs
CANONICAL_SYNONYM_MAP = {
    "dengue fever": "Dengue",
    "severe dengue (dengue shock syndrome)": "Dengue",
    "zika virus infection": "Zika Virus",
    "pulmonary tuberculosis": "Tuberculosis",
    "miliary tuberculosis": "Tuberculosis",
    "cutaneous tuberculosis (lupus vulgaris)": "Tuberculosis",
    "severe falciparum malaria": "Malaria",
    "leptospirosis (weil disease)": "Leptospirosis",
    "echinococcosis (cystic hydatid disease)": "Echinococcosis",
    "cerebral echinococcosis": "Echinococcosis",
    "cutaneous scabies infestation": "Scabies",
    "visceral leishmaniasis": "Leishmaniasis",
    "cutaneous leishmaniasis": "Leishmaniasis",
    "mucocutaneous leishmaniasis": "Leishmaniasis",
    "tuberculoid leprosy": "Leprosy",
}

# =====================================================================
# BLOCK 2: LOAD MASTER EXTRACTION TRIPLES & MONOGRAPHS
# =====================================================================
def load_data():
    if not os.path.exists(EXTRACTED_TRIPLES_FILE):
        sys.exit(f"ERROR: Extracted triples file not found at: {EXTRACTED_TRIPLES_FILE}")

    with open(EXTRACTED_TRIPLES_FILE, "r", encoding="utf-8") as f:
        extracted_data = {
            item["case_id"]: item
            for line in f
            if line.strip() and (item := json.loads(line))
        }

    # Load corresponding canonical monographs
    monographs_dict = {}
    for cid in extracted_data:
        guide_path = os.path.join(DISEASES_DIR, cid, "canonical_guide.md")
        if not os.path.exists(guide_path):
            sys.exit(f"ERROR: Missing canonical guide for {cid} at {guide_path}")
        with open(guide_path, "r", encoding="utf-8") as f:
            monographs_dict[cid] = f.read()

    return extracted_data, monographs_dict

# =====================================================================
# BLOCK 3: ENTITY NORMALIZATION & CROSS-DISEASE BRIDGING
# =====================================================================
def normalise_disease_name(name: str) -> str:
    cleaned = " ".join(name.strip().split())
    cleaned_lower = cleaned.lower()
    
    # Check if this entity references one of our 22 canonical diseases
    if cleaned_lower in CANONICAL_SYNONYM_MAP:
        return CANONICAL_SYNONYM_MAP[cleaned_lower]
    for canon in CANONICAL_22_DISEASES:
        if cleaned_lower == canon.lower():
            return canon
            
    return cleaned

def normalise_extraction(extraction: dict) -> dict:
    name_map = {}
    normalised_entities = []
    seen_entity_names = set()

    # Identify which entities are purely disease look-alikes vs clinical manifestations
    disease_lookalike_targets = set()
    for rel in extraction.get("relationships", []):
        pred = rel.get("predicate", "")
        if not pred and rel.get("description", "").startswith("["):
            pred = rel["description"].split("]")[0].strip("[")
        if pred == "DIFFERENTIATED_FROM":
            disease_lookalike_targets.add(rel["target"])

    for entity in extraction.get("entities", []):
        original = entity["name"]
        # Only normalize if it is a disease hub or a differential look-alike target
        if entity.get("type") in ("Disease", "Differential_Diagnosis") or original in disease_lookalike_targets:
            normalised = normalise_disease_name(original)
        else:
            normalised = " ".join(original.strip().split())
        name_map[original] = normalised
        if normalised not in seen_entity_names:
            seen_entity_names.add(normalised)
            normalised_entities.append({**entity, "name": normalised})

    normalised_relationships = []
    seen_rel_keys = set()
    for rel in extraction.get("relationships", []):
        pred = rel.get("predicate", "")
        if not pred and rel.get("description", "").startswith("["):
            pred = rel["description"].split("]")[0].strip("[")

        src_orig = rel["source"]
        tgt_orig = rel["target"]
        
        src_norm = normalise_disease_name(src_orig)
        if pred == "DIFFERENTIATED_FROM" or tgt_orig in disease_lookalike_targets:
            tgt_norm = normalise_disease_name(tgt_orig)
        else:
            tgt_norm = name_map.get(tgt_orig, " ".join(tgt_orig.strip().split()))
        
        # Prevent self-loops
        if src_norm == tgt_norm:
            continue

        rel_key = (src_norm, tgt_norm, rel.get("keywords", ""))
        if rel_key not in seen_rel_keys:
            seen_rel_keys.add(rel_key)
            normalised_relationships.append({
                **rel,
                "source": src_norm,
                "target": tgt_norm,
                "predicate": pred,
            })

    return {"entities": normalised_entities, "relationships": normalised_relationships}

# =====================================================================
# BLOCK 4: LIGHTRAG INGESTION PIPELINE
# =====================================================================
current_case_id = None
extracted_data_global = {}

async def my_llm_func(prompt: str, **kwargs) -> str:
    """
    Deterministic LLM Mock:
    When LightRAG requests entity extraction for a chunk ('---Input Text---'),
    this function intercepts the call and serves our pre-validated clinical
    triples for the active disease monograph.
    """
    if "---Input Text---" in prompt:
        extraction_payload = extracted_data_global[current_case_id]["extraction"]
        return json.dumps(extraction_payload, ensure_ascii=False)
    return ""

async def main():
    global current_case_id, extracted_data_global

    parser = argparse.ArgumentParser(description="Build Stage 1 Canonical Semantic Knowledge Graph")
    parser.add_argument("--clean", action="store_true", help="Remove existing output directory before build")
    parser.add_argument(
        "--model",
        type=str,
        default="NeuML/pubmedbert-base-embeddings",
        help="HuggingFace embedding model (default: NeuML/pubmedbert-base-embeddings)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("STAGE 1: CANONICAL SEMANTIC KNOWLEDGE GRAPH BUILDER (LightRAG)")
    print("=" * 70)

    extracted_data, monographs_dict = load_data()
    print(f"Loaded {len(extracted_data)} disease extraction profiles from: {EXTRACTED_TRIPLES_FILE}")
    print(f"Loaded {len(monographs_dict)} canonical disease monographs from: {DISEASES_DIR}")

    # Normalize all 22 extractions in memory
    for cid in extracted_data:
        extracted_data[cid]["extraction"] = normalise_extraction(extracted_data[cid]["extraction"])
    extracted_data_global = extracted_data

    total_nodes = sum(len(d["extraction"]["entities"]) for d in extracted_data.values())
    total_edges = sum(len(d["extraction"]["relationships"]) for d in extracted_data.values())
    print(f"Normalized clinical graph: {total_nodes} entities, {total_edges} relationships ready for ingestion.")

    # -----------------------------------------------------------------
    # Configure Embedding Model (Default: NeuML/pubmedbert-base-embeddings)
    # -----------------------------------------------------------------
    embedding_model_name = args.model
    embedding_dim = 384 if "minilm" in embedding_model_name.lower() or "bge-small" in embedding_model_name.lower() else 768

    print(f"\nInitializing Embedding Model: '{embedding_model_name}' (dim={embedding_dim})...")
    embed_model = SentenceTransformer(embedding_model_name)
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
        embedding_dim=embedding_dim,
        func=my_embed_func,
        model_name=embedding_model_name,
    )

    if args.clean and os.path.exists(WORKING_DIR):
        print(f"Cleaning existing graph directory: {WORKING_DIR}")
        shutil.rmtree(WORKING_DIR)

    os.makedirs(WORKING_DIR, exist_ok=True)
    print(f"Target LightRAG storage directory: {WORKING_DIR}")

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

    print("\nInitializing LightRAG storages...")
    await rag.initialize_storages()

    total_diseases = len(extracted_data)
    print(f"\nCommencing ingestion of {total_diseases} Canonical Disease Monographs...")
    print("-" * 70)

    for idx, (cid, case_data) in enumerate(extracted_data.items(), start=1):
        current_case_id = cid
        disease_name = case_data.get("disease", cid)
        monograph_text = monographs_dict[cid]
        num_ents = len(case_data["extraction"]["entities"])
        num_rels = len(case_data["extraction"]["relationships"])

        print(f"[{idx:02d}/{total_diseases:02d}] Ingesting {disease_name:<28} ({num_ents} entities, {num_rels} relationships)...")
        await rag.ainsert(
            input=monograph_text,
            ids=cid,
            file_paths=f"{cid}.txt"
        )

    print("-" * 70)
    print("Finalizing LightRAG storages...")
    await rag.finalize_storages()

    graphml_path = os.path.join(WORKING_DIR, "graph_chunk_entity_relation.graphml")
    if os.path.exists(graphml_path):
        size_kb = os.path.getsize(graphml_path) / 1024
        print(f"\nSUCCESS: Canonical Knowledge Graph successfully compiled!")
        print(f"GraphML location : {graphml_path} ({size_kb:.1f} KB)")
        print(f"Vector storages  : {WORKING_DIR}")
    else:
        print(f"\nBuild complete. Output files saved in {WORKING_DIR}")

if __name__ == "__main__":
    asyncio.run(main())
