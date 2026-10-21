# Changelog

All notable changes to the `Datasets` unified repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Guidelines for Updating this Changelog

> **CRITICAL INSTRUCTIONS FOR HUMAN CODERS AND AI AGENTS:**
>
> 1. **When to Update:**
>    - Every non-trivial commit or PR (including feature additions, bug fixes, dataset curation steps, model benchmark runs, documentation updates, and architectural refactoring) MUST append an entry to this file.
>    - Ongoing changes under development should be placed under the `## [Unreleased]` section. When a release is cut or tagged, convert `## [Unreleased]` into the new version header with a timestamp.
>
> 2. **Standard Entry Format:**
>    Each entry line must adhere to the following template:
>    `- **YYYY-MM-DD HH:MM:SS ±ZZZZ** | \`[TAG]\` \`(scope)\` Description of what changed, rationale, and key artifacts produced. (Author / Agent ID)`
>
>    **Allowed Tags:**
>    - `[feat]`: New clinical features, pipeline stages, or inference modules
>    - `[fix]`: Bug fixes, path corrections, dependency resolutions
>    - `[data]`: Dataset extraction, cleaning, masking, case definition grading, schema updates
>    - `[eval]`: Benchmark runs, ablation evaluations, diagnostic accuracy scoring
>    - `[docs]`: Monograph additions, guidelines, paper drafts, markdown documentation
>    - `[refactor]`: Code reorganization, cleanup, optimization without changing behavior
>    - `[infra]`: Environment configuration, requirements, gitignore, CI/CD scripts
>
> 3. **Example Entries:**
>    ```markdown
>    - **2026-10-21 22:15:00 +07:00** | `[fix]` `(portability)` Replaced hardcoded `/Users/khoale/...` paths with `os.path.dirname(os.path.abspath(__file__))` in root benchmark scripts. (Agent Antigravity)
>    - **2026-10-22 10:00:00 +07:00** | `[data]` `(data_pipeline)` Cleaned 45 edge cases in Dengue cohort with missing platelet counts. (BillyData)
>    ```

---

## [Unreleased]

- Ongoing development and experiments.

---

## [1.0.0] - 2026-10-21 22:30:00 +07:00

### Added
- **Unified Main Repository:** Consolidated all clinical data engineering, LightRAG infrastructure, and Dual-Brain SLM diagnostic architecture into a single unified repository on `main`.
- **Billy's Clinical Data Curation Pipeline (`data_pipeline/`):**
  - Imported via `git subtree` preserving full commit history and author attribution (`BillyData <khoi20082005@gmail.com>`).
  - MeSH disease candidate extraction (`data_pipeline/llm/build_partA.py`) filtering 76,137 PMC MultiCaRe cases to 2,437 tropical candidate records across 22 WHO/CDC neglected tropical diseases.
  - LLM extraction and verification prompt suite (`data_pipeline/llm/prompt_v4.py`, `check_v4.py`, `merge_v4.py`) extracting verbatim clinical quotes and establishing ground truth.
  - Blind case rewrite engine (`data_pipeline/llm/rewrite_agent.py`) following MedCaseReasoning format to strip spoiler diagnoses from admission vignettes.
  - Algorithmic case-definition grading (`data_pipeline/llm/casedef_agent.py`) against published WHO/CDC criteria (Confirmed, Probable, Suspected).
  - Regex and agentic symptom masking (`data_pipeline/llm/mask_regex.py`, `mask_agent.py`).
- **Khoa's Complete LightRAG Ablation Suite (`feat/lightrag-ablation-study`):**
  - Clinical Knowledge Graph ingestion (`build_clinical_kg.py`) embedding clinical entities and relationships via biomedical transformers into LightRAG storage.
  - Multi-tier LightRAG diagnostic evaluation engine (`benchmark_rag.py`) supporting Tier 1 Graph-Only retrieval and Tier 2 Hybrid (Graph + Vector) retrieval with configurable 10-chunk windows.
  - Clinical slot-prompted LightRAG evaluation (`benchmark_rag_slot.py`).
  - Graph retrieval hit-rate and recall evaluator (`benchmark_retrieval.py`) supporting both instant clue-based extraction and local Ollama keyword querying.
  - Pre-computed benchmark ablation result sets (`rag_tier1_graph_only_results.csv`, `rag_tier2_hybrid_results.csv`, `rag_tier2_hybrid_10chunks_results.csv`).
- **Khoa's Dual-Brain Cognitive Architecture (Stages 1-4):**
  - **Stage 1 (Semantic Brain):** 22 canonical disease monographs (`stage1_disease_guides/`) synthesized from WHO/CDC literature, parsed into a canonical Semantic Knowledge Graph (`build_stage1_kg.py`) with PubMedBERT embeddings.
  - **Stage 2 (Episodic Brain):** 1,427 distilled historical patient profiles (`stage2_medcase_distillation/train_medcase_profiles.jsonl`), pre-computed dense embeddings (`train_medcase_embeddings.npy`), and high-speed (<2ms) Patient Twin vector retriever (`case_memory_retriever.py`).
  - **Stage 3 (Graph Weighting & Hub Suppression):** Degree discounting algorithm (`stage3_graph_weighting/triple_ranker.py`) penalizing hyper-generic symptoms (fever, headache, fatigue) to surface pathognomonic diagnostic triples.
  - **Stage 4 (Constrained CoT SLM Engine):** Constrained micro-Chain-of-Thought diagnostic inference runner (`stage4_constrained_inference/benchmark_stage4_cot.py`) powered by Qwen2.5-3B-Instruct, achieving **48.22% Top-1** and **72.33% Top-3** accuracy across 365 test cases (vs. 7.67% zero-shot baseline).
- **Standards & Guidelines:**
  - Added comprehensive `GIT_GUIDELINES.md` detailing branch taxonomies, daily workflows, safety rules (`revert`, `reset`, `push --force-with-lease`), and ML engineering best practices.
  - Added repository-wide `CHANGELOG.md` with explicit formatting guidelines.

### Changed / Portability
- **Path Sanitization:** Replaced hardcoded `/Users/khoale/Downloads/Project - SLM for Disease Diagnosis` paths across `prepare_test_masked.py`, `build_clinical_kg.py`, `benchmark_baseline.py`, `benchmark_rag.py`, `benchmark_rag_slot.py`, `benchmark_retrieval.py`, and distillation batch runners with dynamic relative paths.
- **Dependency Harmonization:** Added missing neural retrieval requirements (`torch>=2.0.0`, `sentence-transformers>=2.2.0`, `pydantic>=2.0.0`) to `requirements.txt`.
- **Git Ignore Whitelisting:** Updated `.gitignore` to prevent committing heavy PMC parquets and clinical images while explicitly whitelisting curated artifacts (`train_medcase_profiles.jsonl`, `label_additions.jsonl`, `test_masked_cases.jsonl`, `disease_ontology_doid.txt`).
- **Ontology Relocation:** Relocated DOID disease ontology hierarchy from root `disease.txt` to `Custom_Tropical_Project/2_Clinical_Verification/disease_ontology_doid.txt`.
