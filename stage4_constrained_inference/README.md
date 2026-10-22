# Stage 4: Constrained Diagnostic CoT for Small Language Model

## 🎯 Objective
Formulate and execute a **Constrained Diagnostic Chain-of-Thought (CoT)** inference pipeline tailored for the Small Language Model (`qwen2.5:3b`), evaluating all **365 masked admission test cases** ([`data/test_masked_cases.jsonl`](../data/test_masked_cases.jsonl)) against the weighted clinical knowledge graph.

---

## 🧭 Role in the Big Picture

A 3-Billion parameter model cannot reliably perform open-ended, multi-class differential diagnosis if asked directly: *"What does this patient have?"*
* **The Baseline Failure:** Without constraints, Qwen2.5-3B exhibits massive attractor bias—guessing **Melioidosis in 55.3% of all cases** (202 out of 365 cases), resulting in an abysmal 7.95% Top-1 accuracy.
* **The CoT Steering Mechanism:** In auto-regressive generation, every previously generated token conditions the next token's probability distribution. 
  By forcing Qwen2.5-3B to write out **differential hypotheses** and **explicit clinical rule-outs** *before* emitting the final diagnosis, we force the model's self-attention to deliberate over the clinical evidence, steering it away from attractor traps directly toward the correct disease label.

---

## 📝 The Constrained Diagnostic CoT Prompt

### 1. System Prompt
```text
You are an expert Infectious Disease Physician specializing in Tropical and Neglected Diseases.
Your task is to analyze an admission clinical case presentation where final diagnostic tests are masked.
You are augmented with retrieved medical knowledge graph evidence from 22 canonical tropical disease profiles and historical patient cases.

Synthesize the patient's presentation with the retrieved clinical facts to formulate the correct diagnosis.

CONSTRAINTS:
1. You MUST select your candidate diseases strictly from the 22 canonical tropical disease classes.
2. Formulate your reasoning using the required differential elimination structure.
3. Output strictly a valid JSON object matching the requested schema. No conversational preamble.
```

### 2. Output Schema
```json
{
  "differential_hypotheses": [
    "<Primary Candidate from 22 diseases>",
    "<Second Candidate from 22 diseases>",
    "<Third Candidate from 22 diseases>"
  ],
  "rule_out_rationale": [
    "Rule out <Second Candidate>: [1 concise sentence citing pertinent negative, mismatched exposure, or lab discrepancy]",
    "Rule out <Third Candidate>: [1 concise sentence citing pertinent negative, mismatched exposure, or lab discrepancy]"
  ],
  "rule_in_anchor": "Anchor <Primary Candidate>: [1 concise sentence citing pathognomonic finding, clinical timeline, or empirical drug response matching evidence]",
  "final_diagnosis": "<Exact primary disease name strictly matching one of the 22 candidate classes>"
}
```

---

## 🔬 Target Evaluation Metrics

| Metric | Target | Formula | Clinical Purpose |
|---|:---:|---|---|
| **Top-1 Diagnostic Accuracy** | **$\ge 55\text{–}65\%$** | $\frac{\text{Hits}(\text{final\_diagnosis} = \text{Ground Truth})}{365}$ | Primary diagnosis accuracy matching the true etiology. |
| **Top-3 Differential Coverage** | **$\ge 75\text{–}85\%$** | $\frac{\text{Hits}(\text{Ground Truth} \in \text{differential\_hypotheses})}{365}$ | Ensures the true disease is safely captured in the initial workup. |
| **Melioidosis Attractor Rate** | **$\le 10\%$** | $\frac{\text{Count}(\text{final\_diagnosis} = \text{Melioidosis})}{365}$ | Measures elimination of systemic prior-distribution hallucination. |
| **Differential Elimination Recall** | **$\ge 80\%$** | Human-in-the-loop / LLM-judge audit | Confirms clinical validity of the rule-out statements. |

---

## 🛠️ Step-by-Step Execution Plan for Stage 4

1. **Implement `benchmark_stage4_cot.py`:**
   - Integrates the weighted graph context from Stage 3 and canonical profiles from Stage 1.
   - Enforces the structured CoT JSON output schema.
   - Implements per-case instant disk flushing (`a` append mode) and automatic checkpoint resume.
2. **Execute Full Cohort Evaluation:**
   - Run across all 365 masked admission test cases on local Ollama (`qwen2.5:3b`).
3. **Compute Comparative Ablation Metrics:**
   - Compare Stage 4 results against:
     - Tier 0 Baseline (7.95% Top-1, 32.05% Top-3)
     - Tier 1 Graph-Only (35.07% Top-1, 47.95% Top-3)
     - Tier 2 Hybrid RAG (39.73% Top-1, 52.60% Top-3)
4. **Publish Master Report:**
   - Document complete per-disease confusion matrices and differential capture rates in [`docs/RESULT.md`](../docs/RESULT.md).
