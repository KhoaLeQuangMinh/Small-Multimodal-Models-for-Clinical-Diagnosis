"""
03_merge_results.py
───────────────────
Merges results from all 6 accounts into one final answers.csv.
Also validates the output before writing.

Usage:
    python3 03_merge_results.py \
        --results-root /path/to/results \
        --cases        /path/to/cases_full.jsonl \
        --output       /path/to/answers.csv \
        --accounts     6

Expected results-root structure:
    results/
      account_00/
        results_chunk_000.json
        results_chunk_001.json
        ...
      account_01/
        ...
      ...
      account_05/
        ...
"""

import json
import csv
import os
import argparse
import glob


VALID_STATUSES = {"present", "absent", "historical", "differential", "other_person"}


def load_jsonl(path):
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_all_results(results_root, n_accounts):
    all_results = []
    for acc_idx in range(n_accounts):
        acc_dir = os.path.join(results_root, f"account_{acc_idx:02d}")
        if not os.path.isdir(acc_dir):
            print(f"  ⚠️  Missing account dir: {acc_dir}")
            continue

        result_files = sorted(glob.glob(os.path.join(acc_dir, "results_chunk_*.json")))
        acc_count = 0
        for rf in result_files:
            try:
                with open(rf, encoding="utf-8") as f:
                    chunk_results = json.load(f)
                all_results.extend(chunk_results)
                acc_count += len(chunk_results)
            except Exception as e:
                print(f"  ⚠️  Error reading {rf}: {e}")

        print(f"  Account {acc_idx:02d}: loaded {acc_count} cases from {len(result_files)} chunks")

    return all_results


def validate(all_results, expected_case_ids):
    errors = []
    result_ids = [r["case_id"] for r in all_results]

    # Count
    if len(all_results) != len(expected_case_ids):
        errors.append(f"Count mismatch: got {len(all_results)}, expected {len(expected_case_ids)}")

    # Duplicates
    seen = {}
    for cid in result_ids:
        seen[cid] = seen.get(cid, 0) + 1
    dupes = [cid for cid, cnt in seen.items() if cnt > 1]
    if dupes:
        errors.append(f"Duplicate case_ids: {dupes[:10]}")

    # Missing / extra
    result_set = set(result_ids)
    expected_set = set(expected_case_ids)
    missing = expected_set - result_set
    extra = result_set - expected_set
    if missing:
        errors.append(f"Missing case_ids ({len(missing)}): {list(missing)[:10]}")
    if extra:
        errors.append(f"Extra case_ids ({len(extra)}): {list(extra)[:10]}")

    # Field checks
    for r in all_results:
        cid = r.get("case_id", "UNKNOWN")
        for field in ["case_id", "is_target_case", "assertions", "note"]:
            if field not in r or str(r[field]).strip() == "":
                errors.append(f"Empty/missing field '{field}' in {cid}")

        # Assertion format
        assertions = r.get("assertions", "")
        for part in [p.strip() for p in assertions.split(";")]:
            if ":" not in part:
                errors.append(f"Bad assertion format in {cid}: '{part}'")
                continue
            _, status = part.rsplit(":", 1)
            if status.strip() not in VALID_STATUSES:
                errors.append(f"Invalid status '{status.strip()}' in {cid}")

    # Logical consistency: true → must have 'present'
    for r in all_results:
        if str(r.get("is_target_case", "")).lower() == "true":
            if "present" not in r.get("assertions", ""):
                errors.append(f"TRUE case without 'present' assertion: {r['case_id']}")

    return errors


def write_csv(all_results, output_path, expected_order):
    # Sort by original case order
    order_map = {cid: i for i, cid in enumerate(expected_order)}
    all_results.sort(key=lambda r: order_map.get(r["case_id"], 999999))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "is_target_case", "assertions", "note"])
        writer.writeheader()
        for r in all_results:
            writer.writerow({
                "case_id":        r["case_id"],
                "is_target_case": str(r["is_target_case"]).lower(),
                "assertions":     r["assertions"],
                "note":           r["note"],
            })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--cases",        required=True, help="Path to original cases_full.jsonl")
    parser.add_argument("--output",       required=True, help="Output answers.csv path")
    parser.add_argument("--accounts",     type=int, default=6)
    args = parser.parse_args()

    print("Loading original cases to get expected order...")
    original_cases = load_jsonl(args.cases)
    expected_ids = [c["case_id"] for c in original_cases]
    print(f"  Expected: {len(expected_ids)} cases\n")

    print("Loading results from all accounts...")
    all_results = load_all_results(args.results_root, args.accounts)
    print(f"\nTotal results collected: {len(all_results)}\n")

    print("Validating...")
    errors = validate(all_results, expected_ids)
    if errors:
        print(f"❌ {len(errors)} validation error(s):")
        for e in errors:
            print(f"  - {e}")
        print("\nFix errors before writing final CSV.")
        return
    else:
        print("✅ Validation passed — no errors found.\n")

    # Stats
    true_cases  = sum(1 for r in all_results if str(r["is_target_case"]).lower() == "true")
    false_cases = sum(1 for r in all_results if str(r["is_target_case"]).lower() == "false")
    print(f"Statistics:")
    print(f"  is_target_case = true  : {true_cases}")
    print(f"  is_target_case = false : {false_cases}")

    write_csv(all_results, args.output, expected_ids)
    print(f"\n✅ Written {len(all_results)} rows to: {args.output}")


if __name__ == "__main__":
    main()
