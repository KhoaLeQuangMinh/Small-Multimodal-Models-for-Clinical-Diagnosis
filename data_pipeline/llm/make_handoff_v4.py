#!/usr/bin/env python3
"""
Split the cleaned Part A cohort (llm/partA_present.jsonl) into work packages
for the prompt-v4 re-run.

    python3 llm/make_handoff_v4.py                  # 3 packages -> handoff_v4/

One package per PERSON, not per account.  A person runs their package on one
account until it hits its limit, then opens the same folder with their next
account and pastes RUNNER.md again; finished cases are never redone.

Same design as llm/make_handoff.py (v3), which is left untouched:
  * split by article, so sibling cases go to one person
  * stratified by the rarest candidate class, so every package has the same mix
  * a calibration set that appears in every package
"""
import argparse, collections, csv, json, os, random, shutil, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from prompt_v4 import SYSTEM, build_user, candidates, PROMPT_VERSION  # noqa: E402

COHORT = os.path.join(HERE, "partA_present.jsonl")
OUTDIR = os.path.join(ROOT, "handoff_v4")

# the same patients published under two PMC ids - keep them in one package
SAME_ARTICLE = {"PMC9650497": "PMC9469688"}

CONCURRENCY = 30
CHUNK = 10
WAIT = 45            # seconds between waves

CASE_TEMPLATE = """{system}

########################################################################
# CASE {idx} of {total}   -   case_id: {cid}
########################################################################

{user}
"""

RUNNER_MD = """# Driving prompt for package {k}

Open this folder in Antigravity, then paste the block below into the chat.

`responses/` is the progress log: a case is done when `responses/<case_id>.json`
exists and is valid JSON.  When an account hits its limit, open this same
folder with your next account, start a new session and paste the block again.
It picks up where the last session stopped and never redoes finished work.

---

```
You are running a clinical NLP annotation job over the files in this folder.

SCOPE
  `cases/` holds {ncases} .txt files. Each file is a COMPLETE, self-contained
  prompt - a system prompt plus exactly one patient case.

WHAT IS ALREADY DONE
  A case is finished when `responses/<case_id>.json` exists and contains
  valid JSON. The case_id is the part of the filename after the sequence
  number:
      0001_PMC10018284_01.txt  ->  responses/PMC10018284_01.json
  Before you start, list `cases/` and `responses/`. If a file in
  `responses/` is empty or is not valid JSON, delete it - an earlier session
  was cut off while writing it - and treat that case as not done. Then work
  only on the cases that are not done. Never redo a finished case.

HOW TO RUN IT
  Sort the remaining files by filename and split them into chunks of {chunk}.
  Launch up to {conc} subagents at the same time, one chunk each. After each
  wave finishes, wait {wait} seconds before launching the next wave. Repeat until
  no chunks remain.

  That pause is deliberate: it keeps this account under its token quota.
  Do not skip it, even if the first waves feel slow.

EACH SUBAGENT
  Give each subagent one chunk of {chunk} files and these instructions:
    - Read each file and follow the instructions inside it exactly.
    - Produce the JSON object that file asks for - nothing else, no prose
      around it, no markdown fences.
    - Write it to `responses/<case_id>.json`.
    - Treat every case as completely independent. Do not let one case
      influence another. Do not look for patterns across the {chunk}. Do not
      reason about them together or reuse a previous answer's shape. Each
      file is a different patient and a separate decision.

IF SOMETHING FAILS
  - Quota / 429 / RESOURCE_EXHAUSTED: stop launching new subagents, wait 120
    seconds, then resume from where you were. Do not drop the case. If it
    still fails after 3 tries, stop and print how many cases are done - the
    run will continue on another account.
  - A model reply that is not valid JSON: save it verbatim as
    `responses/<case_id>.raw.txt` and carry on. Do not repair it yourself.
  - A file you cannot read: note it and carry on.

RULES
  - Never modify anything in `cases/`.
  - Write nothing except files in `responses/`.
  - Do not answer any case yourself, and do not edit a model's answer.

REPORT
  After every wave print: cases done / {ncases}, and any failures so far.
  When no cases are left, print a final count and stop.

Start by listing what is already done, then begin.
```

---

## Expected

{nchunks} chunks of {chunk}, {nwaves} waves of up to {conc} subagents, {wait} seconds apart.
"""

