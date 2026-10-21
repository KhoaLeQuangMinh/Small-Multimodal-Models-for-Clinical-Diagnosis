# Stage 2: MedCaseReasoning Distillation & Vector Case Memory (The Episodic Brain)

## 🎯 Objective
Distill the **1,427 real-world training cases** (`train_kg_cases.jsonl`) into structured **MedCaseReasoning Clinical Profiles** using Gemini 1.5 Flash, and index them into an ultra-fast **Episodic Vector Case Memory** for **Case-Based Reasoning (CBR)**.

---

## 🧭 Role in the Big Picture: The "Clinician's Dual-Brain"

Under the **Dual-Brain Architecture** (supported by Stanford's *MedCaseReasoning*, Microsoft *GraphRAG*, and *MedRAG*), clinical diagnosis is split into two specialized memory stores:

```
                            [ Unseen Masked Test Patient ]
                                           │
                  ┌────────────────────────┴────────────────────────┐
                  ▼                                                 ▼
     [ 1. SEMANTIC BRAIN (Stage 1) ]                   [ 2. EPISODIC BRAIN (Stage 2) ]
        Knowledge Graph (LightRAG)                        Vector Case Memory (FAISS/NumPy)
                  │                                                 │
    22 Canonical Disease Monographs                   1,427 Distilled MedCase Profiles
   "Textbook Criteria & Exclusions"                   "Historical Real-World Patient Twins"
                  │                                                 │
                  ▼                                                 ▼
        Top 15 Graph Triples                              Top 2 "Patient Twins"
                  └────────────────────────┬────────────────────────┘
                                           ▼
                             [ Synthesized Prompt to SLM ]
                                     (Qwen2.5-3B)
```

### Why Decouple the 1,427 Cases from the Graph?
1. **Prevents Mega-Hub Explosion:** If 1,427 patients are added directly to the knowledge graph, diseases like *Tuberculosis* (518 cases) end up with massive degree skew, burying rare diseases and creating graph traversal bottlenecks.
2. **Specialized Representation:**
   * **Graphs** are best for **abstract rules, hierarchies, and exclusions** (`Dengue ──[rules_out]──► Malaria`).
   * **Dense Vectors** are best for **analogical patient matching** (*"Find the 2 patients in hospital history whose admission presentation looks most identical to this patient"*).
3. **Speed & Efficiency:** Vector similarity lookup over 1,427 case vectors takes **~3 milliseconds** with zero graph traversal lag.

---

## ⚡ The MedCaseReasoning Profile Schema

Using the known ground-truth labels in `train_kg_cases.jsonl`, Gemini 1.5 Flash compresses each 2,000-word raw PMC narrative into a standardized, ~150-word clinical profile:

```json
{
  "case_id": "PMC10034413_01",
  "ground_truth": "Foodborne Trematodes",
  "subtype": "Paragonimiasis",
  "case_vignette": "A 45-year-old male presenting with chronic cough, hemoptysis, recurrent spontaneous pneumothorax, and marked peripheral eosinophilia following Missouri river rafting and wild game consumption.",
  "anchor_presentation": {
    "epidemiology": "Missouri river rafting, hunting, consumption of wild game (freshwater crab/crayfish vector risk).",
    "cardinal_signs": "Chronic cough, recurrent spontaneous pneumothorax, absence of toxic high fever.",
    "admission_labs": "Marked peripheral eosinophilia (AEC > 1200 cells/µL, 11.3%), sterile pleural fluid cultures.",
    "treatment_response": "Cured following a 3-day course of oral Praziquantel."
  },
  "differential_rule_outs": [
    {
      "candidate": "Tuberculosis",
      "rule_out_reason": "Severe peripheral eosinophilia is uncharacteristic of uncomplicated TB; lack of apical cavitary necrosis; failed standard antibacterials."
    },
    {
      "candidate": "Bacterial Empyema / Lung Abscess",
      "rule_out_reason": "Sterile pleural fluid cultures and chronic 12-month smoldering timeline."
    }
  ],
  "discriminative_keywords": [
    "Missouri river", "pneumothorax", "eosinophilia", "praziquantel", "hemoptysis", "wild boar"
  ]
}
```

---

## 🛡️ Critical Safety Rule: Admission-Phase Temporal Constraint

> [!IMPORTANT]
> **Gemini Flash MUST anchor only on admission-accessible clinical findings.**
> 
> In our unseen test set (`test_masked_cases.jsonl`), all confirmatory PCR, serology titers, and biopsy organisms are masked with `[MASK]`.
> If the training profile states: *"Anchor finding: Confirmed because PCR grew Burkholderia pseudomallei"*, a test patient at admission will never match this profile.
> 
> Distillation must anchor strictly on:
> * Exposure history (geography, freshwater, animals, insect bites).
> * Cardinal physical examination signs (rashes, eschars, organomegaly).
> * Initial triage laboratory results (CBC with differential, LFTs, basic urinalysis, bedside ultrasound).
> * Empirical treatment responses (e.g. rapid defervescence within 48h of Doxycycline).

---

## 🔍 How the "Patient Twin" Retrieval Works During Inference

When an unseen test case is evaluated:
1. **Dense Vector Search:** The test case narrative is embedded with `all-MiniLM-L6-v2` (384 dimensions) and compared against the 1,427 pre-computed case profile embeddings.
2. **Top-2 Twin Selection:** The system retrieves the **top 2 most semantically similar historical patients**.
3. **Exemplar Injection:** The retrieved profiles are formatted as clean clinical precedents into the Qwen2.5-3B prompt:
   ```text
   ### HISTORICAL CLINICAL PRECEDENTS (Closest Real-World Patient Cases):
   [Precedent 1 - Confirmed Scrub Typhus (Similarity: 0.88)]:
   - Presentation: Young female with fever, abdominal eschar, ARDS, cured by doxycycline.
   - Ruled out Dengue: Due to eschar and ARDS; smear negative for Malaria.

   [Precedent 2 - Confirmed Leptospirosis (Similarity: 0.74)]:
   - Presentation: Severe febrile illness with marked jaundice and renal impairment.
   ```

This gives Qwen2.5-3B an immediate, concrete real-world comparison to anchor its reasoning.

---

## 🛠️ Step-by-Step Execution Plan for Stage 2

1. **Verify Training Split:** Confirm the 1,427 cases in `train_kg_cases.jsonl`.
2. **Implement Distillation Script (`distill_cases.py`):**
   - Asynchronously batch-calls Gemini 1.5 Flash API with the Admission-Constrained prompt.
   - Implements exponential backoff and rate-limit handling.
   - Saves output to `train_medcase_profiles.jsonl`.
3. **Build the Vector Store Index:**
   - Embed all 1,427 `case_vignette` strings using `all-MiniLM-L6-v2`.
   - Save pre-computed embeddings matrix (`train_medcase_embeddings.npy`) and lookup metadata.
4. **Unit Test Retrieval Speed & Precision:**
   - Run a test query against the vector store to verify that twin cases are retrieved in < 5ms with high clinical relevance.
