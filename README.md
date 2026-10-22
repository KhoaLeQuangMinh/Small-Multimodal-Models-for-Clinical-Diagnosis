# Small-Multimodal-Models-for-Clinical-Diagnosis

Project repository for **Tropical Infectious Diseases Clinical Diagnosis** using Small Multimodal Models (SMMs/SLMs), Knowledge Graph RAG (LightRAG), and a Dual-Brain Cognitive Architecture.

Supervised by: **Dr. Tran Duc Khanh** (Faculty of Engineering, Vietnamese-German University).

---

## 🏛️ System Architecture: The 3 Core Pillars

This repository unifies three interconnected clinical engineering pillars into a single end-to-end diagnosis and reasoning pipeline:

```
                            [1. Clinical Data Pipeline (data_pipeline/)]
                            Official_MultiCaRe PMC Parquets (76,137 Cases)
                                                │
                                                ▼  Stage 1 (build_partA.py)
                                    2,437 Tropical Candidates
                                                │
                                                ▼  Stage 2 (prompt_v4.py & merge_v4.py)
                                    1,797 Verified Cases with Quotes
                                                │
                                                ▼  Stages 4 & 5 (rewrite_agent.py & casedef_agent.py)
                                    1,236 Clinically Proven Gold Cases
                                                │
                    ┌───────────────────────────┴───────────────────────────┐
                    ▼                                                       ▼
    [2. LightRAG Knowledge Graph Suite]                      [3. Dual-Brain Cognitive Architecture]
    build_clinical_kg.py (Biomedical Embeddings)             Stage 1: Semantic Brain (22 WHO/CDC Guides)
    LightRAG Graph & Vector Storage                          Stage 2: Episodic Memory (1,427 Patient Twins)
    benchmark_rag.py (Tier 1 Graph / Tier 2 Hybrid)          Stage 3: Hub Suppression (Degree Discounting)
    benchmark_retrieval.py (Hit-Rate & Recall)               Stage 4: Constrained CoT SLM Engine (Qwen2.5-3B)
```

### Pillar 1: Clinical Data Curation Pipeline (`data_pipeline/`)
Curated from upstream PMC open-access case reports:
- **MeSH Disease Cohort Derivation (`build_partA.py`):** Selects cases mapped to 22 WHO/CDC neglected tropical diseases.
- **Verbatim Evidence Verification (`prompt_v4.py`, `check_v4.py`, `merge_v4.py`):** Multi-stage LLM extraction requiring exact source quotes.
- **Blinded Case Rewriting (`rewrite_agent.py`):** MedCaseReasoning-style reformulations removing diagnostic spoilers from admission vignettes.
- **Algorithmic Case Definition Checklist (`casedef_agent.py`):** Grades diagnostic certainty (Confirmed / Probable / Suspected) against published CDC/WHO/EORTC surveillance guidelines.

### Pillar 2: LightRAG Knowledge Graph & Benchmark Suite
A multi-tier evaluation framework benchmarking Knowledge Graph retrieval for clinical differential diagnosis:
- **Graph Ingestion (`build_clinical_kg.py`):** Ingests clinical triples with entity normalization into LightRAG storage.
- **Tier 1 & Tier 2 Evaluation (`benchmark_rag.py`, `benchmark_rag_slot.py`):** Evaluates naive Graph-Only (Tier 1) and Hybrid Graph+Vector (Tier 2, 10-chunk window) retrieval against 365 masked test cases.
- **Retrieval Hit-Rate Benchmark (`benchmark_retrieval.py`):** Measures precision, recall, and hit-rate of disease entity retrieval.

