#!/usr/bin/env python3
"""
Verify that every evidence quote actually appears in its own case text.

    python3 llm/check_quotes.py <responses_dir> [--manifest handoff/account-N/manifest.csv]

Three failure modes, in increasing seriousness:

  title-quoted   the quote is the ARTICLE TITLE, not the case text.  The title
                 is the claim being checked, so quoting it is circular.  The
                 verdict may still be right, but the audit trail is not.
  fabricated     the quote appears nowhere in the case text, the title, the
                 MeSH or the keywords.  The model invented it.
  no-support     the whole case has no quote that appears in the case text -
                 every term was answered from the title or from nothing.

Writes <dir>/../rerun_<name>.txt - the case_ids to run again.
"""
import argparse, csv, difflib, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
COHORT = os.path.join(HERE, "cohort_partA.jsonl")
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip()
EXPLAIN = re.compile(
    r"(not (mentioned|present|found|stated|described)|does not appear|"
    r"appears? only|only (in|appears)|no mention|"
    r"\b(title|mesh|keywords?)\b.*\b(only|not)\b)", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses")
    ap.add_argument("--manifest")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    coh = {json.loads(l)["case_id"]: json.loads(l) for l in open(COHORT)}
    seq = {}
    if a.manifest:
        seq = {r["case_id"]: int(r["seq"]) for r in csv.DictReader(open(a.manifest))}

    files = sorted(f for f in os.listdir(a.responses) if f.endswith(".json"))
    counts = collections.Counter()
    rerun, detail = set(), []

    for fn in files:
        cid = fn[:-5]
        try:
            j = json.load(open(os.path.join(a.responses, fn)))
        except Exception as e:
            counts["unparseable"] += 1; rerun.add(cid)
            detail.append((cid, "-", "unparseable", str(e))); continue
        if cid not in coh:
            counts["not-in-cohort"] += 1; continue
        r = coh[cid]
        text = norm(r["case_text"])
        title = norm(r["title"]).lower()
        meta = norm(" ".join(r["mesh"]) + " " + " ".join(r["keywords"])).lower()
        has_real = False
        for v in j.get("verdicts", []):
            e = norm(v.get("evidence") or "")
            counts["terms"] += 1
            if not e:
                counts["empty"] += 1
            elif e in text:
                counts["verbatim"] += 1; has_real = True
            elif e.lower() in title or title in e.lower():
                counts["title-quoted"] += 1; rerun.add(cid)
                detail.append((cid, v.get("term"), "title-quoted", e[:90]))
            elif e.lower() in meta:
                counts["meta-quoted"] += 1; rerun.add(cid)
                detail.append((cid, v.get("term"), "meta-quoted", e[:90]))
            elif EXPLAIN.search(e):
                # the model wrote a reason ("appears only in the title") where
                # a quote belongs - no quote, but nothing invented either
                counts["explanation"] += 1
            else:
                m = difflib.SequenceMatcher(None, e, text).find_longest_match(
                    0, len(e), 0, len(text))
                counts["fabricated"] += 1; rerun.add(cid)
                detail.append((cid, v.get("term"), "fabricated",
                               f"(best run {100*m.size/max(1,len(e)):.0f}%) {e[:70]}"))
        if not has_real and j.get("verdicts"):
            counts["no-support cases"] += 1; rerun.add(cid)

    n = counts["terms"] or 1
    print(f"{len(files)} responses, {counts['terms']} term verdicts\n")
    for k in ["verbatim", "empty", "explanation", "title-quoted", "meta-quoted", "fabricated"]:
        print(f"   {k:16}{counts[k]:>6}  {100*counts[k]/n:>5.1f}%")
    print(f"\n   cases with NO case-text quote anywhere: {counts['no-support cases']}")
    print(f"   cases to re-run                       : {len(rerun)}")

    if not a.quiet and detail:
        print(f"\n{'case_id':18}{'seq':>5}  {'problem':13} term / quote")
        for cid, term, kind, q in sorted(detail, key=lambda d: seq.get(d[0], 0)):
            print(f"{cid:18}{seq.get(cid,0):>5}  {kind:13} {term} :: {q}")

    out = os.path.join(os.path.dirname(a.responses.rstrip("/")) or ".",
                       "rerun_" + os.path.basename(a.responses.rstrip("/")) + ".txt")
    open(out, "w").write("\n".join(sorted(rerun)) + "\n")
    print(f"\nre-run list -> {out}")


if __name__ == "__main__":
    main()
