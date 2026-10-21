#!/usr/bin/env python3
"""
Collect the six accounts' answers back into one file, and report quality.

    python3 handoff/merge_responses.py          # run from anywhere

Reads   handoff/account-*/responses/<case_id>.json
Writes  llm/assertions_agents.jsonl      (same shape as the API runs)
        llm/handoff_report.txt

Reports, in order of how much they matter:

  1. COVERAGE      which cases are still missing, per account
  2. CALIBRATION   the cases everyone judged - do the accounts agree?
                   this is the number that tells you whether the six sets of
                   answers can be pooled at all
  3. REFERENCE     calibration cases that already carry two independent labels
                   from the pilot, so each account is scored against a known
                   answer rather than only against its peers
  4. SPLIT         present / absent / uncertain per account - a account whose
                   uncertain rate is 3x everyone else's is reading the prompt
                   differently
"""
import collections, csv, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "llm" else HERE
HAND = os.path.join(ROOT, "handoff")
LLM  = os.path.join(ROOT, "llm")
OUT  = os.path.join(LLM, "assertions_agents.jsonl")
REP  = os.path.join(LLM, "handoff_report.txt")

VERDICTS = {"present", "absent", "uncertain"}
JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def parse(path):
    """Tolerant: accepts a bare JSON file, or prose with JSON somewhere in it."""
    raw = open(path, encoding="utf-8", errors="replace").read().strip()
    try:
        return json.loads(raw), None
    except Exception:
        pass
    m = JSON_BLOCK.search(raw)
    if m:
        try:
            return json.loads(m.group(0)), "extracted from surrounding prose"
        except Exception as e:
            return None, f"JSON block did not parse: {e}"
    return None, "no JSON found"


