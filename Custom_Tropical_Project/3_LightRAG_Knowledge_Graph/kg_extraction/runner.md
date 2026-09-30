# Driving prompt for Knowledge Graph Triplet Extraction

Open this folder (`kg_extraction/`) in Antigravity, then copy and paste the block below into the chat.

`extracted_triplets/` is the progress log: a case is finished when `extracted_triplets/<case_id>.json`
exists and contains valid JSON with `entities` and `relationships` arrays.

When an account hits its token/usage limit, open this same folder with your next account, start a new session,
and paste the block again. It will automatically detect existing files, pick up where the last session stopped,
and never redo finished work.

---

```text
You are running a clinical Knowledge Graph triplet extraction job over the files in this folder.

SCOPE
  `case_prompts/` holds 1,797 .txt files. Each file is a COMPLETE, self-contained
  prompt — extraction instructions plus exactly one clinical case document.

WHAT IS ALREADY DONE
  A case is finished when `extracted_triplets/<case_id>.json` exists and contains
  valid JSON with "entities" and "relationships" arrays. The case_id is the
  part of the filename after the sequence number:
      0001_PMC10018284_01.txt  ->  extracted_triplets/PMC10018284_01.json
  Before you start, list `case_prompts/` and `extracted_triplets/`. If a file in
  `extracted_triplets/` is empty or is not valid JSON, delete it — an earlier session
  was cut off while writing it — and treat that case as not done. Then work
  only on the cases that are not done. Never redo a finished case.

HOW TO RUN IT
  Sort the remaining files by filename and split them into chunks of 10.
  Launch up to 25 subagents at the same time, one chunk each. After each
  wave finishes, wait 45 seconds before launching the next wave. Repeat
  until no chunks remain.

  That pause is deliberate: it keeps this account under its token quota.
  Do not skip it, even if the first waves feel slow.

EACH SUBAGENT
  Invoke each subagent using `invoke_subagent` with:
    - TypeName: "self"
    - Role: "Clinical Triplet Extractor"
    - Model: "inherit"
    - Prompt: Use this EXACT prompt template (replacing {FILE_LIST} with the 10 assigned filenames):
      """
      You are a specialized Clinical Knowledge Graph Extractor worker.
      You are assigned a batch of 10 clinical case prompt files in `case_prompts/`:
      {FILE_LIST}

      For each file:
      1. Read the file using `view_file`: case_prompts/<filename>.txt
      2. Follow the extraction instructions inside the file strictly.
      3. Construct a valid JSON object: {"entities": [...], "relationships": [...]}
      4. Determine case_id by stripping the 4-digit prefix (e.g. 0001_PMC10018284_01.txt -> PMC10018284_01).
      5. Write ONLY the raw JSON string directly to disk using `write_to_file`:
         extracted_triplets/<case_id>.json
         (No markdown ```json fences, no prose before or after).
      6. If invalid or error occurs, save verbatim to:
         extracted_triplets/<case_id>.raw.txt
      7. Treat every case as completely independent.

      When all 10 files are done, reply:
      "Batch complete: X/10 cases successfully written to extracted_triplets/."
      """


IF SOMETHING FAILS
  - Quota / 429 / RESOURCE_EXHAUSTED: stop launching new subagents, wait
    120 seconds, then resume from where you were. Do not drop the case. If
    it still fails after 3 tries, stop and print how many cases are done —
    the run will continue on another account.
  - A model reply that is not valid JSON: save it verbatim as
    `extracted_triplets/<case_id>.raw.txt` and carry on. Do not repair it yourself.
  - A file you cannot read: note it and carry on.

RULES
  - Never modify anything in `case_prompts/`.
  - Write nothing except files in `extracted_triplets/`.
  - Do not answer any case yourself, and do not edit a model's answer.

REPORT
  After every wave print: cases done / 1797, and any failures so far.
  When no cases are left, print a final count and stop.

Start by listing what is already done, then begin.
```

---

## Expected Throughput

* **Total cases:** 1,797 files in `case_prompts/`.
* **Execution:** Chunks of 10 files, running in waves of up to 25 subagents (250 cases per wave), spaced 45 seconds apart.
* **Accounts:** ~4 accounts will complete all 1,797 cases (~450 cases per account quota cycle).