### Pillar 3: Dual-Brain Cognitive Architecture (`stage1` to `stage4`)
A biologically inspired dual-memory architecture designed to overcome SLM diagnostic hallucination:
- **Stage 1 (Semantic Brain):** 22 canonical disease monographs (`stage1_disease_guides/`) synthesized from WHO/CDC literature, parsed into a canonical Semantic Knowledge Graph (`build_stage1_kg.py`) with PubMedBERT embeddings.
- **Stage 2 (Episodic Brain):** 1,427 distilled historical patient profiles (`stage2_medcase_distillation/train_medcase_profiles.jsonl`), pre-computed dense embeddings (`train_medcase_embeddings.npy`), and high-speed (<2ms) Patient Twin vector retriever (`case_memory_retriever.py`).
- **Stage 3 (Graph Weighting & Hub Suppression):** Degree discounting algorithm (`stage3_graph_weighting/triple_ranker.py`) penalizing hyper-generic symptoms (fever, headache, fatigue) to surface pathognomonic diagnostic triples.
- **Stage 4 (Constrained CoT SLM Engine):** Constrained micro-Chain-of-Thought diagnostic inference runner (`stage4_constrained_inference/benchmark_stage4_cot.py`) powered by Qwen2.5-3B-Instruct, achieving **48.22% Top-1** and **72.33% Top-3** accuracy across 365 test cases (vs. 7.67% zero-shot baseline).

---

## 📊 Benchmark Results

Evaluated across the 365-case clinical test cohort with zero test leakage:

| Diagnostic Architecture | Retriever / Memory | Model | Top-1 Accuracy | Top-3 Accuracy | Avg Latency |
|---|---|---|---|---|---|
| **Tier 0 Baseline** | None (Zero-shot) | Qwen2.5-3B-Instruct | 7.67% | 31.78% | ~1.1s |
| **Tier 1 Naive LightRAG** | Graph-Only (Extracted Triples) | Qwen2.5-3B-Instruct | 28.22% | 58.63% | ~1.8s |
| **Tier 2 Hybrid LightRAG** | Hybrid (Graph + Vector, 10 chunks) | Qwen2.5-3B-Instruct | 28.77% | 59.45% | ~2.1s |
| **Tier 4 Dual-Brain Engine** | **Semantic KG + Episodic Twins (k=2)** | **Qwen2.5-3B-Instruct** | **48.22%** | **72.33%** | **~2.8s** |

*For complete ablation breakdowns, see [`docs/RESULT.md`](docs/RESULT.md).*

---

## 📂 Repository Structure

```text
Datasets/
├── README.md                                           # Master documentation & entry point
├── CHANGELOG.md                                        # Chronological project ledger
├── requirements.txt                                    # Python dependencies
├── .gitignore                                          # VCS ignore patterns & explicit whitelists
│
├── benchmarks/                                         # [Pillar 2] Benchmark Suite & Runners
│   ├── README.md                                       # CLI usage guide for all evaluation tiers
│   ├── benchmark_baseline.py                           # Tier 0: Zero-shot baseline SLM diagnostic runner
│   ├── benchmark_rag.py                                # Tiers 1 & 2: LightRAG (Graph & Hybrid) runner
│   ├── benchmark_rag_slot.py                           # Phase 1: Clinical slot keyword LightRAG runner
│   ├── benchmark_retrieval.py                          # Knowledge Graph retrieval hit-rate evaluator
│   ├── build_clinical_kg.py                            # LightRAG biomedical KG index builder
│   ├── prepare_test_masked.py                          # Cohort splitter & masked test cohort builder
│   └── results/                                        # Output CSV benchmark evaluations
│       ├── baseline_results.csv
│       ├── rag_tier1_graph_only_results.csv
│       ├── rag_tier1_slot_prompt_results.csv
│       ├── rag_tier2_hybrid_results.csv
│       ├── rag_tier2_hybrid_10chunks_results.csv
│       ├── retrieval_benchmark_results.csv
│       └── retrieval_benchmark_ollama_results.csv
│
├── data/                                               # Shared Canonical Evaluation Datasets
│   ├── README.md                                       # Cohort description, masking protocol & provenance
│   └── test_masked_cases.jsonl                         # 365 verified masked clinical admissions cohort
│
├── docs/                                               # Architecture, Prompt & Research Documentation
│   ├── GIT_GUIDELINES.md                               # Team git branching & PR guidelines + Secret prevention
│   ├── PIPELINE_ROADMAP.md                             # 4-stage Dual-Brain architecture roadmap
│   ├── PROMPTS.md                                      # Clinical prompt repository (Tiers 0, 1, 2)
│   └── RESULT.md                                       # Master diagnostic benchmark results report
│
├── data_pipeline/                                      # [Pillar 1] Clinical Data Curation Pipeline
│   ├── README.md
│   ├── docs/
│   └── llm/
│
├── stage1_disease_guides/                              # [Pillar 3 - Stage 1] 22 Disease Monographs & Semantic KG
├── stage2_medcase_distillation/                        # [Pillar 3 - Stage 2] 1,427 Patient Vignettes & Episodic Twins
├── stage3_graph_weighting/                             # [Pillar 3 - Stage 3] Hub Suppression & Degree Discounting
├── stage4_constrained_inference/                       # [Pillar 3 - Stage 4] Constrained CoT SLM Diagnostic Engine
│
├── Custom_Tropical_Project/                            # Clinical project core & notebooks
│   ├── 1_Data_Exploration/                             # Cohort derivation & EDA notebooks
│   ├── 2_Clinical_Verification/                        # Gold dataset, DOID taxonomy, download instructions
│   └── 4_Literature_and_Materials/                     # Foundational literature PDFs
│
├── Official_MultiCaRe/                                 # Upstream MultiCaRe reference dataset
└── scripts/                                            # Multi-account evaluation split/merge utilities
```