def main():
    if not os.path.isdir(HAND):
        sys.exit(f"{HAND} not found - run llm/make_handoff.py first")

    manifests, cal = {}, set()
    for mf in sorted(glob.glob(os.path.join(HAND, "account-*", "manifest.csv"))):
        acct = os.path.basename(os.path.dirname(mf))
        rows = list(csv.DictReader(open(mf)))
        manifests[acct] = rows
        for r in rows:
            if r["calibration"] == "yes":
                cal.add(r["case_id"])

    got = collections.defaultdict(dict)      # acct -> case_id -> record
    problems = []
    for acct in sorted(manifests):
        for p in glob.glob(os.path.join(HAND, acct, "responses", "*.json")):
            cid = os.path.basename(p)[:-5]
            j, warn = parse(p)
            if j is None:
                problems.append((acct, cid, warn))
                continue
            if warn:
                problems.append((acct, cid, warn))
            got[acct][cid] = j
        for p in glob.glob(os.path.join(HAND, acct, "responses", "*.raw.txt")):
            problems.append((acct, os.path.basename(p), "saved as raw text"))

    L = []
    L.append("1. COVERAGE")
    L.append(f"   {'account':12}{'expected':>10}{'received':>10}{'missing':>9}")
    missing = {}
    for acct, rows in manifests.items():
        exp = {r["case_id"] for r in rows}
        miss = sorted(exp - set(got[acct]))
        missing[acct] = miss
        L.append(f"   {acct:12}{len(exp):>10}{len(got[acct]):>10}{len(miss):>9}")
    tot_missing = sum(len(v) for v in missing.values())
    if tot_missing:
        L.append(f"   -> {tot_missing} missing; first few per account:")
        for acct, miss in missing.items():
            if miss:
                L.append(f"      {acct}: {', '.join(miss[:6])}"
                         f"{' ...' if len(miss) > 6 else ''}")

    L.append("\n2. CALIBRATION - the cases every account judged")
    if not cal:
        L.append("   none defined")
    else:
        rowsv = []
        for cid in sorted(cal):
            vs = {a: (got[a].get(cid) or {}).get("verdict") for a in manifests}
            vs = {a: v for a, v in vs.items() if v}
            if len(vs) < 2:
                continue
            c = collections.Counter(vs.values())
            rowsv.append((cid, c.most_common(1)[0][1] / len(vs), vs))
        if rowsv:
            unan = sum(1 for _, f, _ in rowsv if f == 1.0)
            L.append(f"   {len(rowsv)} calibration cases with >=2 answers")
            L.append(f"   unanimous: {unan}/{len(rowsv)} ({100*unan/len(rowsv):.0f}%)")
            L.append(f"   mean majority agreement: "
                     f"{100*sum(f for _, f, _ in rowsv)/len(rowsv):.0f}%")
            split = [(c, f, v) for c, f, v in rowsv if f < 1.0]
            if split:
                L.append(f"   cases the accounts split on ({len(split)}):")
                for cid, f, vs in split[:15]:
                    L.append(f"      {cid}: " +
                             "  ".join(f"{a.split('-')[1]}={v}" for a, v in sorted(vs.items())))
        else:
            L.append("   not enough answers yet")

    L.append("\n3. REFERENCE - calibration cases with existing independent labels")
    pilot = {}
    pj = os.path.join(LLM, "assertions.jsonl")
    if os.path.exists(pj):
        for l in open(pj):
            try:
                r = json.loads(l)
                pilot[r["case_id"]] = json.loads(r["text"]).get("is_target_case")
            except Exception:
                pass
    ref = sorted(c for c in cal if c in pilot)
    if not ref:
        L.append("   none of the calibration cases were in the pilot")
    else:
        L.append(f"   {len(ref)} reference cases")
        L.append(f"   {'account':12}{'n':>5}{'agree':>7}{'rate':>7}")
        for acct in sorted(manifests):
            hits = [(c, got[acct][c]) for c in ref if c in got[acct]]
            if not hits:
                continue
            ok = sum(1 for c, j in hits
                     if (j.get("verdict") == "present") == bool(pilot[c]))
            L.append(f"   {acct:12}{len(hits):>5}{ok:>7}{100*ok/len(hits):>6.0f}%")
        L.append("   (pilot label is itself ~88% accurate - treat as a tripwire,")
        L.append("    not ground truth)")

    L.append("\n4. SPLIT per account")
    L.append(f"   {'account':12}{'n':>6}{'present':>9}{'absent':>8}{'uncert':>8}"
             f"{'bad':>6}")
    for acct in sorted(manifests):
        c = collections.Counter()
        for j in got[acct].values():
            v = j.get("verdict")
            c[v if v in VERDICTS else "bad"] += 1
        n = sum(c.values()) or 1
        L.append(f"   {acct:12}{n:>6}{c['present']:>9}{c['absent']:>8}"
                 f"{c['uncertain']:>8}{c['bad']:>6}")

    if problems:
        L.append(f"\n5. PROBLEM FILES ({len(problems)})")
        for acct, cid, why in problems[:30]:
            L.append(f"   {acct} {cid}: {why}")

    # ---- write the merged file (calibration cases: majority verdict)
    n_out = 0
    with open(OUT, "w") as fh:
        seen = set()
        for acct in sorted(manifests):
            for cid, j in sorted(got[acct].items()):
                if cid in cal:
                    continue
                if cid in seen:
                    continue
                seen.add(cid)
                fh.write(json.dumps({"case_id": cid, "source": acct,
                                     "text": json.dumps(j)}, ensure_ascii=False) + "\n")
                n_out += 1
        for cid in sorted(cal):
            vs = {a: got[a][cid] for a in manifests if cid in got[a]}
            if not vs:
                continue
            c = collections.Counter(j.get("verdict") for j in vs.values())
            top, cnt = c.most_common(1)[0]
            pick = next(j for j in vs.values() if j.get("verdict") == top)
            fh.write(json.dumps({"case_id": cid, "source": "calibration",
                                 "n_raters": len(vs), "agreement": cnt / len(vs),
                                 "text": json.dumps(pick)}, ensure_ascii=False) + "\n")
            n_out += 1

    L.append(f"\nwrote {OUT}  ({n_out:,} cases)")
    rep = "\n".join(L)
    open(REP, "w").write(rep + "\n")
    print(rep)
    print(f"\nreport also at {REP}")


if __name__ == "__main__":
    main()
