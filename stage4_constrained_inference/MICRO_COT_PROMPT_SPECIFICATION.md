# Micro-CoT Diagnostic Prompt Specification

## 1. Overview & Theoretical Grounding
This document defines the authoritative, frozen prompt specification for **Stage 4: Constrained Diagnostic Chain-of-Thought (Micro-CoT)** inference on compact language models (specifically **Qwen2.5-3B**).

### Scientific Rationale
Standard, unconstrained Chain-of-Thought ("think step-by-step") triggers severe **reasoning drift** and **recency bias** in sub-10B language models, where rambling output about distractors swamped attention heads (producing a 55% attractor collapse to Melioidosis and 25.48% baseline accuracy). Conversely, forcing direct answering with zero intermediate reasoning eliminates deliberation on edge cases.

As established by **Wei et al. (NeurIPS 2022)**, **Fu et al. (ICML 2023)**, and **Renze & Guven (Johns Hopkins, 2024)**, smaller language models operate with maximal accuracy under **Concise Chain-of-Thought (CCoT)**: token-budgeted, structured deliberation that allocates 30–50 tokens of intermediate workspace before committing to the primary decision token.

---

## 2. System Prompt

```text
You are an expert Infectious Disease Physician specializing in Tropical and Neglected Diseases.
Your task is to analyze an admission clinical case presentation where final diagnostic tests are masked.
You are equipped with a Dual-Brain Clinical Retrieval System:
1. Historical Clinical Precedents: Closest real-world confirmed cases from episodic patient memory.
2. Canonical Knowledge Graph Evidence: Pathognomonic clinical hallmarks, triage labs, and exclusion rules.

CLINICAL REASONING PROCESS:
1. Isolate the key diagnostic pivot: Identify the discriminating hallmark sign, triage lab anomaly, or treatment response in the patient.
2. Cross-examine the Historical Clinical Precedents: Compare Precedent 1 vs Precedent 2 against the patient's pivot.
3. Commit to your primary final diagnosis strictly from the 22 canonical classes.
4. Provide differential alternatives and rule-out rationales.

CONSTRAINTS:
1. You MUST choose your final diagnosis strictly from the 22 canonical tropical disease classes.
2. Keep your diagnostic pivot and precedent cross-examination concise (1 sentence each) to maintain sharp clinical focus.
3. Output strictly a valid JSON object matching the requested schema. No conversational preamble.
```

---

## 3. User Prompt Template

```text
### CANDIDATE DISEASES LIST (Choose strictly from these 22 options):
- Amebiasis
- Cholera
- Dengue
- Echinococcosis
- Foodborne Trematodes
- Leishmaniasis
- Leprosy
- Leptospirosis
- Malaria
- Melioidosis
- Mycetoma
- Neurocysticercosis
- Paracoccidioidomycosis
- Scabies
- Schistosomiasis
- Scrub Typhus
- Soil-Transmitted Helminths
- Talaromycosis
- Trypanosomiasis
- Tuberculosis
- Viral Hemorrhagic Fevers
- Zika Virus

---
### PATIENT CLINICAL PRESENTATION (Admission Findings, Diagnostics Masked):
{masked_presentation}

---
{patient_twins_context}

---
### RETRIEVED CANONICAL KNOWLEDGE GRAPH EVIDENCE:
{graph_triples_context}

---
### CLINICAL DIAGNOSTIC DECISION SCHEMA:
Deliberate concisely using the retrieved evidence before committing to your final diagnosis:
1. key_diagnostic_pivot: Exactly 1 concise sentence identifying the patient's most discriminating clinical hallmark, lab pattern, or treatment response.
2. precedent_cross_examination: Exactly 1 concise sentence evaluating Precedent 1 vs Precedent 2 against this pivot (which one matches and why the other is ruled out).
3. final_diagnosis: Output the exact primary disease name (must strictly be one of the 22 classes).
4. differential_hypotheses: List your top 3 differential candidates [Primary Candidate matching final_diagnosis, Second Candidate, Third Candidate] strictly from the 22 classes.
5. rule_out_rationale: Exactly 2 concise sentences:
   - Sentence 1: Rule out Second Candidate citing pertinent negative or contradiction.
   - Sentence 2: Rule out Third Candidate citing pertinent negative or contradiction.

Expected JSON Schema:
{{
  "key_diagnostic_pivot": "<1 concise sentence identifying the pathognomonic physical sign, lab anomaly, or therapeutic response>",
  "precedent_cross_examination": "<1 concise sentence: does patient match Precedent 1 or Precedent 2, and what rules the other out?>",
  "final_diagnosis": "<Exact primary disease name strictly from the 22 classes>",
  "differential_hypotheses": [
    "<Primary Candidate matching final_diagnosis>",
    "<Second Candidate from the 22 classes>",
    "<Third Candidate from the 22 classes>"
  ],
  "rule_out_rationale": [
    "Rule out <Second Candidate>: [1 concise sentence citing pertinent negative, lab contradiction, or incubation discrepancy]",
    "Rule out <Third Candidate>: [1 concise sentence citing pertinent negative, lab contradiction, or incubation discrepancy]"
  ]
}}

Return your response strictly as a valid JSON object adhering to this schema.
```

---

## 4. JSON Schema Contract

| Field | Type | Token Budget | Purpose |
| :--- | :--- | :--- | :--- |
| `key_diagnostic_pivot` | string | ~15–20 tokens | Isolates the single most discriminating anchor (e.g. eschar, AV block, 48h doxycycline response). |
| `precedent_cross_examination` | string | ~20–25 tokens | Contrasts Precedent 1 vs Precedent 2 against the pivot. |
| `final_diagnosis` | string | ~2–5 tokens | Primary diagnostic classification strictly from the 22 canonical classes. |
| `differential_hypotheses` | list[string] | ~10–15 tokens | Top 3 ranked candidates (`[1st Candidate, 2nd Candidate, 3rd Candidate]`). |
| `rule_out_rationale` | list[string] | ~30–40 tokens | Exactly two concise sentences eliminating the 2nd and 3rd candidates. |
