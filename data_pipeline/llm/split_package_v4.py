#!/usr/bin/env python3
"""
Split one v4 work package into smaller sub-packages by a given ratio.

    python3 llm/split_package_v4.py                       # package-1 -> 1a 1b 1c, 1:2:2
    python3 llm/split_package_v4.py --package 2 --ratio 1 1

Reads the package's manifest, keeps each article in one sub-package, balances
the candidate-class mix, and writes complete folders (cases, manifest, README,
RUNNER, PROMPT, empty responses) plus a zip for each.  The parent package is
left as it is - do not run it alongside its sub-packages.
"""
import argparse, collections, csv, json, os, random, shutil, string, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from prompt_v4 import SYSTEM, build_user, candidates, PROMPT_VERSION  # noqa: E402
from make_handoff_v4 import (CASE_TEMPLATE, RUNNER_MD, PACKAGE_README,  # noqa: E402
                             SAME_ARTICLE, CONCURRENCY, CHUNK, WAIT, COHORT)

OUTDIR = os.path.join(ROOT, "handoff_v4")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", type=int, default=1)
    ap.add_argument("--ratio", type=int, nargs="+", default=[1, 2, 2])
    ap.add_argument("--seed", type=int, default=20260927)
    a = ap.parse_args()
    rnd = random.Random(a.seed)

    parent = os.path.join(OUTDIR, f"package-{a.package}")
    man = list(csv.DictReader(open(os.path.join(parent, "manifest.csv"))))
    rows = {json.loads(l)["case_id"]: json.loads(l) for l in open(COHORT)}
    recs = [rows[m["case_id"]] for m in man]
    is_cal = {m["case_id"] for m in man if m["calibration"] == "yes"}

    total = len(recs)
    targets = [total * r / sum(a.ratio) for r in a.ratio]
    freq = collections.Counter(d for r in recs for d in candidates(r))

    arts = collections.defaultdict(list)
    for r in recs:
        arts[SAME_ARTICLE.get(r["article_id"], r["article_id"])].append(r)
    strata = collections.defaultdict(list)
    for g in arts.values():
        strata[min((d for r in g for d in candidates(r)), key=lambda d: freq[d])].append(g)

    shards = [[] for _ in a.ratio]
    for s in sorted(strata, key=lambda s: freq[s]):
        gs = strata[s]
        rnd.shuffle(gs)
        gs.sort(key=len, reverse=True)
        for g in gs:                       # fill whichever is furthest below its share
            i = min(range(len(shards)), key=lambda i: (len(shards[i]) + len(g)) / targets[i])
            shards[i].extend(g)

    for i, shard in enumerate(shards):
        name = f"package-{a.package}{string.ascii_lowercase[i]}"
        d = os.path.join(OUTDIR, name)
        if os.path.exists(d):
            if os.listdir(os.path.join(d, "responses")):
                sys.exit(f"{name}/responses is not empty - refusing to overwrite")
            shutil.rmtree(d)
        os.makedirs(os.path.join(d, "cases"))
        os.makedirs(os.path.join(d, "responses"))
        pkg = sorted(shard, key=lambda r: r["case_id"])
        for j, rec in enumerate(pkg, 1):
            with open(os.path.join(d, "cases", f"{j:04d}_{rec['case_id']}.txt"), "w") as fh:
                fh.write(CASE_TEMPLATE.format(system=SYSTEM, idx=j, total=len(pkg),
                                              cid=rec["case_id"], user=build_user(rec)))
        with open(os.path.join(d, "manifest.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["seq", "case_id", "article_id", "candidates", "n_chars",
                        "calibration"])
            for j, rec in enumerate(pkg, 1):
                w.writerow([j, rec["case_id"], rec["article_id"],
                            "|".join(candidates(rec)), len(rec["case_text"]),
                            "yes" if rec["case_id"] in is_cal else ""])
        nch = -(-len(pkg) // CHUNK)
        ncal = sum(r["case_id"] in is_cal for r in pkg)
        fmt = dict(k=name.split("-")[1], n=3, ncases=len(pkg), ncal=ncal,
                   ver=PROMPT_VERSION, conc=CONCURRENCY, chunk=CHUNK, wait=WAIT,
                   nchunks=nch, nwaves=-(-nch // CONCURRENCY))
        readme = PACKAGE_README.format(**fmt).replace(
            f"# Work package {fmt['k']} of 3",
            f"# Work package {fmt['k']} (part of package {a.package})")
        open(os.path.join(d, "README.md"), "w").write(readme)
        open(os.path.join(d, "RUNNER.md"), "w").write(RUNNER_MD.format(**fmt))
        open(os.path.join(d, "PROMPT.md"), "w").write(
            f"# System prompt ({PROMPT_VERSION})\n\n"
            "Already included at the top of every file in `cases/`.\n"
            "Here for reference only.\n\n```\n" + SYSTEM + "\n```\n")
        with zipfile.ZipFile(d + ".zip", "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(d):
                for f in files:
                    p = os.path.join(root, f)
                    z.write(p, os.path.relpath(p, OUTDIR))
            z.writestr(f"{name}/responses/", "")
        top = collections.Counter(x for r in pkg for x in candidates(r)).most_common(3)
        print(f"{name}: {len(pkg)} cases ({100*len(pkg)/total:.0f}%), {nch} chunks, "
              f"{ncal} calibration | " + ", ".join(f"{x} {v}" for x, v in top))


if __name__ == "__main__":
    main()
