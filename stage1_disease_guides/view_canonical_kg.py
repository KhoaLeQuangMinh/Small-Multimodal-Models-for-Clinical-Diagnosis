#!/usr/bin/env python3
"""
view_canonical_kg.py
CLI Inspector for the Stage 1 Canonical Knowledge Graph across 22 Diseases.
==========================================================================
Usage:
  # 1. Show overall summary across all 22 diseases:
  python stage1_disease_guides/view_canonical_kg.py

  # 2. Inspect a specific disease illness script (e.g., Dengue, Malaria, Scrub Typhus):
  python stage1_disease_guides/view_canonical_kg.py --disease "Scrub Typhus"

  # 3. Search for a specific symptom, finding, or hallmark across all diseases:
  python stage1_disease_guides/view_canonical_kg.py --search "eschar"

  # 4. Verify the compiled GraphML file directly:
  python stage1_disease_guides/view_canonical_kg.py --graphml
"""

import os
import sys
import json
import argparse
from collections import Counter, defaultdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STAGE1_DIR = os.path.join(PROJECT_ROOT, "stage1_disease_guides")
TRIPLES_FILE = os.path.join(STAGE1_DIR, "canonical_triples.jsonl")
GRAPHML_FILE = os.path.join(STAGE1_DIR, "canonical_kg", "graph_chunk_entity_relation.graphml")

