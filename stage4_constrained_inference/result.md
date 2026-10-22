# Clinical Diagnostic Benchmark Results & Ablation Progression
## Small Language Models (Qwen2.5-3B) with Dual-Brain Architecture for Tropical Disease Diagnosis

- **Model Evaluated:** `qwen2.5:3b` (Local Ollama, greedy decoding `temperature=0.0`, `num_ctx=8192`)
- **Dataset:** 365 verified masked clinical case admissions ([`data/test_masked_cases.jsonl`](../data/test_masked_cases.jsonl))
- **Disease Space:** 22 canonical tropical and neglected infectious diseases
- **Knowledge Base:** Dual-Brain System:
  - **Semantic Brain:** Stage 1 Canonical Knowledge Graph (3,719 entities, 3,696 relationships in PubMedBERT 768-d space) + Stage 3 Soft-Weighted Triple Ranker
  - **Episodic Brain:** Stage 2 Vector Case Memory (1,427 real patient precedent cards indexed via PubMedBERT)
  - **Constrained CoT:** Stage 4 Anchor-First structured differential elimination

---

## 1. Executive Cross-Experiment Ablation Summary

This master table tracks all 5 experimental benchmarks conducted on the 365 masked admission cohort ([`data/test_masked_cases.jsonl`](../data/test_masked_cases.jsonl)) under the **Tolerant Clinical Differential Evaluation** paradigm:

| Experiment / Benchmark Tier | Top-1 Diagnostic Accuracy | Tolerant Top-3 Coverage (Patient F1) | Mean Reciprocal Rank (MRR) | Weighted Tolerant Precision | Weighted Tolerant Recall | Weighted Tolerant F1 | Macro Tolerant F1 | Melioidosis Attractor Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tier 0: Zero-Shot (No RAG)** | 7.67% | 31.78% | 16.71% | 33.13% | 31.44% | 24.90% | 10.95% | 55.34% | Completed |
| **Tier 1: Graph-Only** | 29.04% | 44.11% | 35.75% | 35.36% | 43.90% | 36.87% | 21.18% | 25.21% | Completed |
| **Tier 2: Hybrid RAG** | 33.97% | 48.77% | 40.55% | 37.69% | 48.24% | 40.62% | 23.79% | 22.47% | Completed |
| **Stage 4: Old Sparse Baseline** | 25.21% | 45.75% | 33.88% | 45.01% | 45.26% | 38.77% | 28.65% | 32.88% | Completed |
| **Stage 4: Dual-Brain (Current)** | **48.22%** | **72.33%** | **58.86%** | **57.63%** | **71.54%** | **60.94%** | **43.94%** | **14.25%** | **Production** |

### Key Architectural Leaps:
1. **Top-1 Diagnostic Accuracy:** Leaped from **7.67%** (Tier 0) $\rightarrow$ **33.97%** (Tier 2) $\rightarrow$ **48.22%** (Stage 4 Dual-Brain), an absolute gain of **+40.55 percentage points** (+528% relative gain).
2. **Tolerant Top-3 Clinical Coverage:** Reached **72.33%** (264 / 365 cases), meaning nearly 3 out of every 4 complex masked admissions had the true pathogen isolated within the top 3 differential list.
3. **Mean Reciprocal Rank (MRR):** Climbed from **16.71%** to **58.86%**, confirming that true diagnoses are placed near the very top of the differential ranking.
4. **Weighted Tolerant F1-Score:** Broke the 60% threshold, reaching **60.94%** (compared to 24.90% in zero-shot).
5. **Melioidosis Attractor Collapse:** Reduced by **-74.2%** from 55.34% down to **14.25%**, demonstrating effective elimination of the severe LLM hallucination attractor.

---

## 2. Global Diagnostic Ranking & Classification Metrics ($N = 365$)

### Comparison: Top-1 vs. Strict Top-3 vs. Tolerant Differential Paradigm

