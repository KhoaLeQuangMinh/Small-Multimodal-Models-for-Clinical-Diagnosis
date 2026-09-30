# 🚀 Guide: How to Run Knowledge Graph Extraction in Antigravity

This guide provides step-by-step instructions for running the distributed extraction of all 1,797 clinical case reports using **Google Antigravity subagents**.

---

## 📌 Important: Which Folder to Open in Antigravity

> [!IMPORTANT]
> **You MUST open `kg_extraction/` as your workspace root in Antigravity.**
>
> In the Antigravity IDE:
> Click **File** $\rightarrow$ **Open Folder...** (or `Cmd+O` on Mac) and select:
> ```text
> .../Datasets/Custom_Tropical_Project/3_LightRAG_Knowledge_Graph/kg_extraction
> ```
> 
> *Why this is critical:* The driving prompt in `runner.md` uses relative paths (`case_prompts/` and `extracted_triplets/`). Opening this specific directory ensures subagents find the input prompts and save output JSON files without path errors.

---

## 📋 Complete Step-by-Step Workflow

### Step 1: Open the `kg_extraction/` Workspace
1. Launch Antigravity.
2. Open the folder:
   `Custom_Tropical_Project/3_LightRAG_Knowledge_Graph/kg_extraction/`
3. Verify in the file explorer sidebar that you see:
   - `case_prompts/` (containing 1,797 `.txt` prompt files)
   - `extracted_triplets/` (destination folder)
   - `runner.md` (driving prompt)
   - `subagent_prompt.md` (subagent worker prompt template)
   - `validate_triplets.py` (verification script)


---

### Step 2: Launch the Subagent Waves
1. Open [`runner.md`](runner.md) in your editor.
2. Copy the text block inside the triple backticks under the divider line.
3. In Antigravity, open a **New Chat**.
4. Paste the prompt and press **Enter**.

---

### Step 3: What Happens During the Run
* Antigravity will check `extracted_triplets/` to see what is already done.
* It will launch **waves of up to 25 subagents** in parallel.
* Each subagent is assigned a chunk of **10 cases**.
* Between waves, there is a deliberate **45-second pause** to prevent hitting rate limits (`429 RESOURCE_EXHAUSTED`).
* After each wave, Antigravity prints a progress report:
  ```text
  Cases done: 250 / 1797 (Failures: 0)
  ```

---

### Step 4: Switching Accounts When Quota is Exhausted
A single Antigravity account typically processes **~400 to 500 cases** before hitting hourly/daily usage limits. When this happens:

1. **Do not worry:** Every finished case is already permanently saved in `extracted_triplets/<case_id>.json`.
2. Log out or switch to your **next Antigravity account** (Account 2, 3, or 4).
3. In Antigravity, open the **exact same `kg_extraction/` folder**.
4. Open a fresh chat and paste the driving prompt from `runner.md` again.
5. The agent will inspect `extracted_triplets/`, detect that cases 1–450 are already finished, and immediately start working on case 451. **It will never repeat already completed cases.**

---

### Step 5: Checking Progress and Health
At any time, open a terminal inside this folder and run:

```bash
python3 validate_triplets.py
```

This will print a real-time status report:
```text
============================================================
Knowledge Graph Triplet Extraction Verification Report
============================================================
Valid completed cases:    450 / 1797 (25.0%)
Remaining cases to run:   1347

--- Graph Density Metrics ---
Total entities extracted:      5,820 (avg 12.9 per case)
Total relationships extracted: 3,940 (avg 8.8 per case)

Top Entity Types:
  - Event          : 1,820
  - Creature       : 1,140
  - Method         : 980
  - Person         : 450
============================================================
```

---

### Step 6: After All 1,797 Cases Are Extracted
Once `validate_triplets.py` reports `Valid completed cases: 1797 / 1797`:

1. Open [`tropical_lightrag_mock_llm.ipynb`](../tropical_lightrag_mock_llm.ipynb) in Google Colab (with T4 GPU) or Jupyter on your Mac.
2. Run Steps 1 through 6.
3. The notebook will load all 1,797 pre-extracted JSON files from `extracted_triplets/` into memory and run only the fast **`bge-m3` embedding model**.
4. The entire 1,797-case Knowledge Graph will be built and ready for hybrid diagnostic queries in **~8 to 12 minutes**!
