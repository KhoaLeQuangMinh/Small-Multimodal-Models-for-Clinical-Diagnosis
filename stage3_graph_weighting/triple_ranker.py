"""
triple_ranker.py
Stage 3: Clinical Triple Ranker & Generic Term Weight Discounting.
Applies Soft Weight Discounting to candidate Knowledge Graph triples,
suppressing generic constitutional symptom noise while prioritizing
pathognomonic diagnostic anchors for Qwen2.5-3B prompt injection.
"""

import os
import re
import json
from typing import List, Dict, Any, Union, Tuple

class ClinicalTripleRanker:
    def __init__(self, config_path: str = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = config_path or os.path.join(base_dir, "generic_terms_config.json")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.canonical_diseases = set(self.config.get("canonical_diseases", []))
        
        patterns = self.config.get("patterns", {})
        self.generic_regex = re.compile(patterns.get("generic_symptoms_regex", r"\b(fever|headache|pain)\b"), re.IGNORECASE)
        self.admin_regex = re.compile(patterns.get("administrative_terms_regex", r"\b(patient|hospital)\b"), re.IGNORECASE)
        self.patho_regex = re.compile(patterns.get("pathognomonic_terms_regex", r"\b(eschar|suffusion)\b"), re.IGNORECASE)

        weights = self.config.get("weights", {})
        self.generic_penalty = weights.get("generic_discount_penalty", 0.20)
        self.admin_penalty = weights.get("administrative_discount_penalty", 0.10)
        self.disease_anchor_mult = weights.get("disease_anchor_multiplier", 1.50)
        self.patient_match_mult = weights.get("patient_match_multiplier", 2.00)
        self.patho_bonus_mult = weights.get("pathognomonic_bonus_multiplier", 2.50)
        self.default_top_k = weights.get("default_top_k", 15)
        self.min_score_threshold = float(weights.get("min_score_threshold", 2.0))

    def _entity_specificity_weight(self, entity_text: str) -> float:
        """Computes specificity multiplier W(entity) using regex penalties."""
        if not entity_text:
            return 1.0
        
        # Severe penalty for administrative stop words
        if self.admin_regex.search(entity_text):
            return self.admin_penalty
        
        # Moderate penalty for generic constitutional symptoms
        if self.generic_regex.search(entity_text):
            return self.generic_penalty
        
        return 1.0

    def _matches_patient(self, text: str, patient_text_lower: str) -> bool:
        """Checks if a term or entity finding is mentioned in the patient's text."""
        if not text or not patient_text_lower:
            return False
        
        text_lower = text.lower()
        # Direct substring
        if text_lower in patient_text_lower:
            return True
        
        # Word token overlap (exclude short words)
        words = [w for w in re.findall(r"\w+", text_lower) if len(w) > 4]
        matches = sum(1 for w in words if w in patient_text_lower)
        return (matches >= 2) if len(words) >= 3 else (matches >= 1)

    def score_triple(
        self,
        triple: Union[Dict[str, Any], Tuple[str, str, str]],
        patient_text: str = ""
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculates the clinical discriminative utility score of a triple.
        """
        if isinstance(triple, dict):
            src = triple.get("source", "")
            rel = triple.get("relation", "")
            tgt = triple.get("target", "")
            desc = triple.get("description", "")
            base_w = float(triple.get("weight", 1.0))
        elif isinstance(triple, (list, tuple)):
            src = str(triple[0])
            rel = str(triple[1]) if len(triple) > 1 else "related_to"
            tgt = str(triple[2]) if len(triple) > 2 else ""
            desc = str(triple[3]) if len(triple) > 3 else ""
            base_w = 1.0
        else:
            return 0.0, {}

        patient_lower = patient_text.lower() if patient_text else ""

        # 1. Base weight
        score = base_w

        # 2. Specificity Discount (Down-weight generic hubs)
        w_src = self._entity_specificity_weight(src)
        w_tgt = self._entity_specificity_weight(tgt)
        score *= (w_src * w_tgt)

        # 3. Disease Anchor Multiplier
        is_anchor = (src in self.canonical_diseases or tgt in self.canonical_diseases)
        if is_anchor:
            score *= self.disease_anchor_mult

        # 4. Patient Presentation Match
        src_matched = self._matches_patient(src, patient_lower)
        tgt_matched = self._matches_patient(tgt, patient_lower)
        desc_matched = self._matches_patient(desc, patient_lower) if desc else False

        if src_matched or tgt_matched or desc_matched:
            score *= self.patient_match_mult

        # 5. Pathognomonic Anchor Booster
        has_patho_src = bool(self.patho_regex.search(src))
        has_patho_tgt = bool(self.patho_regex.search(tgt))
        has_patho_desc = bool(self.patho_regex.search(desc)) if desc else False

        if has_patho_src or has_patho_tgt or has_patho_desc:
            # If pathognomonic AND present in the patient: massive booster!
            if (has_patho_src and src_matched) or (has_patho_tgt and tgt_matched) or desc_matched:
                score *= self.patho_bonus_mult
            else:
                score *= 1.25

        breakdown = {
            "source": src,
            "relation": rel,
            "target": tgt,
            "description": desc,
            "score": round(score, 4),
            "is_anchor": is_anchor,
            "matched_patient": (src_matched or tgt_matched or desc_matched),
            "has_pathognomonic": (has_patho_src or has_patho_tgt or has_patho_desc)
        }

        return score, breakdown

    def rank_triples(
        self,
        candidate_triples: List[Union[Dict[str, Any], Tuple[str, str, str]]],
        patient_text: str = "",
        top_k: int = None,
        min_score: float = None
    ) -> List[Dict[str, Any]]:
        """
        Scores and ranks candidate triples in descending order of clinical utility.
        Filters out low-scoring distractor triples below min_score.
        """
        k = top_k or self.default_top_k
        thresh = min_score if min_score is not None else self.min_score_threshold
        scored = []
        for t in candidate_triples:
            s, meta = self.score_triple(t, patient_text=patient_text)
            if thresh is not None and s < thresh:
                continue
            scored.append((s, meta))

        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)

        return [meta for s, meta in scored[:k]]

    def format_triples_for_prompt(
        self,
        candidate_triples: List[Union[Dict[str, Any], Tuple[str, str, str]]],
        patient_text: str = "",
        top_k: int = None,
        min_score: float = None
    ) -> str:
        """
        Ranks candidate triples and formats them into clean markdown lines
        ready for prompt injection into {stage1_graph_context}.
        """
        ranked = self.rank_triples(candidate_triples, patient_text=patient_text, top_k=top_k, min_score=min_score)
        if not ranked:
            return "No specific pathognomonic graph triples matched this patient's admission presentation."

        lines = []
        for i, item in enumerate(ranked, 1):
            src = item["source"]
            rel = item["relation"]
            tgt = item["target"]
            desc = item.get("description", "")
            
            line = f"- [{src}] -> [{rel}] -> [{tgt}]"
            if desc and desc.strip() and desc.strip() != tgt:
                # Truncate long descriptions
                desc_clean = desc.strip().replace("\n", " ")
                if len(desc_clean) > 120:
                    desc_clean = desc_clean[:117] + "..."
                line += f": {desc_clean}"
            lines.append(line)

        return "\n".join(lines)
