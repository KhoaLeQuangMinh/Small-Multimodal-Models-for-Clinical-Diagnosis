"""
test_triple_ranker.py
Unit test for Stage 3 ClinicalTripleRanker.
Demonstrates the before-and-after ranking of candidate triples
for an acute febrile clinical scenario with pathognomonic clues.
"""

from triple_ranker import ClinicalTripleRanker

def run_unit_test():
    ranker = ClinicalTripleRanker()

    patient_presentation = (
        "A 34-year-old agricultural laborer presents with acute onset of high fever, "
        "excruciating myalgias, conjunctival suffusion, and dark urine after wading through "
        "monsoon floodwaters. Initial triage laboratory tests show elevated serum bilirubin (8.5 mg/dL), "
        "profound acute kidney injury with creatinine 4.1 mg/dL, and marked neutrophilic leukocytosis. "
        "Platelet count is 145,000/uL. Empiric therapy was initiated."
    )

    # Simulated candidate triples retrieved from LightRAG
    candidate_pool = [
        {"source": "Malaria", "relation": "causes", "target": "Fever", "description": "High fever with chills"},
        {"source": "Dengue", "relation": "manifests_as", "target": "Headache and Body Aches", "description": "Retro-orbital pain and fever"},
        {"source": "Melioidosis", "relation": "presents_with", "target": "Fever and Malaise", "description": "Septic illness in diabetics"},
        {"source": "Tuberculosis", "relation": "causes", "target": "Night Sweats and Weight Loss", "description": "Constitutional B-symptoms"},
        {"source": "Leptospirosis", "relation": "pathognomonic_sign", "target": "Conjunctival Suffusion", "description": "Bilateral conjunctival injection without purulent discharge"},
        {"source": "Leptospirosis", "relation": "cardinal_syndrome", "target": "Weil Syndrome Triad of Jaundice, Renal Failure, and Hemorrhage", "description": "Severe icteric leptospirosis with acute tubular necrosis and liver impairment"},
        {"source": "Leptospirosis", "relation": "exposure_risk", "target": "Wading in Contaminated Floodwater and Rodent Urine", "description": "Direct contact with water containing Leptospira"},
        {"source": "Viral Hemorrhagic Fevers", "relation": "causes", "target": "Fever and Weakness", "description": "Acute febrile onset"},
        {"source": "Amebiasis", "relation": "causes", "target": "Abdominal Pain and Vomiting", "description": "GI symptoms in amoebic dysentery"},
        {"source": "Scrub Typhus", "relation": "pathognomonic_sign", "target": "Eschar", "description": "Necrotic black cigarette-burn ulcer"}
    ]

    print("=== Stage 3: Clinical Triple Ranker Unit Test ===")
    print("\nPatient Clinical Query:")
    print(patient_presentation)

    print("\n--- UNWEIGHTED BASELINE RANKING (Natural candidate order) ---")
    for i, t in enumerate(candidate_pool[:5], 1):
        print(f"  {i}. [{t['source']}] -> [{t['relation']}] -> [{t['target']}]")

    print("\n--- SOFT-WEIGHTED STAGE 3 RANKING (Filtered & Prioritized) ---")
    ranked = ranker.rank_triples(candidate_pool, patient_text=patient_presentation, top_k=5)
    for i, r in enumerate(ranked, 1):
        print(f"  {i}. [{r['source']}] -> [{r['relation']}] -> [{r['target']}] (Score: {r['score']})")

    print("\n--- FORMATTED MARKDOWN PROMPT CONTEXT (Ready for {stage1_graph_context}) ---")
    formatted_context = ranker.format_triples_for_prompt(candidate_pool, patient_text=patient_presentation, top_k=5)
    print(formatted_context)

    # Verification checks
    top_sources = [r["source"] for r in ranked[:3]]
    top_targets = [r["target"] for r in ranked[:3]]

    assert "Leptospirosis" in top_sources, "Leptospirosis must be in top-ranked sources!"
    assert any("Suffusion" in t for t in top_targets), "Conjunctival suffusion must be prioritized in top targets!"
    assert ranked[0]["score"] > ranked[-1]["score"], "Ranking order must be strictly descending!"
    print("\n>>> ALL CLINICAL UNIT TEST ASSERTIONS PASSED! <<<")

if __name__ == "__main__":
    run_unit_test()
