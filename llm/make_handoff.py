#!/usr/bin/env python3
"""
Split the Part A cohort into N self-contained work packages, one per Antigravity
account, and produce a merge script to collect the answers back.

    python3 llm/make_handoff.py                 # 6 accounts, 30 calibration cases
    python3 llm/make_handoff.py --accounts 4 --calibration 40

Design decisions, and why:

* Split by ARTICLE, not by case.  Cases from one article share a title and MeSH
  and often a patient population; two people judging siblings differently is a
  pure loss.  One article -> one annotator.

* Stratified by disease.  Each account gets roughly the same disease mix, so a
  per-account error rate is comparable, and losing an account costs you a
  representative slice rather than an entire class.

* A CALIBRATION set appears in EVERY package - the same cases for all accounts.
  Without overlap you cannot tell whether account 3 is systematically stricter
  than account 5.  These are drawn, where possible, from the 300 cases that
  already carry two independent labels, so each account can also be scored
  against a known reference.

* Every case file is the COMPLETE prompt - system + case in one block.  Each
  Antigravity session starts cold, so there is nothing to remember and nothing
  to paste twice.  Select all, paste, done.
"""
import argparse, collections, csv, json, os, random, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from prompt import SYSTEM, build_user, PROMPT_VERSION  # noqa: E402

COHORT = os.path.join(HERE, "cohort_partA.jsonl")
PILOT  = os.path.join(HERE, "assertions.jsonl")       # 300 already-judged cases
OUTDIR = os.path.join(ROOT, "handoff")

CASE_TEMPLATE = """{system}

########################################################################
# CASE {idx} of {total}   -   case_id: {cid}
########################################################################

{user}
"""

RUNNER_MD = """# Driving prompt for account {k}

Open this folder in Antigravity, then paste the block below into the chat.

`responses/` is the progress log: a case is done when `responses/<case_id>.json`
exists.  Restarting is safe and never redoes finished work.

---

```
You are running a clinical NLP annotation job over the files in this folder.

SCOPE
  `cases/` holds {ncases} .txt files. Each file is a COMPLETE, self-contained
  prompt - a system prompt plus exactly one patient case.

WHAT IS ALREADY DONE
  A case is finished when `responses/<case_id>.json` exists. The case_id is the
  part of the filename after the sequence number:
      0001_PMC10018284_01.txt  ->  responses/PMC10018284_01.json
  Before you start, list `cases/` and `responses/`, and work only on the
  difference. Never redo a finished case.

HOW TO RUN IT
  Sort the remaining files by filename and split them into chunks of 10.
  Process 3 chunks at a time using 3 concurrent subagents - no more than 3.
  After each wave of 3 finishes, wait 45 seconds before launching the next.

  That pacing is deliberate: it is what keeps this account under its token
  quota. Do not raise the concurrency and do not skip the cooldown, even if
  the first few waves feel slow.

EACH SUBAGENT
  Give each subagent one chunk of 10 files and these instructions:
    - Read each file and follow the instructions inside it exactly.
    - Produce the JSON object that file asks for - nothing else, no prose
      around it, no markdown fences.
    - Write it to `responses/<case_id>.json`.
    - Treat every case as completely independent. Do not let one case
      influence another. Do not look for patterns across the 10. Do not
      reason about them together or reuse a previous answer's shape. Each
      file is a different patient and a separate decision.

IF SOMETHING FAILS
  - Quota / 429 / RESOURCE_EXHAUSTED: stop launching new waves, wait 120
    seconds, then resume from where you were. Do not drop the case.
  - A model reply that is not valid JSON: save it verbatim as
    `responses/<case_id>.raw.txt` and carry on. Do not repair it yourself.
  - A file you cannot read: note it and carry on.

RULES
  - Never modify anything in `cases/`.
  - Write nothing except files in `responses/`.
  - Do not answer any case yourself, and do not edit a model's answer.

REPORT
  After every wave print: cases done / {ncases}, and any failures so far.
  When the difference is empty, print a final count and stop.

Start by listing what is already done, then begin.
```

---

## Expected

{nchunks} chunks, ~{nwaves} waves of 3.  Roughly 1-1.5 hours.

## Before the full run

Do one wave only - change the last line to "Do the first chunk of 10 only,
then stop".  Then take case 10 of that chunk, open a brand new session, paste
`cases/<that file>` by hand, and compare the two answers.

If they match, the chunking is safe.  If they differ, the cases in a chunk are
contaminating each other and the chunk size needs to come down.
"""