PACKAGE_README = """# Work package {k} of {n}

**{ncases} cases.**  Prompt version `{ver}`.

## How to run it

1. Open this folder in Antigravity with your first account.
2. Paste the block in **`RUNNER.md`** into the chat.  It runs up to {conc}
   subagents at a time, {chunk} cases each.
3. When that account hits its limit, close the session, open **this same
   folder** with your next account, start a new session and paste the block
   again.  It carries on from where the last one stopped.
4. Repeat until it prints that no cases are left.

**Only one session at a time on this folder.**  Two sessions running at once
would both pick up the same unfinished cases.

**Do one chunk first.**  For the very first run, change the last line of the
runner prompt to "Do the first chunk of {chunk} only, then stop", look at what
lands in `responses/`, and only then run the rest.

### Doing it by hand instead

If the agent misbehaves, each file in `cases/` is a complete prompt on its own:
open a new session, paste the whole file, save the JSON as
`responses/<case_id>.json`.

## If something goes wrong

- **Reply is not valid JSON**: save it as `responses/<case_id>.raw.txt` and
  move on.
- **You are unsure whether the model followed the instructions**: do not fix
  it yourself.  Save what it said.

## Do not

- Do not edit the prompt.
- Do not answer the cases yourself.
- Do not use a script or extension to drive Antigravity.  Using third-party
  tools to access the service breaches its terms; pasting by hand does not.

## Calibration cases

{ncal} of your cases also appear in the other two packages.  That is how we
measure whether the packages are judged consistently.  Treat them exactly
like the rest.

## When you are done

Zip the `responses/` folder and send it back.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", type=int, default=3)
    ap.add_argument("--calibration", type=int, default=30)
    ap.add_argument("--out", default=OUTDIR)
    ap.add_argument("--seed", type=int, default=20260926)
    a = ap.parse_args()
    rnd = random.Random(a.seed)

    rows = [json.loads(l) for l in open(COHORT)]
    by_id = {r["case_id"]: r for r in rows}
    freq = collections.Counter(d for r in rows for d in candidates(r))

    # ---- calibration: keep the v3 calibration cases that survived clean-up
    # (so v4 can be compared with the 6-account v3 majority), then add one
    # single-candidate case from each class they do not cover, rarest first
    cal = [r["case_id"] for r in rows if r.get("n_accounts") == 6]
    covered = {d for c in cal for d in candidates(by_id[c])}
    for d in sorted(freq, key=lambda d: freq[d]):
        if len(cal) >= a.calibration:
            break
        if d in covered:
            continue
        pool = sorted(r["case_id"] for r in rows
                      if candidates(r) == [d] and r["case_id"] not in cal)
        if pool:
            cal.append(rnd.choice(pool))
            covered.add(d)
    cal = set(cal[:a.calibration])

    # ---- everything else: group by article, stratify by rarest candidate
    arts = collections.defaultdict(list)
    for r in rows:
        if r["case_id"] not in cal:
            arts[SAME_ARTICLE.get(r["article_id"], r["article_id"])].append(r)

    def primary(g):
        return min((d for r in g for d in candidates(r)), key=lambda d: freq[d])

    strata = collections.defaultdict(list)
    for g in arts.values():
        strata[primary(g)].append(g)
    shards = [[] for _ in range(a.packages)]
    for s in sorted(strata, key=lambda s: freq[s]):
        gs = strata[s]
        rnd.shuffle(gs)
        gs.sort(key=len, reverse=True)
        for g in gs:
            min(shards, key=len).extend(g)

    # ---- write
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    cal_rows = [by_id[c] for c in sorted(cal)]
    summary = []
    for k, shard in enumerate(shards, 1):
        pkg = sorted(shard + cal_rows, key=lambda r: r["case_id"])
        d = os.path.join(a.out, f"package-{k}")
        os.makedirs(os.path.join(d, "cases"))
        os.makedirs(os.path.join(d, "responses"))
        for i, rec in enumerate(pkg, 1):
            with open(os.path.join(d, "cases", f"{i:04d}_{rec['case_id']}.txt"), "w") as fh:
                fh.write(CASE_TEMPLATE.format(system=SYSTEM, idx=i, total=len(pkg),
                                              cid=rec["case_id"], user=build_user(rec)))
        with open(os.path.join(d, "manifest.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["seq", "case_id", "article_id", "candidates", "n_chars",
                        "calibration"])
            for i, rec in enumerate(pkg, 1):
                w.writerow([i, rec["case_id"], rec["article_id"],
                            "|".join(candidates(rec)), len(rec["case_text"]),
                            "yes" if rec["case_id"] in cal else ""])
        nch = -(-len(pkg) // CHUNK)
        fmt = dict(k=k, n=a.packages, ncases=len(pkg), ncal=len(cal),
                   ver=PROMPT_VERSION, conc=CONCURRENCY, chunk=CHUNK, wait=WAIT,
                   nchunks=nch, nwaves=-(-nch // CONCURRENCY))
        open(os.path.join(d, "README.md"), "w").write(PACKAGE_README.format(**fmt))
        open(os.path.join(d, "RUNNER.md"), "w").write(RUNNER_MD.format(**fmt))
        open(os.path.join(d, "PROMPT.md"), "w").write(
            f"# System prompt ({PROMPT_VERSION})\n\n"
            "Already included at the top of every file in `cases/`.\n"
            "Here for reference only.\n\n```\n" + SYSTEM + "\n```\n")
        with zipfile.ZipFile(d + ".zip", "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(d):
                for f in files:
                    p = os.path.join(root, f)
                    z.write(p, os.path.relpath(p, a.out))
            z.writestr(f"package-{k}/responses/", "")
        dis = collections.Counter(x for r in pkg for x in candidates(r))
        summary.append((k, len(pkg), nch, dis))

    open(os.path.join(a.out, "README.md"), "w").write(
        f"# Handoff v4 - {a.packages} work packages\n\n"
        f"Prompt `{PROMPT_VERSION}`.  Cohort: `llm/partA_present.jsonl`, "
        f"{len(rows):,} cases after clean-up.\n\n"
        "| package | cases | chunks of 10 |\n|---|---|---|\n"
        + "\n".join(f"| package-{k} | {n} | {c} |" for k, n, c, _ in summary)
        + f"\n\n{len(cal)} calibration cases appear in every package.  "
        f"Total judgements: {sum(n for _, n, _, _ in summary):,}.\n\n"
        "Give one `package-N.zip` to each person.  Each person runs it on their "
        "accounts one after another, as its README explains.\n")

    print(f"calibration: {len(cal)} cases, classes covered: {len(covered)}")
    for k, n, c, dis in summary:
        print(f"package-{k}: {n} cases, {c} chunks | "
              + ", ".join(f"{x} {v}" for x, v in dis.most_common(4)))
    print(f"wrote {a.out}/")


if __name__ == "__main__":
    main()
