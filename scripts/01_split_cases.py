"""
01_split_cases.py
─────────────────
Splits cases_full.jsonl into 6 account partitions,
then chunks each partition into groups of 10.

Usage:
    python3 01_split_cases.py \
        --input  /path/to/cases_full.jsonl \
        --output /path/to/output_dir \
        --accounts 6 \
        --chunk-size 10

Output structure:
    output_dir/
      account_00/
        chunk_000.json   (10 cases)
        chunk_001.json   (10 cases)
        ...
        chunk_041.json   (7 cases — last chunk may be smaller)
      account_01/
        ...
      ...
      account_05/
        ...
      manifest.json      (summary of all partitions)
"""

import json
import os
import argparse
import math


def load_jsonl(path):
    cases = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def split_into_accounts(cases, n_accounts):
    """Divide cases as evenly as possible across n_accounts."""
    total = len(cases)
    base = total // n_accounts
    remainder = total % n_accounts  # first `remainder` accounts get +1 case

    partitions = []
    start = 0
    for i in range(n_accounts):
        size = base + (1 if i < remainder else 0)
        partitions.append(cases[start: start + size])
        start += size
    return partitions


def chunk_list(lst, chunk_size):
    """Yield successive chunk_size chunks from lst."""
    for i in range(0, len(lst), chunk_size):
        yield lst[i: i + chunk_size]


def main():
    parser = argparse.ArgumentParser(description="Split cases_full.jsonl for multi-account evaluation")
    parser.add_argument("--input",      required=True,  help="Path to cases_full.jsonl")
    parser.add_argument("--output",     required=True,  help="Output directory")
    parser.add_argument("--accounts",   type=int, default=6,  help="Number of accounts (default: 6)")
    parser.add_argument("--chunk-size", type=int, default=10, help="Cases per chunk (default: 10)")
    args = parser.parse_args()

    print(f"Loading cases from: {args.input}")
    cases = load_jsonl(args.input)
    print(f"Total cases loaded: {len(cases)}")

    os.makedirs(args.output, exist_ok=True)

    partitions = split_into_accounts(cases, args.accounts)
    manifest = {"total_cases": len(cases), "accounts": []}

    for acc_idx, partition in enumerate(partitions):
        acc_dir = os.path.join(args.output, f"account_{acc_idx:02d}")
        os.makedirs(acc_dir, exist_ok=True)

        chunks = list(chunk_list(partition, args.chunk_size))
        acc_info = {
            "account": acc_idx,
            "account_dir": acc_dir,
            "total_cases": len(partition),
            "total_chunks": len(chunks),
            "chunks": []
        }

        for chunk_idx, chunk in enumerate(chunks):
            chunk_path = os.path.join(acc_dir, f"chunk_{chunk_idx:03d}.json")
            with open(chunk_path, "w", encoding="utf-8") as f:
                json.dump(chunk, f, indent=2, ensure_ascii=False)

            acc_info["chunks"].append({
                "chunk_idx": chunk_idx,
                "path": chunk_path,
                "n_cases": len(chunk),
                "case_ids": [c.get("case_id", f"case_{i}") for i, c in enumerate(chunk)]
            })

        manifest["accounts"].append(acc_info)
        print(f"Account {acc_idx:02d}: {len(partition)} cases → {len(chunks)} chunks in {acc_dir}")

    manifest_path = os.path.join(args.output, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done. Manifest written to: {manifest_path}")
    print(f"\nSummary:")
    for acc in manifest["accounts"]:
        print(f"  Account {acc['account']:02d}: {acc['total_cases']} cases, {acc['total_chunks']} chunks")


if __name__ == "__main__":
    main()
