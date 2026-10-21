#!/usr/bin/env python3
"""
Comprehensive Evaluation Script for Stage 4 Ablation Results.
Computes Top-1 Accuracy, Tolerant Top-3 Coverage, MRR, Melioidosis Attractor Rate,
Weighted/Macro F1 for both Top-1 and Tolerant Differential paradigms.
"""

import os
import csv
import sys
import json
from collections import defaultdict

CANDIDATE_DISEASES = [
    "Amebiasis",
    "Cholera",
    "Dengue",
    "Echinococcosis",
    "Foodborne Trematodes",
    "Leishmaniasis",
    "Leprosy",
    "Leptospirosis",
    "Malaria",
    "Melioidosis",
    "Mycetoma",
    "Neurocysticercosis",
    "Paracoccidioidomycosis",
    "Scabies",
    "Schistosomiasis",
    "Scrub Typhus",
    "Soil-Transmitted Helminths",
    "Talaromycosis",
    "Trypanosomiasis",
    "Tuberculosis",
    "Viral Hemorrhagic Fevers",
    "Zika Virus",
]

def normalize_disease_name(d_str):
    if not d_str:
        return ""
    d_clean = d_str.strip().lower()
    for cand in CANDIDATE_DISEASES:
        if cand.lower() == d_clean:
            return cand
    for cand in CANDIDATE_DISEASES:
        if cand.lower() in d_clean or d_clean in cand.lower():
            return cand
    return d_str.strip()

def evaluate_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return None

    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    total_cases = len(rows)
    if total_cases == 0:
        print(f"Empty CSV: {csv_path}")
        return None

    # Top-1 structures
    top1_correct = 0
    top3_correct = 0
    melio_attractor = 0
    reciprocal_ranks = []

    # Per-class Top-1 counters
    tp1 = defaultdict(int)
    fp1 = defaultdict(int)
    fn1 = defaultdict(int)
    support = defaultdict(int)

    # Tolerant Differential counters
    tp_tol = defaultdict(int)
    haz_fp = defaultdict(int)
    fn_tol = defaultdict(int)

    for r in rows:
        gt = normalize_disease_name(r["ground_truth"])
        pred_top1 = normalize_disease_name(r["predicted_final"])
        
        # Parse differentials
        raw_diffs = r.get("differential_hypotheses", "")
        diff_list = []
        if pred_top1:
            diff_list.append(pred_top1)
        for item in raw_diffs.split("|"):
            norm_item = normalize_disease_name(item)
            if norm_item and norm_item not in diff_list:
                diff_list.append(norm_item)
        top3 = diff_list[:3]

        support[gt] += 1

        # Check Top-1
        is_top1 = (pred_top1 == gt)
        if is_top1:
            top1_correct += 1
            tp1[gt] += 1
        else:
            fn1[gt] += 1
            if pred_top1:
                fp1[pred_top1] += 1

        # Check Melioidosis attractor
        if pred_top1 == "Melioidosis" and gt != "Melioidosis":
            melio_attractor += 1

        # Check Top-3 / MRR
        if gt in top3:
            rank = top3.index(gt) + 1
            rr = 1.0 / rank
            top3_correct += 1
            tp_tol[gt] += 1
        else:
            rr = 0.0
            fn_tol[gt] += 1
            for p in top3:
                haz_fp[p] += 1
        reciprocal_ranks.append(rr)

    # Aggregate Top-1 Metrics
    top1_acc = (top1_correct / total_cases) * 100.0
    top3_cov = (top3_correct / total_cases) * 100.0
    mrr = (sum(reciprocal_ranks) / total_cases) * 100.0
    melio_rate = (melio_attractor / total_cases) * 100.0

    # Class-level Top-1 F1
    prec_top1_list = []
    rec_top1_list = []
    f1_top1_list = []

    # Tolerant Class-level F1
    prec_tol_list = []
    rec_tol_list = []
    f1_tol_list = []

    weighted_f1_tol = 0.0
    weighted_f1_top1 = 0.0

    for d in CANDIDATE_DISEASES:
        s = support[d]
        # Top-1
        p1 = tp1[d] / (tp1[d] + fp1[d]) if (tp1[d] + fp1[d]) > 0 else 0.0
        r1 = tp1[d] / (tp1[d] + fn1[d]) if (tp1[d] + fn1[d]) > 0 else 0.0
        f1_1 = (2 * p1 * r1 / (p1 + r1)) if (p1 + r1) > 0 else 0.0
        prec_top1_list.append(p1)
        rec_top1_list.append(r1)
        f1_top1_list.append(f1_1)
        weighted_f1_top1 += f1_1 * s

        # Tolerant
        p_t = tp_tol[d] / (tp_tol[d] + haz_fp[d]) if (tp_tol[d] + haz_fp[d]) > 0 else 0.0
        r_t = tp_tol[d] / (tp_tol[d] + fn_tol[d]) if (tp_tol[d] + fn_tol[d]) > 0 else 0.0
        f1_t = (2 * p_t * r_t / (p_t + r_t)) if (p_t + r_t) > 0 else 0.0
        prec_tol_list.append(p_t)
        rec_tol_list.append(r_t)
        f1_tol_list.append(f1_t)
        weighted_f1_tol += f1_t * s

    macro_f1_top1 = (sum(f1_top1_list) / len(CANDIDATE_DISEASES)) * 100.0
    weighted_f1_top1 = (weighted_f1_top1 / total_cases) * 100.0

    macro_f1_tol = (sum(f1_tol_list) / len(CANDIDATE_DISEASES)) * 100.0
    weighted_f1_tol = (weighted_f1_tol / total_cases) * 100.0

    summary = {
        "csv_path": csv_path,
        "total_cases": total_cases,
        "top1_acc": top1_acc,
        "top3_cov": top3_cov,
        "mrr": mrr,
        "melioidosis_attractor_rate": melio_rate,
        "macro_f1_top1": macro_f1_top1,
        "weighted_f1_top1": weighted_f1_top1,
        "macro_f1_tolerant": macro_f1_tol,
        "weighted_f1_tolerant": weighted_f1_tol,
    }

    print("\n" + "=" * 75)
    print(f"BENCHMARK EVALUATION: {os.path.basename(csv_path)}")
    print("=" * 75)
    print(f"Total Cases Evaluated       : {total_cases}")
    print(f"Top-1 Diagnostic Accuracy   : {top1_acc:.2f}%")
    print(f"Top-3 Tolerant Coverage     : {top3_cov:.2f}%")
    print(f"Mean Reciprocal Rank (MRR)  : {mrr:.2f}%")
    print(f"Melioidosis Attractor Rate  : {melio_rate:.2f}%")
    print(f"Top-1 Macro F1              : {macro_f1_top1:.2f}%")
    print(f"Top-1 Weighted F1           : {weighted_f1_top1:.2f}%")
    print(f"Tolerant Macro F1           : {macro_f1_tol:.2f}%")
    print(f"Tolerant Weighted F1        : {weighted_f1_tol:.2f}%")
    print("=" * 75 + "\n")

    return summary

if __name__ == "__main__":
    if len(sys.argv) > 1:
        for p in sys.argv[1:]:
            evaluate_csv(p)
    else:
        print("Usage: python3 evaluate_ablation_metrics.py <results_csv_1> [<results_csv_2> ...]")