| Evaluation Metric | Top-1 (Commitment) | Strict Top-3 (Multi-Label) | **Tolerant Top-3 (Clinical Differential)** | Clinical & Statistical Meaning |
| :--- | :---: | :---: | :---: | :--- |
| **Diagnostic Coverage / Hit Rate** | **48.22%** (176/365) | **72.33%** (264/365) | **72.33%** (264/365) | Percentage of patient admissions where the true pathogen is captured. |
| **Mean Reciprocal Rank (MRR)** | **0.5886 (58.86%)** | **0.5886 (58.86%)** | **0.5886 (58.86%)** | Average reciprocal score (Rank 1: 1.0, Rank 2: 0.5, Rank 3: 0.333). |
| **Patient-Level Precision** | 48.22% | 24.11% *(Max: 33.3%)* | **72.33%** | Precision when any valid hit in the top-3 differential is credited. |
| **Patient-Level Recall** | 48.22% | 72.19% | **72.33%** | Patient-level sensitivity. |
| **Patient-Level F1-Score** | 48.22% | 36.14% | **72.33%** | Harmonic balance of patient-level diagnostic accuracy. |
| **Weighted Precision** | 55.28% | 38.85% | **57.63%** | Population-weighted positive predictive value. |
| **Weighted Recall (Sensitivity)** | 47.70% | 71.54% | **71.54%** | Population-weighted sensitivity across all admissions. |
| **Weighted F1-Score** | 48.63% | 46.53% | **60.94%** | Population-weighted harmonic performance. |
| **Macro-Precision** | 38.14% | 23.73% | **41.25%** | Unweighted average precision across all 22 diseases. |
| **Macro-Recall (Sensitivity)** | 40.50% | 60.56% | **60.56%** | Unweighted average sensitivity across all 22 diseases. |
| **Macro-F1 Score** | 37.24% | 29.52% | **43.94%** | Unweighted harmonic performance across all 22 diseases. |

### Reciprocal Rank (RR) Distribution ($N = 365$)
- **Rank 1 ($RR = 1.000$):** 176 cases (**48.2%**) — Model placed the correct diagnosis as its primary hypothesis.
- **Rank 2 ($RR = 0.500$):** 57 cases (**15.6%**) — Model placed the correct diagnosis as its second differential.
- **Rank 3 ($RR = 0.333$):** 31 cases (**8.5%**) — Model placed the correct diagnosis as its third differential.
- **Not in Top-3 ($RR = 0.0$):** 101 cases (**27.7%**) — Model failed to capture the pathogen in the top-3 differential.

---

## 3. Per-Class Top-1 Diagnostic Metrics (Stage 4)

