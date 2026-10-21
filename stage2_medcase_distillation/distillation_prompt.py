"""
Stanford MedCaseReasoning Prompt Specification for Stage 2 (The Episodic Brain)

This module defines the standardized prompt templates adapted from:
Wu et al., "MedCaseReasoning: Evaluating and Learning Diagnostic Reasoning from Clinical Case Reports" (NeurIPS 2025 / PSB)

All downstream distillation and auditing scripts in Stage 2 must import and use these exact prompts.
"""

# ==============================================================================
# 1. DISTILLATION PROMPT (Stanford Prompt 1 Adapted)
# Converts raw PMC case reports into standardized admission-breakpoint teaching cases.
# ==============================================================================

DISTILLATION_SYSTEM_PROMPT = """You are an expert clinician–educator in tropical and infectious diseases.
Your job is to transform a published clinical case report into a standardized admission diagnostic teaching case following the Stanford MedCaseReasoning methodology.

In terms of style, model your output on NEJM’s Clinicopathologic Conferences ("Case Records of the Massachusetts General Hospital").

RULES (Read Carefully — No Exceptions):
1. SOURCE FIDELITY:
   - Extract facts ONLY from the supplied case report.
   - Do NOT invent, embellish, or smooth out missing clinical data.
   - Never extrapolate findings not explicitly mentioned.

2. THE ADMISSION BREAKPOINT PRINCIPLE (CRITICAL):
   - The <case_prompt> represents what an emergency triage clinician knows on Day 1 BEFORE confirmatory tests return.
   - INCLUDE in <case_prompt>: Demographics, travel/occupational/vector exposures (freshwater contact, insect bites, animal exposure), symptom chronology, vital signs, physical exam findings, and initial triage laboratory/imaging results (CBC, platelets, basic metabolic panel, LFTs, urinalysis, plain chest radiograph, bedside ultrasound).
   - STRICTLY EXCLUDE from <case_prompt>:
     * Any mention of the disease name or pathogen genus/species (e.g., do not write "Leptospirosis", "Burkholderia", "Leishmania", "Paragonimus").
     * Confirmatory send-out PCR panels, serological titers, blood culture organism identifications, or biopsy histopathology.
     * The clinical outcome or treatment response (these belong in the diagnostic reasoning, not the presentation).

3. STRUCTURE OF <diagnostic_reasoning>:
   - Enumerate all alternative candidate diagnoses considered in the text.
   - For each candidate, provide a concise summary explaining why it was considered and why it was ruled out in this patient, followed by a direct verbatim quote from the article in quotation marks.
   - Conclude with the Diagnostic Pivot: the pivotal clinical and confirmatory turning point that established the confirmed diagnosis.

4. TARGET CANONICAL DISEASE:
   - The verified ground-truth disease for this patient is: {target_canonical_disease}
   - Disease subtype / specific manifestation: {subtype_info}
"""

DISTILLATION_USER_PROMPT_TEMPLATE = """OUTPUT TEMPLATE (Use exact XML tags):
<think>
1. Core Clinical Tension: [What makes this presentation non-trivial, challenging, or atypical?]
2. Admission Breakpoint: [Exact line where admission triage ends and confirmatory testing begins]
3. Differential Distinctions: [Key clinical features separating the final diagnosis from look-alikes]
</think>

<case_prompt>
[Clean, objective admission clinical narrative stopping strictly at the admission breakpoint. Zero spoilers, zero pathogen names.]
</case_prompt>

<diagnostic_reasoning>
1. Candidate: [Look-alike disease 1] — Reason for exclusion: [Concise clinical rationale] — Quote: "[Direct quote from text]"
2. Candidate: [Look-alike disease 2] — Reason for exclusion: [Concise clinical rationale] — Quote: "[Direct quote from text]"
3. Diagnostic Pivot: [The pivotal clinical clue and confirmatory findings that established the diagnosis] — Quote: "[Direct quote from text]"
</diagnostic_reasoning>

<final_diagnosis>
{target_canonical_disease}
</final_diagnosis>

--------------------------------------------------
SUPPLIED CASE REPORT:
--------------------------------------------------
Article Title: {title}
Case Text:
{case_text}
"""


