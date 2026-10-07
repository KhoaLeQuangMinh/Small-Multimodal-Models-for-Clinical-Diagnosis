"""
02_evaluate_account.py
──────────────────────
Per-account evaluation runner. Run one instance of this script
per Gemini account. Each instance processes its own partition
using 3 concurrent subagents at a time with a 45-second cooldown.

Usage (run separately in each account's Antigravity session):
    python3 02_evaluate_account.py \
        --account 0 \
        --chunks-dir /path/to/output_dir/account_00 \
        --results-dir /path/to/results/account_00 \
        --rubric    /path/to/TASK.md \
        --concurrency 3 \
        --cooldown 45

This script is meant to be called from within an Antigravity
agent session (or adapted as an agent prompt). It tracks which
chunks are done, skips completed ones on restart, and writes
one result JSON per chunk.

Each result file: results_chunk_NNN.json
  [
    {
      "case_id": "...",
      "is_target_case": true/false,
      "assertions": "term1: status; term2: status",
      "note": "..."
    },
    ...
  ]
"""

import json
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─── Rubric (condensed for prompt injection) ─────────────────────────────────
RUBRIC = """
RUBRIC — Assertion statuses for each matched TERM for THIS patient:
  present      - active diagnosis for this patient in this episode
  absent       - explicitly ruled out, excluded, or reported negative
  historical   - a prior or resolved episode
  differential - considered or suspected, not confirmed
  other_person - refers to a relative, contact, donor, or another patient

is_target_case = TRUE only if BOTH:
  1. at least one TERM is "present", AND
  2. that disease is the patient's actual diagnosis/active comorbidity —
     NOT an incidental mention, negative workup, risk factor, or background prose.

is_target_case = FALSE when every term is absent/historical/differential/other_person,
OR when the real diagnosis is something else and the term only appeared in a
negative workup, risk factor, test panel, or background prose.

Output format — JSON array:
[
  {
    "case_id": "...",
    "is_target_case": true or false,
    "assertions": "term1: status; term2: status",
    "note": "concise clinical rationale (1-2 sentences)"
  }
]
Assertions must be sorted alphabetically by term name.
"""


def load_chunk(chunk_path):
    with open(chunk_path, encoding="utf-8") as f:
        return json.load(f)


def result_path_for(chunk_path, results_dir):
    chunk_name = os.path.basename(chunk_path).replace(".json", "")
    return os.path.join(results_dir, f"results_{chunk_name}.json")


def is_done(chunk_path, results_dir):
    rp = result_path_for(chunk_path, results_dir)
    if not os.path.exists(rp):
        return False
    try:
        with open(rp) as f:
            data = json.load(f)
        return isinstance(data, list) and len(data) > 0
    except Exception:
        return False


def evaluate_chunk_prompt(chunk_path, rubric):
    """
    Returns the text prompt to feed to a subagent for evaluating one chunk.
    In actual Antigravity use, this is sent as the subagent's initial prompt.
    """
    cases = load_chunk(chunk_path)
    case_texts = []
    for c in cases:
        case_texts.append(
            f"CASE ID: {c['case_id']}\n"
            f"TERMS: {json.dumps(c.get('matched_terms', []))}\n"
            f"ARTICLE TITLE: {c.get('article_title', '')}\n"
            f"FULL CASE TEXT:\n{c.get('full_case_text', c.get('text_sent_to_model', ''))}\n"
        )
    cases_block = "\n\n---\n\n".join(case_texts)
    return (
        f"{rubric}\n\n"
        f"Evaluate the following {len(cases)} cases carefully. "
        f"Read every word of each case text before deciding.\n\n"
        f"{cases_block}\n\n"
        f"Return ONLY the JSON array with {len(cases)} objects, one per case, in order."
    )


def save_result(result_data, chunk_path, results_dir):
    rp = result_path_for(chunk_path, results_dir)
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    return rp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account",     type=int, required=True)
    parser.add_argument("--chunks-dir",  required=True)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--rubric",      default=None, help="Path to TASK.md (optional)")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--cooldown",    type=float, default=45.0)
    args = parser.parse_args()

    os.makedirs(args.results_dir, exist_ok=True)

    # Gather all chunk files in order
    chunk_files = sorted([
        os.path.join(args.chunks_dir, f)
        for f in os.listdir(args.chunks_dir)
        if f.endswith(".json") and f.startswith("chunk_")
    ])

    pending = [c for c in chunk_files if not is_done(c, args.results_dir)]
    done_count = len(chunk_files) - len(pending)

    print(f"\nAccount {args.account:02d}")
    print(f"  Total chunks : {len(chunk_files)}")
    print(f"  Already done : {done_count}")
    print(f"  Remaining    : {len(pending)}")
    print(f"  Concurrency  : {args.concurrency}")
    print(f"  Cooldown     : {args.cooldown}s\n")

    # Process in batches of `concurrency`
    batch_num = 0
    for batch_start in range(0, len(pending), args.concurrency):
        batch = pending[batch_start: batch_start + args.concurrency]
        batch_num += 1
        print(f"  Batch {batch_num}: processing {len(batch)} chunks...")

        # --- In real Antigravity usage, spawn subagents here ---
        # The prompt for each chunk is generated by evaluate_chunk_prompt().
        # Each subagent returns a JSON array which you parse and save.
        # Below is a placeholder showing the structure:

        for chunk_path in batch:
            prompt = evaluate_chunk_prompt(chunk_path, RUBRIC)
            chunk_name = os.path.basename(chunk_path)
            print(f"    → Prompt ready for {chunk_name} ({len(prompt)} chars)")
            # In practice: spawn subagent with this prompt, collect response,
            # parse JSON, call save_result(parsed_json, chunk_path, args.results_dir)

        # Cooldown between batches (skip after last batch)
        if batch_start + args.concurrency < len(pending):
            print(f"  Cooling down for {args.cooldown}s...")
            time.sleep(args.cooldown)

    print(f"\n✅ Account {args.account:02d} evaluation loop complete.")
    print(f"   Results in: {args.results_dir}")


if __name__ == "__main__":
    main()
