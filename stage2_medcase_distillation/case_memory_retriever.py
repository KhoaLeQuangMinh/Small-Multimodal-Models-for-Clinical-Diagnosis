"""
case_memory_retriever.py
Stage 2: The Episodic Brain — Vector Case Memory Retriever.
Loads pre-computed 768-d normalized embeddings (train_medcase_embeddings.npy) and metadata.
Retrieves Top-k 'Patient Twins' via fast cosine matrix multiplication in <2ms,
and formats them into standardized Clinical Precedent Cards for Qwen2.5-3B prompt injection.
"""

import os
import json
import time
from typing import List, Dict, Any, Tuple
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

class VectorCaseMemory:
    def __init__(
        self,
        embeddings_path: str = None,
        metadata_path: str = None,
        model_name: str = "NeuML/pubmedbert-base-embeddings",
        device: str = None
    ):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.embeddings_path = embeddings_path or os.path.join(base_dir, "train_medcase_embeddings.npy")
        self.metadata_path = metadata_path or os.path.join(base_dir, "train_medcase_metadata.json")
        self.model_name = model_name

        if device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"[VectorCaseMemory] Initializing on device: {self.device}")
        t0 = time.time()
        self.embeddings = np.load(self.embeddings_path)
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        assert len(self.embeddings) == len(self.metadata), (
            f"Mismatch between embeddings ({len(self.embeddings)}) and metadata ({len(self.metadata)})"
        )
        print(f"[VectorCaseMemory] Loaded {len(self.embeddings)} cases (shape: {self.embeddings.shape}) in {time.time() - t0:.3f}s")

        t1 = time.time()
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.model.max_seq_length = 512
        print(f"[VectorCaseMemory] Loaded {self.model_name} in {time.time() - t1:.3f}s")

    def retrieve(self, query_text: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves top_k patient twins via cosine similarity.
        Returns list of metadata dicts with added 'similarity' score.
        """
        # Encode query
        query_vec = self.model.encode(
            query_text,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        # Dot product with pre-normalized embeddings = exact cosine similarity
        t0 = time.time()
        similarities = np.dot(self.embeddings, query_vec)
        lookup_ms = (time.time() - t0) * 1000

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            case_info = dict(self.metadata[idx])
            case_info["similarity"] = float(similarities[idx])
            case_info["lookup_ms"] = lookup_ms
            results.append(case_info)

        return results

    def format_precedent_cards(self, query_text: str, top_k: int = 2) -> str:
        """
        Retrieves top_k twins and formats them into clean, standardized
        Clinical Precedent Cards ready for injection into {stage2_patient_twins_context}.
        """
        twins = self.retrieve(query_text, top_k=top_k)

        lines = ["### HISTORICAL CLINICAL PRECEDENTS (Closest Real-World Patient Cases):"]
        for i, twin in enumerate(twins, 1):
            disease = twin.get("disease", "Unknown")
            sim = twin.get("similarity", 0.0)
            case_id = twin.get("case_id", f"Case_{i}")
            summary = twin.get("clinical_summary", "")

            lines.append(f"\n[Precedent {i} - Confirmed {disease} (Similarity: {sim:.2f})]:")
            lines.append(f"- Case ID: {case_id}")
            lines.append(f"- Admission Presentation: {summary}")

            differentials = twin.get("differentials", [])
            if differentials:
                lines.append("- Differential Rule-Outs:")
                for diff in differentials[:3]:  # Top 2-3 rule outs
                    cand = diff.get("candidate", "")
                    reason = diff.get("rule_out_reason", "")
                    lines.append(f"  * Ruled out {cand}: {reason}")

            pivot = twin.get("diagnostic_pivot", "")
            if pivot:
                lines.append(f"- Diagnostic Pivot: {pivot}")

        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Running Unit Test for VectorCaseMemory ===")
    memory = VectorCaseMemory()

    test_query = (
        "A 32-year-old agricultural worker presents with a 5-day history of high remittent fever, "
        "severe myalgias, profound jaundice, and conjunctival suffusion after wading through floodwaters. "
        "Laboratory evaluation shows marked neutrophilic leukocytosis, elevated serum creatinine (3.8 mg/dL), "
        "hyperbilirubinemia (total bilirubin 14.2 mg/dL), and mild thrombocytopenia (92,000/uL). "
        "Chest radiograph reveals patchy bilateral alveolar infiltrates."
    )

    print("\n--- Test Query ---")
    print(test_query[:150] + "...")

    t_start = time.time()
    cards = memory.format_precedent_cards(test_query, top_k=2)
    elapsed_ms = (time.time() - t_start) * 1000

    print(f"\nTotal Retrieval + Card Formatting Latency: {elapsed_ms:.2f} ms")
    print("\n--- Formatted Clinical Precedent Cards ---")
    print(cards)