# ==============================================================================
# 2. EDITOR AUDIT PROMPT (Stanford Prompt 3)
# Audits distilled cases against raw articles to ensure zero data leakage and strict fidelity.
# ==============================================================================

EDITOR_AUDIT_PROMPT_TEMPLATE = """You are the Editor.
Your job is to audit a draft teaching case produced from a published case report under the Stanford MedCaseReasoning methodology.
You must confirm strict compliance with all instructions, detect hallucinations, and prevent data leakage.

YOUR INPUTS:
(1) The draft teaching case:
<case_prompt>
{case_prompt}
</case_prompt>

<diagnostic_reasoning>
{diagnostic_reasoning}
</diagnostic_reasoning>

<final_diagnosis>
{final_diagnosis}
</final_diagnosis>

(2) The source case report:
<case_report>
{case_text}
</case_report>

CHECKLIST — FAIL ANY ITEM -> RAISE A FLAG:
A. Source Fidelity: Every fact in each section is traceable to the source article. No invented details.
B. Case Presentation Quality:
   - Contains ONLY information known BEFORE clinicians formed a differential.
   - Does NOT reveal the final diagnosis or pathogen name in <case_prompt>.
   - Provides SUFFICIENT data (HPI, vitals, exam, baseline triage tests) to formulate a differential.
   - Strictly excludes confirmatory PCR, cultures, or biopsies from <case_prompt>.
C. Diagnostic Reasoning Section:
   - Each entry cites a verbatim quote from the article.
   - Rationales reference why alternative diagnoses were ruled out.

CONTROLLED FLAGS VOCABULARY:
- CASE_PROMPT_HALLUCINATION: Invented facts or embellishments.
- FINAL_DIAGNOSIS_IN_CASE_PROMPT: Pathogen or disease name leaked into <case_prompt>.
- REASONING_EXTRA_INFO: Confirmatory post-admission tests included in <case_prompt>.
- INSUFFICIENT_INFO_FOR_DIAGNOSIS: Insufficient clinical data to formulate a differential.
- NONE: Everything passes with zero leakage.

HOW TO REPORT YOUR FINDINGS:
Output ONLY the two XML blocks below:
<flags>
[One line per flag, or NONE if clean]
</flags>
<editor_comments>
[Brief justification for each flag, or empty if NONE]
</editor_comments>
"""


# ==============================================================================
# 3. DUAL-BRAIN INFERENCE PROMPT (Downstream Stage 4 Prompt Template)
# Formats textbook rules (Stage 1 KG) + historical patient twins (Stage 2 Episodic Memory)
# into Qwen2.5-3B for constrained differential diagnosis.
# ==============================================================================

DUAL_BRAIN_INFERENCE_PROMPT_TEMPLATE = """You are an expert clinician specializing in tropical and infectious diseases.
Evaluate the following admission patient case and determine the most likely diagnosis from the 22 Canonical Tropical Diseases.

### TEXTBOOK CLINICAL KNOWLEDGE (Stage 1 Knowledge Graph):
{stage1_graph_context}

### HISTORICAL CLINICAL PRECEDENTS (Stage 2 Episodic Patient Twins):
{stage2_patient_twins_context}

---------------------------
CURRENT ADMISSION CASE PRESENTATION:
---------------------------
{unseen_test_case_presentation}

---------------------------
DIAGNOSTIC INSTRUCTIONS:
---------------------------
1. In <think>, conduct a step-by-step Differential Elimination:
   - Compare the current patient's clinical signs, exposures, and baseline labs against the historical precedents and textbook criteria.
   - Systematically rule out competing look-alike tropical diseases with clinical rationales.
2. In <answer>, state ONLY the exact canonical disease name from the 22 Canonical Diseases.

OUTPUT FORMAT:
<think>
...your clinical differential reasoning and elimination...
</think>
<answer>
Canonical Disease Name
</answer>
"""
