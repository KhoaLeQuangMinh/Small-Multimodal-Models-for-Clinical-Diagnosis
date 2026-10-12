"""
build_vector_case_memory.py
Builds the Episodic Vector Case Memory (The Episodic Brain) for Stage 2.
Encodes 1,427 distilled admission case prompts into 768-d normalized dense vectors
using NeuML/pubmedbert-base-embeddings (512 max sequence length).
"""

import os
import json
import time
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

def extract_clinical_summary(prompt: str, max_words: int = 60) -> str:
    """Extracts the first 1-2 sentences of the case prompt as the concise clinical vignette."""
    # Split on sentence boundaries
    sentences = [s.strip() for s in prompt.replace("\n", " ").split(". ") if s.strip()]
    if not sentences:
        return prompt[:200]
    
    summary = sentences[0]
    if not summary.endswith("."):
        summary += "."
    
    if len(sentences) > 1 and len(summary.split()) < 30:
        summary += " " + sentences[1]
        if not summary.endswith("."):
            summary += "."
            
    # Clip if overly long
    words = summary.split()
    if len(words) > max_words:
        summary = " ".join(words[:max_words]) + "..."
    return summary

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    profiles_path = os.path.join(base_dir, "train_medcase_profiles.jsonl")
    emb_output_path = os.path.join(base_dir, "train_medcase_embeddings.npy")
    meta_output_path = os.path.join(base_dir, "train_medcase_metadata.json")

    print(f"=== Stage 2: Building Episodic Vector Case Memory ===")
    print(f"Reading consolidated profiles: {profiles_path}")

    cases = []
    with open(profiles_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    n_cases = len(cases)
    print(f"Total clinical cases loaded: {n_cases}")
    assert n_cases == 1427, f"Expected 1427 cases, but found {n_cases}"

    # Extract prompts and build metadata lookup
    prompts = []
    metadata = []

    for i, c in enumerate(cases):
        prompt_text = c["case_prompt"]
        prompts.append(prompt_text)

        # Simplify reasoning for fast precedent card injection
        reasoning_list = c.get("diagnostic_reasoning", [])
        differentials = []
        diagnostic_pivot = ""

        if isinstance(reasoning_list, list):
            for item in reasoning_list:
                cand = item.get("candidate", "")
                reason = item.get("rule_out_reason", "")
                if cand.lower() == "diagnostic pivot":
                    diagnostic_pivot = reason
                else:
                    differentials.append({
                        "candidate": cand,
                        "rule_out_reason": reason
                    })
        elif isinstance(reasoning_list, str):
            diagnostic_pivot = reasoning_list

        meta_entry = {
            "index": i,
            "global_index": c.get("global_index", i),
            "batch_id": c.get("batch_id", i // 10),
            "case_id": c["case_id"],
            "disease": c["disease"],
            "final_diagnosis": c.get("final_diagnosis", c["disease"]),
            "clinical_summary": extract_clinical_summary(prompt_text),
            "differentials": differentials,
            "diagnostic_pivot": diagnostic_pivot,
            "prompt_length_chars": len(prompt_text),
            "prompt_length_words": len(prompt_text.split())
        }
        metadata.append(meta_entry)

    # Device selection
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"Using device: {device}")

    # Load model
    model_name = "NeuML/pubmedbert-base-embeddings"
    print(f"Loading embedding model: {model_name}...")
    t0 = time.time()
    model = SentenceTransformer(model_name, device=device)
    model.max_seq_length = 512
    print(f"Model loaded in {time.time() - t0:.2f}s (max_seq_length = {model.max_seq_length})")

    # Encode all case prompts in batches
    batch_size = 32
    print(f"Encoding {n_cases} case prompts (batch_size={batch_size})...")
    t1 = time.time()
    embeddings = model.encode(
        prompts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,  # Unit L2 norm for exact cosine similarity
        convert_to_numpy=True
    )
    encode_time = time.time() - t1
    print(f"Encoding completed in {encode_time:.2f}s ({n_cases / encode_time:.1f} cases/sec)")
    print(f"Embeddings matrix shape: {embeddings.shape}, dtype: {embeddings.dtype}")

    # Save pre-computed embeddings matrix
    print(f"Saving embeddings to: {emb_output_path}")
    np.save(emb_output_path, embeddings.astype(np.float32))

    # Save lookup metadata
    print(f"Saving metadata to: {meta_output_path}")
    with open(meta_output_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    emb_size_mb = os.path.getsize(emb_output_path) / (1024 * 1024)
    meta_size_mb = os.path.getsize(meta_output_path) / (1024 * 1024)
    print(f"Episodic Vector Memory Build Complete!")
    print(f"  - Vector Matrix: {emb_output_path} ({emb_size_mb:.2f} MB)")
    print(f"  - Case Metadata: {meta_output_path} ({meta_size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
