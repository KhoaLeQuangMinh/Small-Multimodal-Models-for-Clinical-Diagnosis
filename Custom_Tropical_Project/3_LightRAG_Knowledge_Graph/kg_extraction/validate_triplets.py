#!/usr/bin/env python3
"""
validate_triplets.py

Verifies the integrity, completeness, and statistics of all JSON files
in kg_extraction/extracted_triplets/.
"""

import os
import glob
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CASE_PROMPTS_DIR = os.path.join(SCRIPT_DIR, "case_prompts")
EXTRACTED_TRIPLETS_DIR = os.path.join(SCRIPT_DIR, "extracted_triplets")

TOTAL_EXPECTED_CASES = 1797

def main():
    if not os.path.exists(EXTRACTED_TRIPLETS_DIR):
        print(f"❌ Directory not found: {EXTRACTED_TRIPLETS_DIR}")
        return

    json_files = sorted(glob.glob(os.path.join(EXTRACTED_TRIPLETS_DIR, "*.json")))
    raw_files = sorted(glob.glob(os.path.join(EXTRACTED_TRIPLETS_DIR, "*.raw.txt")))

    valid_count = 0
    invalid_files = []
    total_entities = 0
    total_relations = 0
    entity_types_count = {}

    for path in json_files:
        fname = os.path.basename(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                invalid_files.append((fname, "Root element is not a JSON object"))
                continue
            
            entities = data.get("entities")
            relationships = data.get("relationships")

            if not isinstance(entities, list) or not isinstance(relationships, list):
                invalid_files.append((fname, "Missing 'entities' or 'relationships' array"))
                continue

            valid_count += 1
            total_entities += len(entities)
            total_relations += len(relationships)

            for ent in entities:
                etype = ent.get("type", "UNKNOWN")
                entity_types_count[etype] = entity_types_count.get(etype, 0) + 1

        except Exception as e:
            invalid_files.append((fname, f"JSON parse error: {str(e)}"))

    print("=" * 60)
    print("Knowledge Graph Triplet Extraction Verification Report")
    print("=" * 60)
    print(f"Valid completed cases:    {valid_count} / {TOTAL_EXPECTED_CASES} ({valid_count/TOTAL_EXPECTED_CASES*100:.1f}%)")
    print(f"Remaining cases to run:   {TOTAL_EXPECTED_CASES - valid_count}")
    
    if raw_files:
        print(f"\n⚠️  Raw failure files (.raw.txt): {len(raw_files)}")
        for r in raw_files[:5]:
            print(f"   - {os.path.basename(r)}")
        if len(raw_files) > 5:
            print(f"   ... and {len(raw_files) - 5} more")

    if invalid_files:
        print(f"\n❌ Invalid JSON files: {len(invalid_files)}")
        for fname, err in invalid_files[:5]:
            print(f"   - {fname}: {err}")
        if len(invalid_files) > 5:
            print(f"   ... and {len(invalid_files) - 5} more")

    if valid_count > 0:
        avg_ent = total_entities / valid_count
        avg_rel = total_relations / valid_count
        print(f"\n--- Graph Density Metrics ---")
        print(f"Total entities extracted:      {total_entities:,} (avg {avg_ent:.1f} per case)")
        print(f"Total relationships extracted: {total_relations:,} (avg {avg_rel:.1f} per case)")
        print("\nTop Entity Types:")
        for etype, count in sorted(entity_types_count.items(), key=lambda x: x[1], reverse=True)[:8]:
            print(f"  - {etype:<15}: {count:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
