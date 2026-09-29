# Decoupled Knowledge Graph Triplet Extraction

This directory contains the pipeline to extract high-quality clinical entities and relationship triplets from all 1,797 verified tropical disease cases using Antigravity subagents.

---

## 📁 Directory Structure

```text
kg_extraction/
├── runner.md                    # Driving prompt to paste into Antigravity
├── prompt.md                    # Reference copy of the extraction prompt
├── prepare_case_prompts.py      # Generates 1,797 prompt files from partA_final.jsonl
├── validate_triplets.py         # Validates and summarizes extracted JSON files
├── case_prompts/                # 1,797 self-contained prompt files (.txt)
└── extracted_triplets/          # Output directory for extracted triplets (.json)
```

---

## 🚀 How to Run the Subagent Extraction

1. Open this folder (`kg_extraction/`) in **Google Antigravity**.
2. Open [`runner.md`](runner.md) and copy the driving prompt block.
3. Paste the driving prompt into the Antigravity chat.
4. Antigravity will automatically:
   - Check `extracted_triplets/` to see what is already done.
   - Launch waves of up to 25 subagents (10 cases per subagent).
   - Write verified JSON files to `extracted_triplets/<case_id>.json`.
5. When an account reaches its usage limit, switch accounts, open this folder again, and paste the driving prompt. It resumes automatically and never redoes completed cases.

---

## 🔍 Checking Progress

At any time, run:
```bash
python3 validate_triplets.py
```
This displays:
* Total valid cases completed out of 1,797
* Total entities and relationships extracted
* Graph density metrics and top entity types
* Any failed cases requiring re-run