ACCOUNT_README = """# Work package {k} of {n}

**{ncases} cases.**  Prompt version `{ver}`.

## How to run it

Open this folder in Antigravity and paste the block in **`RUNNER.md`**.  It
drives the whole package: chunks of 10, 3 subagents at a time, 45 seconds
between waves.  That pacing is what keeps you under the account's token quota.

Roughly 1-1.5 hours.  You can stop and restart at any point - a case counts as
done once `responses/<case_id>.json` exists, and finished work is never redone.

**Do one chunk first.**  Change the last line of the runner prompt to "Do the
first chunk of 10 only, then stop", look at what lands in `responses/`, and
only then let it run the rest.

### Doing it by hand instead

If the agent misbehaves, each file in `cases/` is a complete prompt on its own:
open a new session, paste the whole file, save the JSON as
`responses/<case_id>.json`.  One session per case.  Slower, but it always
works.

## If something goes wrong

- **Model refuses or errors**: save `{{"verdict": "ERROR", "note": "<what happened>"}}`
- **Reply is not valid JSON**: save it anyway as `responses/<case_id>.raw.txt`
  and move on; we will re-run those few by API.
- **You are unsure whether the model followed the instructions**: do not fix it
  yourself.  Save what it said.  We measure the model, not your correction.

## Do not

- Do not edit the prompt.
- Do not answer the cases yourself.
- Do not use a script or extension to drive Antigravity.  Using third-party
  tools to access the service breaches its terms; pasting by hand does not.

## Calibration cases

{ncal} of your cases also appear in everyone else's package.  That is deliberate
- it is how we measure whether the six of us are judging consistently.  Treat
them exactly like the rest; do not compare notes on them.

## When you are done

Zip the `responses/` folder and send it back.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", type=int, default=6)
    ap.add_argument("--calibration", type=int, default=30)
    ap.add_argument("--out", default=OUTDIR)
    ap.add_argument("--seed", type=int, default=20260922)
    a = ap.parse_args()
    rnd = random.Random(a.seed)

    if not os.path.exists(COHORT):
        sys.exit("run llm/build_partA.py first")
    rows = [json.loads(l) for l in open(COHORT)]
    by_id = {r["case_id"]: r for r in rows}

    # ---- calibration set: prefer cases that already have independent labels
    judged = set()
    if os.path.exists(PILOT):
        for l in open(PILOT):
            try:
                judged.add(json.loads(l)["case_id"])
            except Exception:
                pass
    pool = sorted(judged & set(by_id))
    rnd.shuffle(pool)
    cal = pool[:a.calibration]
    if len(cal) < a.calibration:                       # top up from the cohort
        rest = sorted(set(by_id) - set(cal))
        rnd.shuffle(rest)
        cal += rest[:a.calibration - len(cal)]
    cal = set(cal)
    print(f"calibration: {len(cal)} cases "
          f"({len(cal & judged)} of them already have two independent labels)")

    # ---- everything else, grouped by article, stratified by primary disease
    work = [r for r in rows if r["case_id"] not in cal]
    arts = collections.defaultdict(list)
    for r in work:
        arts[r["article_id"]].append(r)

    def primary(group):
        """Rarest disease in the group - so rare classes drive the stratum."""
        ds = [d for r in group for d in r["diseases"]]
        return min(ds, key=lambda d: freq[d]) if ds else "?"

    freq = collections.Counter(d for r in work for d in r["diseases"])
    groups = sorted(arts.values(), key=lambda g: (primary(g), -len(g)))

    # greedy round-robin within each disease stratum -> even size AND even mix
    shards = [[] for _ in range(a.accounts)]
    for stratum, gs in collections.OrderedDict(
            (k, [g for g in groups if primary(g) == k])
            for k in sorted({primary(g) for g in groups})).items():
        rnd.shuffle(gs)
        for g in gs:
            shards.sort(key=lambda s: len(s))
            shards[0].extend(g)

    # ---- write the packages
    if os.path.exists(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)

    cal_rows = [by_id[c] for c in sorted(cal)]
    summary = []
    for k, shard in enumerate(shards, 1):
        pkg = shard + cal_rows
        pkg.sort(key=lambda r: r["case_id"])
        d = os.path.join(a.out, f"account-{k}")
        os.makedirs(os.path.join(d, "cases"))
        os.makedirs(os.path.join(d, "responses"))

        for i, rec in enumerate(pkg, 1):
            fn = f"{i:04d}_{rec['case_id']}.txt"
            with open(os.path.join(d, "cases", fn), "w") as fh:
                fh.write(CASE_TEMPLATE.format(
                    system=SYSTEM, idx=i, total=len(pkg),
                    cid=rec["case_id"], user=build_user(rec)))

        with open(os.path.join(d, "manifest.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["seq", "case_id", "article_id", "diseases",
                        "n_images", "n_chars", "calibration"])
            for i, rec in enumerate(pkg, 1):
                w.writerow([i, rec["case_id"], rec["article_id"],
                            "|".join(sorted(rec["diseases"])),
                            rec["n_images"], len(rec["case_text"]),
                            "yes" if rec["case_id"] in cal else ""])

        open(os.path.join(d, "README.md"), "w").write(ACCOUNT_README.format(
            k=k, n=a.accounts, ncases=len(pkg), ncal=len(cal), ver=PROMPT_VERSION))
        nch = -(-len(pkg) // 10)
        open(os.path.join(d, "RUNNER.md"), "w").write(RUNNER_MD.format(
            k=k, ncases=len(pkg), nchunks=nch, nwaves=-(-nch // 3)))
        open(os.path.join(d, "PROMPT.md"), "w").write(
            f"# System prompt ({PROMPT_VERSION})\n\n"
            "Already included at the top of every file in `cases/`.\n"
            "Here for reference only.\n\n```\n" + SYSTEM + "\n```\n")

        dis = collections.Counter(d2 for r in pkg for d2 in r["diseases"])
        summary.append((k, len(pkg), sum(1 for r in pkg if r["n_images"]), dis))

    # ---- top-level README + merge script
    open(os.path.join(a.out, "README.md"), "w").write(f"""# Handoff - {a.accounts} work packages

