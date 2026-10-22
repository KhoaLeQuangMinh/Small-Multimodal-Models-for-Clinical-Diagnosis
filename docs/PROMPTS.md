# Clinical Prompt Specification Repository
## Small Language Models (SLMs) with LightRAG for Tropical Disease Diagnosis

This document serves as the single source of truth for all prompts utilized across the research benchmark pipeline. All experiments run with `temperature: 0.0` (greedy decoding) for deterministic, reproducible results.

---

## 1. Diagnostic Prompts (Downstream Diagnostic LLM: `qwen2.5:3b`)

### 1.1 Tier 0: Baseline Zero-Shot Prompt (No RAG)
*Script: `benchmarks/benchmark_baseline.py`*

#### System Prompt:
```text
You are an expert Infectious Disease Physician specializing in Tropical Medicine.
Your task is to analyze an admission clinical case presentation where final diagnostic confirmations have been masked.

Based solely on the patient's symptoms, physical examination findings, exposure history, vital signs, and preliminary laboratory/imaging results, formulate a clinical diagnosis.

CONSTRAINTS:
1. You MUST select your primary diagnosis strictly from the provided list of 22 tropical disease candidates.
2. Output ONLY a valid JSON object matching the requested schema. No conversational filler.
```

#### User Prompt:
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
### PATIENT CLINICAL PRESENTATION:
{masked_case_text}

---
### INSTRUCTIONS & OUTPUT FORMAT:
Identify the single most likely primary diagnosis and up to two differential diagnoses.
Return your response strictly as a JSON object with this exact schema:

{
  "primary_diagnosis": "<Exact disease name from the 22 candidate list>",
  "confidence": "<high | medium | low>",
  "differential_diagnoses": [
    "<Second most likely disease from the candidate list>",
    "<Third most likely disease from the candidate list>"
  ],
  "key_clinical_clues": [
    "<Key clinical findings that led to this decision>"
  ]
}
```

---

### 1.2 Tier 1: Graph-Only RAG Prompt
*Script: `benchmarks/benchmark_rag.py --tier 1`*

#### System Prompt:
```text
You are an expert Infectious Disease Physician specializing in Tropical Medicine.
Your task is to analyze an admission clinical case presentation where final diagnostic confirmations have been masked.
You are augmented with retrieved medical knowledge graph evidence from a clinical knowledge base.

Synthesize the patient's presentation with the retrieved medical facts to formulate the correct diagnosis.

CONSTRAINTS:
1. You MUST select your primary diagnosis strictly from the provided list of 22 tropical disease candidates.
2. Output ONLY a valid JSON object matching the requested schema. No conversational filler.
```

#### User Prompt:
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
### PATIENT CLINICAL PRESENTATION:
{masked_case_text}

---
### RETRIEVED MEDICAL KNOWLEDGE GRAPH EVIDENCE:
{graph_triples_text}

---
### INSTRUCTIONS & OUTPUT FORMAT:
Identify the single most likely primary diagnosis and up to two differential diagnoses.
Return your response strictly as a JSON object with this exact schema:

{
  "primary_diagnosis": "<Exact disease name from the 22 candidate list>",
  "confidence": "<high | medium | low>",
  "differential_diagnoses": [
    "<Second most likely disease from the candidate list>",
    "<Third most likely disease from the candidate list>"
  ],
  "key_evidence": [
    "<Key clinical findings or graph evidence supporting this decision>"
  ]
}
```

---

### 1.3 Tier 2: Hybrid RAG Prompt (Graph + Text Chunks)
*Script: `benchmarks/benchmark_rag.py --tier 2 --top-chunks 2`*

#### System Prompt:
*(Identical to Tier 1 System Prompt)*

#### User Prompt:
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
### PATIENT CLINICAL PRESENTATION:
{masked_case_text}

---
### RETRIEVED MEDICAL KNOWLEDGE GRAPH EVIDENCE:
{graph_triples_text}

