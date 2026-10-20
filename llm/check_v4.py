#!/usr/bin/env python3
"""
Quality check for prompt-v4 responses.  Read-only.

    python3 llm/check_v4.py <responses_dir> [<responses_dir> ...] [--dump out.json]

Per directory it reports:
  * files, JSON that parses, responses that pass prompt_v4.valid_response
  * evidence quotes: verbatim / edited-but-real / from title or metadata /
    not found, plus explanations written into `evidence`
  * patient species, text type, candidate status and role, extra diseases
  * agreement with the cleaned v3 labels in llm/partA_present.jsonl
"""
import argparse, collections, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from prompt_v4 import valid_response, candidates  # noqa: E402

COHORT = os.path.join(HERE, "partA_present.jsonl")
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
EXPLAIN = re.compile(r"(not (mentioned|present|found|stated|described)|does not appear|"
                     r"appears? only|no mention|\b(title|mesh|keywords?)\b)", re.I)


def quote_kind(q, text, title, meta):
    q = norm(q)
    if not q:
        return "empty-string"
    if q in text:
        return "verbatim"
    parts = [p.strip(" .,;") for p in re.split(r"\.\.\.|…|\[\.\.\.\]", q)]
    parts = [p for p in parts if len(p) > 12]
    if parts and all(p in text for p in parts):
        return "edited"
    if q.lower() in title or (len(title) > 20 and title in q.lower()):
        return "title"
    if q.lower() in meta:
        return "metadata"
    if EXPLAIN.search(q):
        return "explanation"
    return "not-found"


def check(d, rows):
    out = {}
    c = collections.Counter()
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            c["non-json files"] += 1
            continue
        cid = fn[:-5]
        rec = rows.get(cid)
        if rec is None:
            # a response for a case that is not in the cohort - never assigned,
            # so the agent produced it without a case file
            c["not in cohort"] += 1
            out[cid] = {"error": "not in cohort"}
            continue
        raw = open(os.path.join(d, fn)).read()
        try:
            j = json.loads(raw)
        except Exception:
            c["unparseable"] += 1
            out[cid] = {"error": "unparseable"}
            continue
        ok, why = valid_response(j, rec)
        c["valid" if ok else "invalid"] += 1
        text = norm(rec["case_text"])
        title = norm(rec["title"]).lower()
        meta = norm(" ".join(rec["mesh"]) + " " + " ".join(rec["keywords"])).lower()
        qk = collections.Counter()
        for block in (j.get("terms") or []) + (j.get("diseases") or []):
            ev = block.get("evidence")
            if isinstance(ev, str):
                ev = [ev] if ev else []
            if not ev:
                qk["empty-list"] += 1
            for q in ev or []:
                qk[quote_kind(q, text, title, meta)] += 1
        cand = {x.get("class"): x for x in j.get("diseases") or [] if x.get("candidate")}
        extra = [x for x in j.get("diseases") or [] if not x.get("candidate")]
        out[cid] = {
            "valid": ok, "why": None if ok else why,
            "species": (j.get("patient") or {}).get("species"),
            "text_type": (j.get("patient") or {}).get("text_type"),
            "main_problem": j.get("main_problem"),
            "status": {k: v.get("status") for k, v in cand.items()},
            "role": {k: v.get("role") for k, v in cand.items()},
            "extra": [(x.get("name"), x.get("class"), x.get("role")) for x in extra],
            "quotes": dict(qk),
            "v3_labels": sorted(rec["diseases"]),
            "tags": candidates(rec),
        }
    return c, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--dump")
    a = ap.parse_args()
    rows = {json.loads(l)["case_id"]: json.loads(l) for l in open(COHORT)}
    dump = {}
    for d in a.dirs:
        c, out = check(d, rows)
        dump[d] = out
        good = {k: v for k, v in out.items() if "error" not in v}
        print(f"\n=== {d}")
        print("  files:", dict(c))
        inv = collections.Counter(v["why"].split(":")[0][:50] for v in good.values() if not v["valid"])
        if inv:
            print("  invalid reasons:", dict(inv))
        q = collections.Counter()
        for v in good.values():
            q.update(v["quotes"])
        nq = sum(n for k, n in q.items() if k != "empty-list") or 1
        print("  quotes:", ", ".join(f"{k} {n} ({100*n/nq:.1f}%)" if k != "empty-list"
                                      else f"{k} {n}" for k, n in q.most_common()))
        print("  species:", dict(collections.Counter(v["species"] for v in good.values())))
        print("  text_type:", dict(collections.Counter(v["text_type"] for v in good.values())))
        st = collections.Counter(s for v in good.values() for s in v["status"].values())
        print("  candidate status:", dict(st))
        rl = collections.Counter(r for v in good.values() for k, r in v["role"].items()
                                 if v["status"].get(k) == "present")
        print("  role of present candidates:", dict(rl))
        ex = [x for v in good.values() for x in v["extra"]]
        print(f"  extra diseases listed: {len(ex)} in "
              f"{sum(1 for v in good.values() if v['extra'])} cases; "
              f"in one of the 22 classes: "
              f"{collections.Counter(x[1] for x in ex if x[1] != 'other').most_common()}")
        # agreement with cleaned v3 labels
        agree = collections.Counter()
        for v in good.values():
            for t in v["tags"]:
                kept = t in v["v3_labels"]
                agree[(("v3 kept" if kept else "v3 removed"), v["status"].get(t))] += 1
        print("  v4 status vs cleaned v3 label:",
              ", ".join(f"{a}->{b}: {n}" for (a, b), n in sorted(agree.items(), key=str)))
    if a.dump:
        json.dump(dump, open(a.dump, "w"), indent=1)


if __name__ == "__main__":
    main()