| Tropical Disease Class | Support ($N$) | TP | FP | FN | Precision | Recall (Sensitivity) | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tuberculosis** | 129 | 56 | 16 | 73 | **77.8%** | 43.4% | **55.7%** |
| **Echinococcosis** (Hydatid) | 44 | 37 | 22 | 7 | **62.7%** | **84.1%** | **71.8%** |
| **Leishmaniasis** | 28 | 21 | 18 | 7 | **53.8%** | **75.0%** | **62.7%** |
| **Dengue** | 23 | 5 | 12 | 18 | 29.4% | 21.7% | 25.0% |
| **Malaria** | 19 | 8 | 14 | 11 | 36.4% | 42.1% | 39.0% |
| **Leptospirosis** | 15 | 8 | 5 | 7 | **61.5%** | **53.3%** | **57.1%** |
| **Leprosy** | 11 | 5 | 6 | 6 | 45.5% | 45.5% | 45.5% |
| **Soil-Transmitted Helminths** | 11 | 3 | 5 | 8 | 37.5% | 27.3% | 31.6% |
| **Neurocysticercosis** | 10 | 6 | 3 | 4 | **66.7%** | **60.0%** | **63.2%** |
| **Schistosomiasis** | 10 | 6 | 6 | 4 | **50.0%** | **60.0%** | **54.5%** |
| **Talaromycosis** | 10 | 7 | 10 | 3 | 41.2% | **70.0%** | **51.9%** |
| **Trypanosomiasis** | 9 | 1 | 1 | 8 | **50.0%** | 11.1% | 18.2% |
| **Melioidosis** | 8 | 3 | 49 | 5 | 5.8% | 37.5% | 10.0% |
| **Scrub Typhus** | 7 | 0 | 5 | 7 | 0.0% | 0.0% | 0.0% |
| **Amebiasis** | 6 | 0 | 0 | 6 | 0.0% | 0.0% | 0.0% |
| **Viral Hemorrhagic Fevers** | 6 | 0 | 0 | 6 | 0.0% | 0.0% | 0.0% |
| **Paracoccidioidomycosis** | 5 | 3 | 5 | 2 | 37.5% | **60.0%** | 46.2% |
| **Foodborne Trematodes** | 4 | 0 | 1 | 4 | 0.0% | 0.0% | 0.0% |
| **Mycetoma** | 4 | 2 | 6 | 2 | 25.0% | **50.0%** | 33.3% |
| **Scabies** | 4 | 1 | 2 | 3 | 33.3% | 25.0% | 28.6% |
| **Zika Virus** | 4 | 3 | 1 | 1 | **75.0%** | **75.0%** | **75.0%** |
| **Cholera** | 2 | 1 | 1 | 1 | **50.0%** | **50.0%** | **50.0%** |
| **OVERALL (Macro Average)** | — | — | — | — | **38.1%** | **40.5%** | **37.2%** |
| **OVERALL (Weighted Average)** | **365** | **176** | — | — | **55.3%** | **47.7%** | **48.6%** |

---

## 4. Per-Class Tolerant Differential Metrics (No Penalty for Valid Co-Differentials)

In this **Tolerant Differential Paradigm**, when a patient's true pathogen is safely captured in the Top-3 list, the other two differential hypotheses are considered legitimate clinical considerations rather than false positives. A **Hazardous False Positive (HazFP)** is only recorded if a disease was recommended when the patient's true disease was completely missed.

| Tropical Disease Class | Support ($N$) | TP@3 | HazFP | FN@3 | Tolerant Precision | Tolerant Recall | Tolerant F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tuberculosis** | 129 | 93 | 31 | 36 | **75.0%** | **72.1%** | **73.5%** |
| **Echinococcosis** (Hydatid) | 44 | 39 | 8 | 5 | **83.0%** | **88.6%** | **85.7%** |
| **Leishmaniasis** | 28 | 25 | 27 | 3 | **48.1%** | **89.3%** | **62.5%** |
| **Dengue** | 23 | 14 | 13 | 9 | **51.9%** | **60.9%** | **56.0%** |
| **Malaria** | 19 | 17 | 27 | 2 | **38.6%** | **89.5%** | **54.0%** |
| **Leptospirosis** | 15 | 13 | 9 | 2 | **59.1%** | **86.7%** | **70.3%** |
| **Leprosy** | 11 | 7 | 12 | 4 | **36.8%** | **63.6%** | **46.7%** |
| **Soil-Transmitted Helminths** | 11 | 8 | 18 | 3 | **30.8%** | **72.7%** | **43.2%** |
| **Neurocysticercosis** | 10 | 9 | 6 | 1 | **60.0%** | **90.0%** | **72.0%** |
| **Schistosomiasis** | 10 | 8 | 16 | 2 | **33.3%** | **80.0%** | **47.1%** |
| **Talaromycosis** | 10 | 7 | 19 | 3 | **26.9%** | **70.0%** | **38.9%** |
| **Trypanosomiasis** | 9 | 2 | 1 | 7 | **66.7%** | 22.2% | **33.3%** |
| **Melioidosis** | 8 | 6 | 52 | 2 | 10.3% | **75.0%** | 18.2% |
| **Paracoccidioidomycosis** | 5 | 4 | 19 | 1 | 17.4% | **80.0%** | 28.6% |
| **Amebiasis** | 6 | 3 | 4 | 3 | **42.9%** | **50.0%** | **46.2%** |
| **Mycetoma** | 4 | 3 | 18 | 1 | 14.3% | **75.0%** | 24.0% |
| **Zika Virus** | 4 | 3 | 5 | 1 | **37.5%** | **75.0%** | **50.0%** |
| **Cholera** | 2 | 1 | 0 | 1 | **100.0%** | **50.0%** | **66.7%** |
| **Viral Hemorrhagic Fevers** | 6 | 1 | 1 | 5 | **50.0%** | 16.7% | 25.0% |
| **Scabies** | 4 | 1 | 3 | 3 | 25.0% | 25.0% | 25.0% |
| **Scrub Typhus** | 7 | 0 | 6 | 7 | 0.0% | 0.0% | 0.0% |
| **Foodborne Trematodes** | 4 | 0 | 0 | 4 | 0.0% | 0.0% | 0.0% |
| **OVERALL (Macro Average)** | — | — | — | — | **41.3%** | **60.6%** | **43.9%** |
| **OVERALL (Weighted Average)** | **365** | **264** | — | — | **57.6%** | **71.5%** | **60.9%** |