def load_canonical_data():
    if not os.path.exists(TRIPLES_FILE):
        print(f"Error: Triples file not found at {TRIPLES_FILE}")
        sys.exit(1)
    diseases_data = []
    with open(TRIPLES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                diseases_data.append(json.loads(line))
    return diseases_data

def print_summary(diseases_data):
    print("=" * 95)
    print("       STAGE 1 CANONICAL KNOWLEDGE GRAPH — 22 TROPICAL DISEASES OVERVIEW")
    print("=" * 95)
    print(f"{'#':<3} {'Disease Name':<28} {'Entities':<10} {'Triples':<10} {'Manifest':<9} {'Hallmarks':<10} {'RuleOuts':<9} {'Diffs':<6}")
    print("-" * 95)

    tot_ent = 0
    tot_rel = 0
    tot_pred = Counter()

    for idx, d in enumerate(sorted(diseases_data, key=lambda x: x["disease"]), 1):
        dname = d["disease"]
        extraction = d.get("extraction", {})
        ents = extraction.get("entities", [])
        rels = extraction.get("relationships", [])
        tot_ent += len(ents)
        tot_rel += len(rels)

        pred_counts = Counter(r.get("predicate", "OTHER") for r in rels)
        for k, v in pred_counts.items():
            tot_pred[k] += v

        manifest = pred_counts.get("MANIFESTS_AS", 0)
        hallmarks = pred_counts.get("HAS_PATHOGNOMONIC_HALLMARK", 0) + pred_counts.get("PHYSICAL_EXAM_SIGN", 0)
        ruleouts = pred_counts.get("RULED_OUT_BY", 0)
        diffs = pred_counts.get("DIFFERENTIATED_FROM", 0)

        print(f"{idx:>2}. {dname:<28} {len(ents):>8} {len(rels):>10} {manifest:>9} {hallmarks:>10} {ruleouts:>9} {diffs:>6}")

    print("=" * 95)
    print(f"TOTAL: 22 Tropical Diseases | Entities: {tot_ent:,} | Relationships: {tot_rel:,}")
    if os.path.exists(GRAPHML_FILE):
        size_mb = os.path.getsize(GRAPHML_FILE) / (1024 * 1024)
        print(f"Compiled GraphML Storage : {GRAPHML_FILE} ({size_mb:.2f} MB)")
    print("=" * 95)

def print_disease(diseases_data, query_disease):
    query_lower = query_disease.strip().lower()
    matched = None
    for d in diseases_data:
        if query_lower in d["disease"].lower():
            matched = d
            break

    if not matched:
        print(f"Error: Disease matching '{query_disease}' not found.")
        print("Available diseases:")
        for d in sorted(diseases_data, key=lambda x: x["disease"]):
            print(f"  - {d['disease']}")
        return

    dname = matched["disease"]
    extraction = matched.get("extraction", {})
    ents = extraction.get("entities", [])
    rels = extraction.get("relationships", [])

    print("=" * 90)
    print(f"  CANONICAL ILLNESS SCRIPT: {dname.upper()}")
    print(f"  Total Entities: {len(ents)} | Total Relationships: {len(rels)}")
    print("=" * 90)

    # Group by predicate category
    categories = {
        "1. PATHOGNOMONIC HALLMARKS & PHYSICAL SIGNS": ["HAS_PATHOGNOMONIC_HALLMARK", "PHYSICAL_EXAM_SIGN"],
        "2. ADMISSION TRIAGE LABS & IMAGING FINDINGS": ["EXHIBITS_LAB_PATTERN", "IMAGING_FINDING"],
        "3. ORGAN MANIFESTATIONS & CLINICAL PRESENTATIONS": ["MANIFESTS_AS"],
        "4. EXPOSURE, VECTOR & INCUBATION PERIOD": ["EXPOSURE_TO", "HIGH_RISK_HOST", "INCUBATION_PERIOD"],
        "5. PERTINENT NEGATIVES & EXCLUSION BOUNDARIES": ["RULED_OUT_BY"],
        "6. PAIRWISE DIFFERENTIAL CONTRASTS": ["DIFFERENTIATED_FROM"]
    }

    by_pred = defaultdict(list)
    for r in rels:
        by_pred[r.get("predicate", "OTHER")].append(r)

    for cat_title, preds in categories.items():
        cat_rels = []
        for p in preds:
            cat_rels.extend(by_pred[p])
        print(f"\n{cat_title} ({len(cat_rels)} triples):")
        print("-" * 90)
        for r in cat_rels[:12]:
            desc = r.get("description", "").strip()
            print(f"  • {r.get('source')} --[{r.get('predicate')}]--> {r.get('target')}")
            if desc:
                print(f"    Rationale: {desc[:100]}...")
        if len(cat_rels) > 12:
            print(f"    ... and {len(cat_rels) - 12} more triples.")

def search_term(diseases_data, query):
    q = query.strip().lower()
    print("=" * 90)
    print(f"  SEARCHING CANONICAL GRAPH FOR: '{query}'")
    print("=" * 90)
    hits = []
    for d in diseases_data:
        dname = d["disease"]
        for r in d.get("extraction", {}).get("relationships", []):
            src = str(r.get("source", ""))
            tgt = str(r.get("target", ""))
            desc = str(r.get("description", ""))
            if q in src.lower() or q in tgt.lower() or q in desc.lower():
                hits.append((dname, r))

    if not hits:
        print(f"No triples found containing '{query}'.")
        return

    print(f"Found {len(hits)} matching relationship(s) across {len(set(h[0] for h in hits))} disease(s):\n")
    for dname, r in hits[:25]:
        pred = r.get("predicate", "")
        tgt = r.get("target", "")
        desc = r.get("description", "")
        print(f"  [{dname:<18}] --[{pred}]--> {tgt}")
        print(f"    {desc}\n")
    if len(hits) > 25:
        print(f"  ... and {len(hits) - 25} more matches.")

def inspect_graphml():
    if not os.path.exists(GRAPHML_FILE):
        print(f"Error: GraphML file not found at {GRAPHML_FILE}")
        return
    try:
        import networkx as nx
        print("Reading LightRAG GraphML file (this takes ~1-2 seconds)...")
        G = nx.read_graphml(GRAPHML_FILE)
        print("=" * 75)
        print("               LIGHTRAG GRAPHML STORAGE VERIFICATION")
        print("=" * 75)
        print(f"  GraphML File  : {GRAPHML_FILE}")
        print(f"  Total Nodes   : {G.number_of_nodes():,}")
        print(f"  Total Edges   : {G.number_of_edges():,}")
        print(f"  File Size     : {os.path.getsize(GRAPHML_FILE) / (1024*1024):.2f} MB")
        
        # Hub node connectivity check
        print("\n  Top 10 Most Connected Hub Nodes:")
        degrees = sorted(G.degree, key=lambda x: x[1], reverse=True)[:10]
        for node, deg in degrees:
            print(f"    - {node:<30}: {deg} connections")
        print("=" * 75)
    except ImportError:
        print("NetworkX is required to inspect GraphML: install via pip install networkx")

def main():
    parser = argparse.ArgumentParser(description="Inspect Stage 1 Canonical Knowledge Graph")
    parser.add_argument("--disease", type=str, help="Show full illness script for a specific disease")
    parser.add_argument("--search", type=str, help="Search for a symptom, hallmark, or finding across all diseases")
    parser.add_argument("--graphml", action="store_true", help="Verify the compiled GraphML file directly")
    args = parser.parse_args()

    if args.graphml:
        inspect_graphml()
        return

    diseases_data = load_canonical_data()

    if args.disease:
        print_disease(diseases_data, args.disease)
    elif args.search:
        search_term(diseases_data, args.search)
    else:
        print_summary(diseases_data)

if __name__ == "__main__":
    main()