---

## 🚀 Setup & Execution Guide

### 1. Environment Setup
```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Local Models (Ollama)
Ensure [Ollama](https://ollama.com/) is installed and running:
```bash
ollama pull qwen2.5:3b
ollama pull bge-m3
```

### 3. Running Workflows

#### A. Patient Twin Memory Retrieval (Episodic Brain)
```bash
python3 -c "
from stage2_medcase_distillation.case_memory_retriever import CaseMemoryRetriever
retriever = CaseMemoryRetriever()
twins = retriever.retrieve_twins('A 35-year-old male presents with high fever, retro-orbital headache, and severe myalgia for 4 days.', top_k=2)
for t in twins:
    print('Twin:', t['case_id'], 'Disease:', t['disease'], 'Similarity:', f'{t[\"similarity\"]:.4f}')
"
```

#### B. LightRAG Knowledge Graph Benchmarks
```bash
# Tier 1 (Graph-Only RAG):
python3 benchmarks/benchmark_rag.py --tier 1 --max-cases 5

# Tier 2 (Hybrid Graph + Vector RAG, 10 chunks):
python3 benchmarks/benchmark_rag.py --tier 2 --top-chunks 10 --max-cases 5

# Retrieval Hit-Rate Evaluation:
python3 benchmarks/benchmark_retrieval.py
```

#### C. Dual-Brain Constrained Inference Engine (Stage 4)
```bash
cd stage4_constrained_inference
python3 benchmark_stage4_cot.py --max-cases 5
```

---

## 📖 Team Guidelines & Contributing

All contributors, student researchers, and AI agents must review and follow:
- **[`docs/GIT_GUIDELINES.md`](docs/GIT_GUIDELINES.md)**: Git/GitHub branch conventions (`feature/*`, `bugfix/*`, `experiment/*`), credential security & secret leak prevention, safe rebasing, force-push limits, and ML research best practices (zero test leakage, fixed seeds, multi-metric evaluation).
- **[`docs/PIPELINE_ROADMAP.md`](docs/PIPELINE_ROADMAP.md)**: Architectural roadmap and development checklist.
- **[`docs/PROMPTS.md`](docs/PROMPTS.md)**: Master repository for clinical prompts.
- **[`docs/RESULT.md`](docs/RESULT.md)**: Master diagnostic accuracy and ablation evaluation report.
- **[`CHANGELOG.md`](CHANGELOG.md)**: Project version ledger with strict formatting rules for logging updates.