Prompt `{PROMPT_VERSION}`.  Cohort: 2,437 cases, 22 tropical diseases.

| package | cases | with images |
|---|---|---|
""" + "\n".join(f"| account-{k} | {n} | {ni} |" for k, n, ni, _ in summary) + f"""

{len(cal)} calibration cases appear in **every** package, so the same case is
judged {a.accounts} times.  Unique cases: {len(rows)}.  Total judgements:
{sum(n for _, n, _, _ in summary)}.

## Hand out

Give one `account-N/` folder to each person.  Each is self-contained - the
prompt is already inside every case file.

## Collect

Zip `account-N/responses/` back, unzip in place, then:

    python3 handoff/merge_responses.py

That writes `llm/assertions_agents.jsonl` in the same shape as the API runs,
and prints per-account agreement on the calibration cases.
""")

    shutil.copy(os.path.join(HERE, "merge_responses.py"),
                os.path.join(a.out, "merge_responses.py")) \
        if os.path.exists(os.path.join(HERE, "merge_responses.py")) else None

    print(f"\n{'package':12}{'cases':>7}{'w/img':>7}   biggest classes")
    for k, n, ni, dis in summary:
        top = ", ".join(f"{d} {c}" for d, c in dis.most_common(3))
        print(f"account-{k:<4}{n:>7}{ni:>7}   {top}")
    print(f"\nwrote {a.out}/")


if __name__ == "__main__":
    main()
