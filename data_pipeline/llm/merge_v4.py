#!/usr/bin/env python3
"""
Merge the prompt-v4 agent answers into the Part A dataset.

    python3 llm/merge_v4.py

Inputs
  llm/partA_present.jsonl            the 1,797 cases that were sent to v4
  handoff_v4/<package>/<responses>   one v4 answer per case (see RESPONSE_DIRS)
  Archive-001/captions_and_labels.csv + image files

Output
  llm/partA_final.jsonl   every case with its merged v4 answer and all its images

Nothing is removed: every case and every image panel is kept.  The 30
calibration cases were answered three times; their answers are combined by
majority vote per class.
"""
import collections, csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from prompt_v4 import valid_response, candidates, PROMPT_VERSION  # noqa: E402

COHORT = os.path.join(HERE, "partA_present.jsonl")
DEFAULT_ARCHIVE = os.path.join(ROOT, "Archive-001")
if not os.path.exists(DEFAULT_ARCHIVE):
    multicare = os.path.join(os.path.dirname(ROOT), "Official_MultiCaRe", "whole_multicare_dataset")
    if os.path.exists(multicare):
        DEFAULT_ARCHIVE = multicare
ARCHIVE = os.environ.get("MULTICARE_ARCHIVE", DEFAULT_ARCHIVE)
OUT = os.path.join(HERE, "partA_final.jsonl")

# Package 1c uses the re-run; its first run wrote 5 extra files under
# made-up case ids and is not used.
RESPONSE_DIRS = {
    "package-2":  "handoff_v4/package-2/package-2-responses",
    "package-3":  "handoff_v4/package-3/package-3-responses",
    "package-1a": "handoff_v4/package-1a/responses",
    "package-1b": "handoff_v4/package-1b/package-1b-responses",
    "package-1c": "handoff_v4/package-1c/packakge-1c-responses",
}


def load_answers(rows):
    got = collections.defaultdict(list)
    skipped = collections.Counter()
    for pkg, d in RESPONSE_DIRS.items():
        d = os.path.join(ROOT, d)
        for fn in sorted(os.listdir(d)):
            cid = fn[:-5]
            if not fn.endswith(".json") or cid not in rows:
                skipped[f"{pkg}: not a cohort answer"] += 1
                continue
            ok, j = valid_response(open(os.path.join(d, fn)).read(), rows[cid])
            if not ok:
                skipped[f"{pkg}: invalid"] += 1
                continue
            got[cid].append((pkg, j))
    return got, skipped


def majority(values):
    c = collections.Counter(values).most_common()
    return c[0][0] if c else None


def merge_answers(rec, answers):
    per_class = {}
    for cls in candidates(rec):
        entries = [next(x for x in j["diseases"] if x.get("candidate") and x["class"] == cls)
                   for _, j in answers]
        status = majority(e["status"] for e in entries)
        agree = [e for e in entries if e["status"] == status]
        per_class[cls] = {
            "status": status,
            "role": majority(e.get("role") for e in agree) if status == "present" else None,
            "evidence": agree[0].get("evidence", []),
            "reason": agree[0].get("reason", ""),
            "votes": [e["status"] for e in entries],
        }
    first = answers[0][1]
    return {
        "candidates": per_class,
        "species": majority(j["patient"]["species"] for _, j in answers),
        "text_type": majority(j["patient"]["text_type"] for _, j in answers),
        "main_problem": first.get("main_problem", ""),
        "extra_diagnoses": [
            {"name": x.get("name"), "class": x.get("class"), "role": x.get("role")}
            for x in first["diseases"] if not x.get("candidate")],
        "terms": first.get("terms", []),
        "note": first.get("note", ""),
        "packages": [p for p, _ in answers],
    }


def load_images(case_ids):
    csv.field_size_limit(10 ** 9)
    panels = collections.defaultdict(list)
    for r in csv.DictReader(open(os.path.join(ARCHIVE, "captions_and_labels.csv"))):
        if r["patient_id"] not in case_ids:
            continue
        f = r["file"]
        path = os.path.join(ARCHIVE, f[:4], f[:5], f)
        panels[r["patient_id"]].append({
            "file": f,
            "path": os.path.relpath(path, ROOT),
            "on_disk": os.path.exists(path),
            "image_type": r["image_type"],
            "image_subtype": r["image_subtype"],
            "caption": r["caption"],
            "license": r["license"],
        })
    return panels


def main():
    rows = {json.loads(l)["case_id"]: json.loads(l) for l in open(COHORT)}
    answers, skipped = load_answers(rows)
    missing = sorted(set(rows) - set(answers))
    if missing:
        sys.exit(f"{len(missing)} cases have no valid v4 answer, e.g. {missing[:5]}")
    panels = load_images(set(rows))

    with open(OUT, "w") as fh:
        for cid, rec in rows.items():
            m = merge_answers(rec, answers[cid])
            fh.write(json.dumps({
                "case_id": cid,
                "article_id": rec["article_id"],
                "title": rec["title"],
                "case_text": rec["case_text"],
                "present": sorted(c for c, v in m["candidates"].items()
                                  if v["status"] == "present"),
                "candidates": m["candidates"],
                "main_problem": m["main_problem"],
                "extra_diagnoses": m["extra_diagnoses"],
                "text_type": m["text_type"],
                "species": m["species"],
                "terms": m["terms"],
                "note": m["note"],
                "images": panels.get(cid, []),
                "prompt_version": PROMPT_VERSION,
                "v4_packages": m["packages"],
            }, ensure_ascii=False) + "\n")

    status = collections.Counter(v["status"] for cid in rows
                                 for v in merge_answers(rows[cid], answers[cid])["candidates"].values())
    print(f"cases {len(rows)}   answer files skipped {dict(skipped) or 'none'}")
    print(f"calibration cases merged by majority: {sum(len(a) > 1 for a in answers.values())}")
    print(f"candidate verdicts: {dict(status)}")
    print(f"image panels: {sum(len(p) for p in panels.values())} in {len(panels)} cases")
    print(f"wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
