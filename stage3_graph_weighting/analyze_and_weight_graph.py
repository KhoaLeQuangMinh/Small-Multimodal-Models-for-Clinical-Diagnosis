"""
analyze_and_weight_graph.py
Stage 3: Graph Evaluation & Generic Term Weight Discounting.
Analyzes node degree distribution in the Canonical Knowledge Graph
(stage1_disease_guides/canonical_kg/graph_chunk_entity_relation.graphml)
and identifies multi-disease shared symptom hubs vs disease-specific anchors.
"""

import os
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

CANONICAL_DISEASES = [
    "Amebiasis", "Cholera", "Dengue", "Echinococcosis", "Foodborne Trematodes",
    "Leishmaniasis", "Leprosy", "Leptospirosis", "Malaria", "Melioidosis",
    "Mycetoma", "Neurocysticercosis", "Paracoccidioidomycosis", "Scabies",
    "Schistosomiasis", "Scrub Typhus", "Soil-Transmitted Helminths",
    "Talaromycosis", "Trypanosomiasis", "Tuberculosis", "Viral Hemorrhagic Fevers",
    "Zika Virus"
]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, ".."))
    graph_path = os.path.join(project_root, "stage1_disease_guides", "canonical_kg", "graph_chunk_entity_relation.graphml")
    stats_output = os.path.join(base_dir, "graph_statistics.json")

    print(f"=== Stage 3.1: Analyzing Canonical Knowledge Graph ===")
    print(f"Graph Path: {graph_path}")
    assert os.path.exists(graph_path), f"GraphML file not found at: {graph_path}"

    tree = ET.parse(graph_path)
    root = tree.getroot()
    ns = {"g": "http://graphml.graphdrawing.org/xmlns"}

    nodes = root.findall(".//g:node", ns)
    edges = root.findall(".//g:edge", ns)

    print(f"Total Nodes: {len(nodes)}")
    print(f"Total Edges: {len(edges)}")

    # Extract node metadata
    node_data = {}
    for n in nodes:
        nid = n.get("id")
        data_elems = n.findall("g:data", ns)
        attrs = {}
        for d in data_elems:
            attrs[d.get("key")] = d.text or ""
        node_data[nid] = attrs

    # Compute degree
    degree_counter = Counter()
    adj = defaultdict(set)
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        degree_counter[src] += 1
        degree_counter[tgt] += 1
        adj[src].add(tgt)
        adj[tgt].add(src)

    # Classify nodes: Canonical Disease vs Clinical Entities
    disease_degrees = {d: degree_counter[d] for d in CANONICAL_DISEASES if d in degree_counter}
    non_disease_degrees = {k: v for k, v in degree_counter.items() if k not in CANONICAL_DISEASES}

    print("\n--- Canonical Disease Connectivity (Degree) ---")
    for d, deg in sorted(disease_degrees.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {d:30s}: {deg:2d} edges")

    print("\n--- Top 20 Highest-Degree Clinical Finding Entities ---")
    sorted_non_disease = sorted(non_disease_degrees.items(), key=lambda x: x[1], reverse=True)
    for ent, deg in sorted_non_disease[:20]:
        print(f"  - {ent[:65]:65s}: {deg:2d} edges")

    # Save summary stats
    stats = {
        "graph_path": graph_path,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "canonical_disease_count": len(disease_degrees),
        "disease_degrees": disease_degrees,
        "top_non_disease_entities": [{"entity": ent, "degree": deg} for ent, deg in sorted_non_disease[:50]]
    }

    with open(stats_output, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"\nGraph statistics successfully exported to: {stats_output}")

if __name__ == "__main__":
    main()
