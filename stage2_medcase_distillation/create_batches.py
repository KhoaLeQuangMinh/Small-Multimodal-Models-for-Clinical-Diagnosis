"""
Batch Partitioning Script for Stage 2 Distillation (Folder Architecture)

Partitions all 1,427 cases from train_kg_cases.jsonl into 143 batch directories.
Each batch directory contains:
  - batch_meta.json: tracks the 10 cases, their diseases, and completion status.
  - case_XX_<case_id>.json: isolated file for each case with metadata, raw text,
    and the pre-formatted Stanford MedCaseReasoning distillation prompt.
"""

import os
import sys
import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from stage2_medcase_distillation.distillation_prompt import (
    DISTILLATION_SYSTEM_PROMPT,
    DISTILLATION_USER_PROMPT_TEMPLATE,
)

SOURCE_FILE = ROOT_DIR / "train_kg_cases.jsonl"
BATCH_DIR = BASE_DIR / "batches"

def resolve_target_disease(case_dict):
    present = case_dict.get("present", [])
    if present:
        return ", ".join(present)
    candidates = list(case_dict.get("candidates", {}).keys())
    if candidates:
        return candidates[0]
    return "Unknown"

def main():
    # Clean previous flat batch files if any exist
    if BATCH_DIR.exists():
        for old_file in BATCH_DIR.glob("batch_*.json"):
            old_file.unlink()
    else:
        BATCH_DIR.mkdir(parents=True, exist_ok=True)
    
    cases = []
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            case_raw = json.loads(line)
            
            case_id = case_raw.get("case_id", f"case_{idx:04d}")
            article_id = case_raw.get("article_id", "")
            title = case_raw.get("title", "")
            main_problem = case_raw.get("main_problem", "")
            case_text = case_raw.get("case_text", "")
            
            target_disease = resolve_target_disease(case_raw)
            subtype_info = main_problem if main_problem else title
            
            # Format prompts using standardized templates
            system_prompt = DISTILLATION_SYSTEM_PROMPT.format(
                target_canonical_disease=target_disease,
                subtype_info=subtype_info,
            )
            user_prompt = DISTILLATION_USER_PROMPT_TEMPLATE.format(
                target_canonical_disease=target_disease,
                title=title,
                case_text=case_text,
            )
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            cases.append({
                "case_index": idx,
                "case_id": case_id,
                "article_id": article_id,
                "target_disease": target_disease,
                "subtype_info": subtype_info,
                "title": title,
                "case_text": case_text,
                "distillation_prompt": {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "full_prompt": full_prompt,
                }
            })

    total_cases = len(cases)
    batch_size = 10
    total_batches = (total_cases + batch_size - 1) // batch_size
    
    print(f"Total cases read: {total_cases}")
    print(f"Creating {total_batches} batch folders in {BATCH_DIR}...")

    master_summary = []

    for b_idx in range(total_batches):
        batch_folder_name = f"batch_{b_idx:03d}"
        batch_folder_path = BATCH_DIR / batch_folder_name
        batch_folder_path.mkdir(parents=True, exist_ok=True)
        
        start = b_idx * batch_size
        end = min(start + batch_size, total_cases)
        batch_slice = cases[start:end]
        
        batch_case_entries = []

        for local_idx, c in enumerate(batch_slice):
            case_filename = f"case_{local_idx:02d}_{c['case_id']}.json"
            case_file_path = batch_folder_path / case_filename
            
            with open(case_file_path, "w", encoding="utf-8") as out:
                json.dump(c, out, indent=2)
                
            batch_case_entries.append({
                "local_index": local_idx,
                "global_index": c["case_index"],
                "case_id": c["case_id"],
                "target_disease": c["target_disease"],
                "case_file": case_filename,
                "distilled_output_file": f"distilled_{c['case_id']}.json",
            })

        # Write batch_meta.json inside the folder
        batch_meta_path = batch_folder_path / "batch_meta.json"
        batch_meta = {
            "batch_id": b_idx,
            "batch_folder": batch_folder_name,
            "num_cases": len(batch_slice),
            "cases": batch_case_entries,
        }
        with open(batch_meta_path, "w", encoding="utf-8") as out:
            json.dump(batch_meta, out, indent=2)
            
        master_summary.append({
            "batch_id": b_idx,
            "batch_folder": batch_folder_name,
            "num_cases": len(batch_slice),
            "case_ids": [c["case_id"] for c in batch_slice],
            "target_diseases": [c["target_disease"] for c in batch_slice],
        })

    # Save master index
    index_path = BATCH_DIR / "batches_index.json"
    with open(index_path, "w", encoding="utf-8") as out:
        json.dump({
            "total_cases": total_cases,
            "batch_size": batch_size,
            "total_batches": total_batches,
            "batches": master_summary,
        }, out, indent=2)

    print(f"Successfully generated {total_batches} batch directories with {total_cases} isolated case files.")
    print(f"Master index saved to {index_path}")

if __name__ == "__main__":
    main()