---

## 5. Master Per-Disease Ablation Comparison (Tier 0 vs. Tier 1 vs. Tier 2 vs. Stage 4)

| Tropical Disease Class | Cohort ($N$) | Tier 0 Top-1 | Tier 1 Top-1 | Tier 2 Top-1 | **Stage 4 Top-1** | **Stage 4 Top-3** | Stage 4 Pred #1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Amebiasis** | 5 | 0.0% | 0.0% | 0.0% | **0.0%** | **60.0%** | 0 |
| **Cholera** | 2 | 0.0% | 0.0% | 0.0% | **50.0%** | **50.0%** | 2 |
| **Dengue** | 22 | 4.3% | 21.7% | 26.1% | **22.7%** | **63.6%** | 17 |
| **Echinococcosis** (Hydatid) | 43 | 2.3% | 40.9% | 59.1% | **86.0%** | **90.7%** | 59 |
| **Foodborne Trematodes** | 4 | 0.0% | 0.0% | 0.0% | **0.0%** | **0.0%** | 1 |
| **Leishmaniasis** | 28 | 3.6% | 17.9% | 17.9% | **75.0%** | **89.3%** | 39 |
| **Leprosy** | 10 | 9.1% | 9.1% | 27.3% | **50.0%** | **70.0%** | 11 |
| **Leptospirosis** | 14 | 6.7% | 13.3% | 6.7% | **57.1%** | **85.7%** | 13 |
| **Malaria** | 19 | 15.8% | 21.1% | 21.1% | **42.1%** | **89.5%** | 22 |
| **Melioidosis** | 8 | 87.5% | 62.5% | 62.5% | **37.5%** | **75.0%** | 52 |
| **Mycetoma** | 4 | 25.0% | 25.0% | 50.0% | **50.0%** | **75.0%** | 8 |
| **Neurocysticercosis** | 10 | 50.0% | 20.0% | 20.0% | **60.0%** | **90.0%** | 9 |
| **Paracoccidioidomycosis** | 5 | 0.0% | 20.0% | 0.0% | **60.0%** | **80.0%** | 8 |
| **Scabies** | 4 | 0.0% | 50.0% | 50.0% | **25.0%** | **25.0%** | 3 |
| **Schistosomiasis** | 9 | 10.0% | 20.0% | 10.0% | **66.7%** | **88.9%** | 12 |
| **Scrub Typhus** | 7 | 0.0% | 0.0% | 0.0% | **0.0%** | **0.0%** | 5 |
| **Soil-Transmitted Helminths** | 11 | 0.0% | 18.2% | 0.0% | **27.3%** | **72.7%** | 8 |
| **Talaromycosis** | 10 | 0.0% | 20.0% | 30.0% | **70.0%** | **70.0%** | 17 |
| **Trypanosomiasis** | 8 | 11.1% | 0.0% | 0.0% | **12.5%** | **25.0%** | 2 |
| **Tuberculosis** | 128 | 4.7% | 57.4% | 64.3% | **43.8%** | **72.7%** | 72 |
| **Viral Hemorrhagic Fevers** | 6 | 0.0% | 0.0% | 0.0% | **0.0%** | **16.7%** | 0 |
| **Zika Virus** | 4 | 0.0% | 75.0% | 75.0% | **75.0%** | **75.0%** | 4 |
| **Multi-pathogen / Edge Cases** | 4 | — | — | — | **0.0%** | **0.0%** | — |
| **OVERALL TOTAL** | **365** | **7.95%** | **35.07%** | **39.73%** | **48.22%** | **72.33%** | **365** |

