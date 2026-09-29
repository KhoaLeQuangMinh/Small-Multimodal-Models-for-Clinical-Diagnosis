# Decoupled Knowledge Graph Triplet Extraction

This directory contains the pipeline to extract high-quality clinical entities and relationship triplets from all 1,797 verified tropical disease cases using Antigravity subagents.

---

## 📖 Quick Links & Documentation

* **👉 [HOW_TO_RUN_IN_ANTIGRAVITY.md](HOW_TO_RUN_IN_ANTIGRAVITY.md)** — **Start here!** Full step-by-step guide on which folder to open, how to paste the runner prompt, and how to switch accounts when quota is exhausted.
* **[runner.md](runner.md)** — The driving prompt block to copy and paste into Antigravity chat.
* **[prompt.md](prompt.md)** — Reference copy of LightRAG's entity and relationship extraction prompt.

---

## 📁 Directory Structure

```text
kg_extraction/
├── HOW_TO_RUN_IN_ANTIGRAVITY.md # Step-by-step instructions for running in Antigravity
├── README.md                    # Overview of the extraction pipeline
├── runner.md                    # Antigravity driving prompt (paste into chat)
├── prompt.md                    # Reference copy of the extraction prompt
├── prepare_case_prompts.py      # Generates 1,797 prompt files from partA_final.jsonl
├── validate_triplets.py         # Progress & graph density verification script
├── case_prompts/                # [Git-ignored] 1,797 self-contained prompt files (.txt)
└── extracted_triplets/          # [Git-ignored] Output directory for extracted triplets (.json)
```

---

## ⚡ Quick Summary of the Workflow

1. Open this `kg_extraction/` folder in **Google Antigravity**.
2. Copy the prompt block from [`runner.md`](runner.md) and paste it into a new chat.
3. Subagents will extract triplets in waves of up to 25 workers.
4. Check progress anytime:
   ```bash
   python3 validate_triplets.py
   ```
5. When quota runs out, switch accounts, reopen this folder, and paste the prompt again. It automatically resumes without redoing finished work.
6. Once all 1,797 cases are completed, open [`../tropical_lightrag_mock_llm.ipynb`](../tropical_lightrag_mock_llm.ipynb) to embed the final Knowledge Graph in ~10 minutes.
