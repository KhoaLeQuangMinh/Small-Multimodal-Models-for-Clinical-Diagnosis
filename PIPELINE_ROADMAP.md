# Clinically Grounded Diagnostic RAG: Master Roadmap & Checklist

This roadmap outlines the complete 4-stage engineering overhaul designed to maximize the diagnostic upper bound of a Small Language Model (`qwen2.5:3b`) across **22 Tropical and Neglected Diseases**.

It implements the **Clinician's Dual-Brain Architecture** (grounded in cognitive Script Theory, Stanford's *MedCaseReasoning*, Microsoft *GraphRAG*, and *MedRAG*).

---

## 🗺️ Master Architecture: The Clinician's Dual-Brain

```
=========================================================================================================
                                     [ UNSEEN MASKED TEST PATIENT ]
                                                    │
                   ┌────────────────────────────────┴────────────────────────────────┐
                   ▼                                                                 ▼
      [ STAGE 1: SEMANTIC BRAIN ]                                       [ STAGE 2: EPISODIC BRAIN ]
      Knowledge Graph (LightRAG)                                      Vector Case Memory (FAISS/NumPy)
                   │                                                                 │
    22 Canonical Disease Guides (WHO/CDC)                             1,427 Distilled MedCase Profiles
   "Textbook Criteria, Hallmarks & Exclusions"                        "Historical Patient Twin Precedents"
                   │                                                                 │
                   ▼                                                                 ▼
      [ STAGE 3: WEIGHT DISCOUNTING ]                                       Top 2 "Patient Twins"
    (Suppresses generic symptom hubs like                             (Immediate Case-Based Reasoning
       Fever, Pain via degree penalty)                                    similarity lookup in ~3ms)
                   │                                                                 │
                   ▼                                                                 │
          Top 15 Graph Triples                                                       │
                   │                                                                 │
                   └────────────────────────────────┬────────────────────────────────┘
                                                    ▼
                                   [ STAGE 4: CONSTRAINED SLM CoT ]
                               (Diagnostic Inference via Qwen2.5-3B)
                                                    │
                Prompt: Candidate List + Patient Vignette + Patient Twins + Graph Rules
                                                    ▼
                    Constrained CoT: Differentials -> Rule-Outs -> Rule-In -> Label
                                                    ▼
                                 [ FINAL DIAGNOSTIC EVALUATION REPORT ]
=========================================================================================================
```

---

## 📋 Master Execution Checklist

### Stage 1: 22 Canonical Disease Guides (Semantic Brain)
- [x] **1.1** Define standard clinical schema (Epidemiology, Cardinal Signs, Bedside Labs/Imaging, Exclusion Criteria, Empirical Drug Clues).
- [x] **1.2** Generate 22 comprehensive, guideline-aligned disease monographs (WHO / CDC / Europe PMC full texts).
- [x] **1.3** Format and validate each disease guide into markdown files inside `stage1_disease_guides/guides/` and compile consolidated bundles (`guides_bundle.jsonl` & `all_canonical_guides.md`).
- [ ] **1.4** Ingest the 22 canonical guides into LightRAG to construct the clean, noise-free Semantic Knowledge Graph.

### Stage 2: MedCaseReasoning Distillation & Vector Case Memory (Episodic Brain)
- [x] **2.1** Inspect the 1,427 training cohort cases in `train_kg_cases.jsonl`.
- [x] **2.2** Finalize the Gemini Flash distillation prompt with the **Admission-Phase Temporal Constraint**.
- [x] **2.3** Run batch distillation to convert 1,427 raw cases into `train_medcase_profiles.jsonl`.
- [x] **2.4** Compute dense embeddings (`NeuML/pubmedbert-base-embeddings`) and build the fast vector retrieval index (`train_medcase_embeddings.npy`).
- [x] **2.5** Unit test "Patient Twin" lookup to verify relevant real-world case matching in < 5ms.

### Stage 3: Graph Evaluation & Generic Term Weight Discounting
- [x] **3.1** Export and analyze node degree distribution from the canonical LightRAG graph.
- [x] **3.2** Catalog non-discriminative generic symptom terms (e.g., `Fever`, `Headache`, `Vomiting`, `Pain`).
- [x] **3.3** Implement the weighting discount function:
  $$\text{Score}(u, v) = \text{Relevance}(u, v) \times \frac{1}{\log(1 + \text{Degree}(v))}$$
- [x] **3.4** Integrate the weight discount into triple ranking so pathognomonic evidence is prioritized without deleting nodes.

### Stage 4: Constrained Diagnostic CoT for Small Language Model
- [ ] **4.1** Implement the Structured Chain-of-Thought (CoT) diagnostic prompt (`differentials` $\to$ `rule_out` $\to$ `rule_in` $\to$ `final_diagnosis`).
- [ ] **4.2** Synthesize prompt inputs: Patient Presentation + Top 2 Patient Twins (Stage 2) + Top 15 Graph Triples (Stages 1 & 3).
- [ ] **4.3** Build the automated evaluation script (`benchmark_stage4_cot.py`) with per-case auto-saving and resume capability.
- [ ] **4.4** Run benchmark across all 365 masked admission test cases (`test_masked_cases.jsonl`) on local Ollama (`qwen2.5:3b`).
- [ ] **4.5** Compute primary metrics: Top-1 Diagnostic Accuracy, Top-3 Differential Coverage, and Melioidosis Bias Rate.
- [ ] **4.6** Update master ablation tables in `RESULT.md`.

---

## 📂 Project Directory Structure

```
.
├── PIPELINE_ROADMAP.md                 <-- Master roadmap & checklist (this file)
├── stage1_disease_guides/             <-- Stage 1: 22 Canonical Guides & LightRAG Index
│   ├── README.md
│   └── guides/                         <-- Individual disease guide files
├── stage2_medcase_distillation/       <-- Stage 2: Distillation script & Vector Case Memory
│   ├── README.md
│   └── distill_cases.py
├── stage3_graph_weighting/            <-- Stage 3: Degree analysis & Soft Weighting
│   ├── README.md
│   └── analyze_and_weight_graph.py
└── stage4_constrained_inference/       <-- Stage 4: Dual-Context CoT Benchmark Runner
    ├── README.md
    └── benchmark_stage4_cot.py
```