---

## 6. Forensic Data Leakage & Pipeline Integrity Audit

A comprehensive forensic audit was conducted across 5 potential leakage vectors to verify that these results reflect true generalizable clinical inference:

1. **Patient / Publication Overlap (Train-Test Contamination): CLEAN (0% Leakage)**
   - Test cases: 365 PMC case reports.
   - Episodic memory training cases: 1,427 PubMed Central case reports.
   - **Direct Case ID Overlap:** **0**
   - **Base PMC Publication Overlap:** **0**
   - Zero patient vignettes or source papers in the test cohort were present in the Stage 2 training memory.

2. **Knowledge Graph Contamination (Stage 1): CLEAN (0% Leakage)**
   - The Canonical KG was constructed exclusively from peer-reviewed disease reviews, WHO guidelines, and textbook chapters across the 22 diseases.
   - **Test PMC mentions in KG chunks:** **0**

3. **Input Narrative Masking (`masked_text`): ROBUST (99.7% Clean)**
   - **364 / 365 cases (99.7%)** contain zero mentions of pathogen names, diagnostic terms, or ground-truth disease labels in the clinical vignette presented to the model.
   - Only 1 case (`PMC12544461_01`) contained a single descriptive adjective ("tuberculous").

4. **Syndromic Search Clues (`remaining_clues`): NEGLIGIBLE (<0.6% Leakage)**
   - In 363 / 365 cases (99.45%), extracted search keywords were purely syndromic signs (e.g., `complete block interatrial`, `high grade fever`).
   - Only 2 cases (0.55%) contained a disease term (`PMC4317211_01`, `PMC6713851_02`).

5. **Evaluation Metric Accuracy: 100% Exact Matching**
   - All 176 Top-1 positive matches are **100% exact canonical class matches**.
   - Zero false-positive substring or partial-word matches.

---

## 7. Case-Based Reasoning & Model Independence Analysis

Stage 2 retrieves real confirmed clinical twins from historical memory. Precedent 1 matched the ground-truth diagnosis in 55.34% of cases.

**Did the SLM simply memorize or copy Precedent 1?**
- **No.** The model selected `matched_precedent: Precedent 1` in **only 21.6% of cases** (79 / 365).
- In **77.5% of cases** (283 / 365), the model rejected both precedents as insufficient or contradictory, explicitly choosing **"Neither"**.
- When the model agreed with Precedent 1 ($n = 79$): Top-1 accuracy was **83.54%**.
- When the model chose "Neither" ($n = 286$) and reasoned independently from the Knowledge Graph: Top-1 accuracy was **38.46%** (vastly above the 25.48% baseline and random chance of $4.5\%$).

---

## 8. Pipeline Artifacts
- **Benchmark Runner:** [`stage4_constrained_inference/benchmark_stage4_cot.py`](benchmark_stage4_cot.py)
- **Full Results CSV:** [`stage4_constrained_inference/stage4_results.csv`](stage4_results.csv)
- **Prompt Specification:** [`stage4_constrained_inference/MICRO_COT_PROMPT_SPECIFICATION.md`](MICRO_COT_PROMPT_SPECIFICATION.md)