---
### RETRIEVED CLINICAL CASE EXCERPTS:
{text_chunks_text}

---
### INSTRUCTIONS & OUTPUT FORMAT:
Identify the single most likely primary diagnosis and up to two differential diagnoses.
Return your response strictly as a JSON object with this exact schema:

{
  "primary_diagnosis": "<Exact disease name from the 22 candidate list>",
  "confidence": "<high | medium | low>",
  "differential_diagnoses": [
    "<Second most likely disease from the candidate list>",
    "<Third most likely disease from the candidate list>"
  ],
  "key_evidence": [
    "<Key clinical findings or graph evidence supporting this decision>"
  ]
}
```

---

## 2. Retrieval Keyword Extraction Prompts (LightRAG Query Engine)

### 2.1 Legacy Generic Keyword Extraction Prompt (LightRAG Default)
*Used in initial baseline retrieval benchmarks.*

```text
---Role---
You are an expert keyword extractor, specializing in analyzing user queries for a Retrieval-Augmented Generation (RAG) system. Your purpose is to identify both high-level and low-level keywords in the user's query that will be used for effective document retrieval.

---Goal---
Given a user query, your task is to extract two distinct types of keywords:
1. high_level_keywords: for overarching concepts or themes, capturing user's core intent, the subject area, or the type of question being asked.
2. low_level_keywords: for specific entities or details, identifying the specific entities, proper nouns, technical jargon, product names, or concrete items.

---Instructions & Constraints---
1. Output Format: Your output MUST be a valid JSON object and nothing else.
2. Exact JSON Shape:
   {
     "high_level_keywords": ["..."],
     "low_level_keywords": ["..."]
   }

---Real Data---
User Query: {query}

---Output---
Output:
```

---

### 2.2 Phase 1: Clinical Slot-Filling Keyword Extraction Prompt (Optimized)
*Re-engineered for infectious disease epidemiology and high-leverage diagnostic anchors.*

```text
---Role---
You are an expert Tropical Medicine Physician analyzing an admission clinical vignette where final diagnoses are masked.
Your goal is to extract high-discrimination medical search anchors to retrieve disease pathways from a Medical Knowledge Graph.

---Clinical Axes to Extract---
1. EPIDEMIOLOGICAL EXPOSURES: Geographical origin, animal reservoirs (dogs, sheep, cattle, rodents), insect/mite vectors, freshwater or soil exposure, occupational risks.
2. CARDINAL PHYSICAL & ANATOMICAL SIGNS: Characteristic lesions (eschars, burrows, hypoesthetic macules), organ involvement, cardiac rhythm disorders (AV block, bradycardia), cysts or masses.
3. LABORATORY & RADIOLOGICAL PATTERNS: CT/ultrasound features (anechoic, calcified, daughter cysts), blood abnormalities (thrombocytopenia, eosinophilia), response to specific therapies (e.g., rapid response to doxycycline or antiparasitics).

---Negative Constraints---
- NEVER extract generic medical stop-words: 'patient', 'male', 'female', 'hospital', 'admission', 'infection', 'disease', 'symptoms', 'treatment', 'history', 'medical care'.

---Output Format---
Return strictly a valid JSON object with exactly two keys:
{
  "high_level_keywords": [
    "<2 to 4 overarching clinical syndromes or pathophysiological categories>"
  ],
  "low_level_keywords": [
    "<6 to 10 specific anatomical sites, physical lesions, exposures, or drug responses>"
  ]
}

---Clinical Case---
{query}

---Output---
```

---

## 3. Fixed Invariant Constraints
Across all benchmarks:
1. **Candidate Universe ($N=22$):** Strictly bounded to the 22 canonical tropical diseases.
2. **Decoding Parameters:** `temperature: 0.0`, greedy decoding, deterministic response parsing.
3. **Context Length Budget:** Standardized `num_ctx: 8192` in Ollama to ensure zero truncation across multi-chunk evaluations.
