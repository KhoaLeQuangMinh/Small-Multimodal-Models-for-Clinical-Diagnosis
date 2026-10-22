# Canonical Evaluation Cohort (`data/`)

## 1. Overview & Provenance
This directory houses the frozen canonical evaluation cohort for the tropical disease diagnostic benchmarks.

- **File:** `test_masked_cases.jsonl`
- **Total Cases:** 365 patient admission vignettes
- **Disease Space:** 22 canonical tropical and neglected infectious diseases defined by WHO/CDC criteria
- **Source:** Upstream PMC MultiCaRe dataset, filtered and derived via `data_pipeline/llm/build_partA.py` and `benchmarks/prepare_test_masked.py`
- **Blinding & Masking:** Admission vignettes have undergone biomedical regex masking to prevent data leakage of confirmatory laboratory, microbiologic, or post-treatment outcomes.

---

## 2. JSONL Record Schema

Each line in `test_masked_cases.jsonl` is a self-contained JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `case_id` | `str` | Unique PMC case identifier (e.g. `PMC12544461_01`) |
| `masked_text` | `str` | Admission clinical presentation text with definitive diagnostic clues and confirmatory laboratory findings masked |
| `ground_truth` | `list[str]` | List of verified canonical disease names representing the true patient diagnosis (e.g. `["Tuberculosis"]`) |
| `candidates` | `list[str]` | List of 22 canonical candidate tropical disease classes |
| `remaining_clues` | `str` | Syndromic and non-confirmatory clinical signs used for keyword-based retrieval |

### Example Schema Instance:
```json
{
  "case_id": "PMC5866946_01",
  "masked_text": "A 45-year-old male farmer presents with high continuous fever, severe headache, retro-orbital pain, and generalized myalgia...",
  "ground_truth": ["Dengue"],
  "candidates": [
    "Amebiasis", "Cholera", "Dengue", "Echinococcosis", "Foodborne Trematodes",
    "Leishmaniasis", "Leprosy", "Leptospirosis", "Malaria", "Melioidosis",
    "Mycetoma", "Neurocysticercosis", "Paracoccidioidomycosis", "Scabies",
    "Schistosomiasis", "Scrub Typhus", "Soil-Transmitted Helminths", "Talaromycosis",
    "Trypanosomiasis", "Tuberculosis", "Viral Hemorrhagic Fevers", "Zika Virus"
  ],
  "remaining_clues": "high continuous fever, severe headache, retro-orbital pain, generalized myalgia, thrombocytopenia"
}
```

---

## 3. Data Integrity & Blinding Protocol
1. **Zero Contamination:** Test cases are strictly isolated from the training vignettes in `stage2_medcase_distillation/train_medcase_profiles.jsonl` (0 patient or PMC publication overlap).
2. **Deterministic Evaluation:** All benchmark scripts (`benchmarks/*.py` and `stage4_constrained_inference/benchmark_stage4_cot.py`) load this dataset to compute standardized Top-1 accuracy, Top-3 tolerant differential coverage, MRR, and per-disease metrics.
3. **Immutability:** Do not edit or overwrite `test_masked_cases.jsonl` during benchmarking runs.
