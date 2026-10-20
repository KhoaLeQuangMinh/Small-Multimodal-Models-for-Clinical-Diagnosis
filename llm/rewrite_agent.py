#!/usr/bin/env python3
"""
Blind rewrite of each case into a teaching case, adapted from MedCaseReasoning
(Wu et al., 2025, arXiv 2505.11733), Prompts 1 and 2.

The agent sees only the numbered case text - not our label, title or captions - and returns:
  case_prompt            the presentation up to the point before the diagnosis is reached
  diagnostic_reasoning   numbered reasons, each with a verbatim quote and its sentence number
  final_diagnosis        one disease/entity name (a blind re-label of the case)
  rubric                 the five MedCaseReasoning quality criteria, unchanged

Changes from the paper, and why:
  - JSON instead of XML tags, so the existing Antigravity runner and checks apply
  - the input is MultiCaRe's case text (numbered sentences), not the full article; the
    differential / transparency criteria are recorded but not used as filters
  - quotes must be verbatim (ellipses allowed between exact fragments); the paper allowed paraphrase
  - numbers must be copied exactly; no unit conversion
  - the case prompt must not name organisms, organism-specific tests or disease-specific drugs

Hard checks (a failure makes the answer invalid, so the case is re-run): JSON shape, case_id,
quote fragments found in the cited sentence, rubric values.  Soft checks (recorded as flags,
nothing is dropped): disease / organism / drug terms in the case prompt, numbers not in the
source, figure references, blind diagnosis vs our label.

    python3 llm/rewrite_agent.py build --ids ids.txt --out handoff_rewrite/pilot50
    python3 llm/rewrite_agent.py check handoff_rewrite/pilot50/responses
    python3 llm/rewrite_agent.py apply handoff_rewrite/pilot50/responses --out llm/rewrite_pilot50.jsonl
"""
import argparse, collections, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mask_regex import sentences, TERMS, ABBREV, GENUS_INITIAL, _word_rx  # noqa: E402
from mask_agent import RUNNER_MD as _MASK_RUNNER  # noqa: E402

DATA = os.path.join(HERE, "partA_final.jsonl")
PROMPT_VERSION = "rewrite-v1-2026-10-12"

SYSTEM = """You are an expert clinician-educator.
Your job is to transform a published case report into a teaching diagnostic case that medical
students can work through step by step. In terms of style, think of NEJM's Clinicopathologic
Conferences ("Case Records of the Massachusetts General Hospital") as a template.
You will also grade the case report with a rubric.

You will get:
  SENTENCES   the case text of the report, one numbered sentence per line (S1, S2, ...)

RULES (read carefully - no exceptions)

1. Source fidelity - extract facts only from SENTENCES.
   - Do NOT invent, embellish, or "smooth out" missing data.
   - Paraphrase narrative prose where helpful, but never add new facts.
   - Copy every number, unit and value exactly as written. Do not convert units or round.

2. Structure the teaching case in three phases:
   case presentation -> diagnostic reasoning -> final diagnosis

3. What goes in "case_prompt"
   - Present only the facts known before a working differential was made: age, sex, chief
     complaint, history of present illness, relevant past history and medications, exposures
     (residence, travel, occupation, animals, food, water, contacts), vital signs, physical
     examination, and early, routine investigations and imaging.
   - Stop at the breakpoint. Leave out everything that establishes or confirms the diagnosis and
     everything after it: the organism seen, grown or detected (microscopy, culture, PCR, antigen
     tests), disease-specific serology, biopsy and histology results, pathognomonic findings,
     the diagnosis itself, specific treatment, response to treatment, and outcome.
   - Do not name the final diagnosis, its synonyms or abbreviations, the organism at any level
     (genus, species, strain), tests named after the organism, or disease-specific drugs. Do not
     write wording that hints at it ("endemic for ...", "suggestive of ..."). Describe findings,
     not conclusions: write "a 6 cm hypodense lesion in the right lower lobe", not the name of
     the lesion if that name gives the diagnosis away.
   - Do not refer to figures or tables ("Figure 1", "Table 2"). Describe imaging findings only
     from what the text says.
   - Present the facts in the order of the case report, as close as possible to its style.
   - If the report gives little information before the diagnosis, write what there is. Never
     fill the gap; score thoroughness accordingly.

4. What goes in "diagnostic_reasoning"
   - A numbered list. Each entry: a concise summary of one reason, its role, the sentence number
     "s", and a direct quote from sentence s.
   - role "supports": a finding the case text uses to establish the final diagnosis.
     role "excludes": an alternative diagnosis the case text mentions, with why it was
     considered and why it was excluded.
   - Include every alternative diagnosis the text mentions.
   - The quote is copied from sentence s character for character. You may shorten it with
     "..." but every part between the dots must be exact.
   - Quotes must justify why one possibility rose or fell in likelihood.

5. What goes in "final_diagnosis"
   - The single disease/entity name the authors reached for this patient (e.g. "sarcoidosis").
   - No adjectives, punctuation, or explanatory text.
   - If the case text states no diagnosis, write "not stated".

6. What goes in "think"
   - core_tension: what makes this case non-trivial or interesting.
   - breakpoint: what you include and exclude so students have enough data to reason, but no
     spoilers.
   - distinctions: how the authors separated the final diagnosis from look-alikes.
   One or two short sentences each.

7. RUBRIC (score the case text as given)
   case_presentation        THOROUGHNESS OF CASE PRESENTATION (1-5)
                            look for: HPI, past history, meds, allergies, vitals, focused exam,
                            labs, imaging, hospital course, outcome
                              1 seriously deficient (identifiers only; no vitals)
                              2 major gaps (HPI + vitals OR exam, not both)
                              3 adequate (present but sketchy details)
                              4 very good (complete data, clear timeline)
                              5 exemplary (serial data and course, high quality)
   differential_diagnosis   EXPLICIT DIFFERENTIAL DIAGNOSIS (Yes/No)
                            >= 2 plausible alternatives discussed? Yes, else No
   integrative_reasoning    DEPENDENCE ON INTEGRATIVE CLINICAL REASONING (1-5)
                            need to combine >= 2 data points (history, labs, etc.)
                              1 trivial: a lone clue gives the answer
                              2 minimal: one dominant clue
                              3 moderate: must merge two findings
                              4 high: three or more clues; requires synthesis
                              5 outstanding: stepwise, complex reasoning
   transparency             TRANSPARENCY OF DIAGNOSTIC REASONING PROCESS (1-5)
                              1 none (no rationale)
                              2 superficial (lists without "why")
                              3 adequate (brief pivots)
                              4 detailed (stepwise, probabilities)
                              5 model (structured, addresses pitfalls)
   final_diagnosis_stated   STATED FINAL DIAGNOSIS (Yes/No): is the diagnosis clearly named?
   - If the text is not actually a patient case, use "NA" for every rubric score.
   - When scoring integrative_reasoning, think through whether the final diagnosis can be
     reasonably deduced from the case presentation.

Return ONLY this JSON object, no prose, no markdown fences:
{
  "case_id": "<as given>",
  "think": {"core_tension": "...", "breakpoint": "...", "distinctions": "..."},
  "case_prompt": "<the case presentation, faithful to the report, stopping at the breakpoint>",
  "diagnostic_reasoning": [
    {"summary": "<one reason>", "role": "supports|excludes", "s": <sentence number>,
     "quote": "<copied from sentence s>"}
  ],
  "final_diagnosis": "<single disease/entity name, or not stated>",
  "rubric": {"case_presentation": <1-5 or "NA">, "differential_diagnosis": "Yes|No|NA",
             "integrative_reasoning": <1-5 or "NA">, "transparency": <1-5 or "NA">,
             "final_diagnosis_stated": "Yes|No|NA"},
  "note": "<optional, empty if nothing>"
}"""

# --- leak and fidelity checks on the rewritten case prompt --------------------------------------

# terms the masking regex missed (found in the masking review); checked here as well
EXTRA_TERMS = {"Tuberculosis": ["ripe", "rhze", "2hrze", "isohydrazide", "pyrazinamid", "rifampicine"],
               "Malaria": ["lumefantrine"], "Leishmaniasis": ["antimoniate", "antimonate"]}


def _class_rx(words):
    return re.compile(r"(?<![\w])(?:" + "|".join(_word_rx(w) for w in sorted(words, key=len, reverse=True))
                      + r")(?![\w])", re.I)


CLASS_RX = {c: _class_rx(ws + EXTRA_TERMS.get(c, []) + ([c] if not c.startswith("_") else []))
            for c, ws in TERMS.items()}
SPECIES_RX = re.compile(r"\b[A-Z]\.\s?(?:" + "|".join(GENUS_INITIAL) + r")\b")
ABBREV_RX = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(a) for a in ABBREV) + r")(?![A-Za-z0-9])")
FIG_RX = re.compile(r"\b(?:fig(?:ure)?s?\.?\s*\d|table\s*\d)", re.I)
NUM_RX = re.compile(r"\d+(?:[.,]\d+)?")

norm = lambda s: re.sub(r"\s+", " ", s).strip()


def leaks(text):
    """{class: [matched words]} for disease, organism and drug terms found in text"""
    out = collections.defaultdict(list)
    for c, rx in CLASS_RX.items():
        for m in rx.finditer(text):
            out[c].append(m.group(0))
    for m in SPECIES_RX.finditer(text):
        out["_species"].append(m.group(0))
    for m in ABBREV_RX.finditer(text):
        out["_abbrev"].append(m.group(0))
    return dict(out)


def new_numbers(prompt, source):
    """numbers > 10 or with a decimal point that appear in the rewrite but not in the source"""
    have = set(NUM_RX.findall(source))
    out = []
    for n in NUM_RX.findall(prompt):
        if n in have:
            continue
        if "." in n or "," in n or int(n) > 10:
            out.append(n)
    return out


# for matching the blind diagnosis only: class abbreviations, and terms inside longer words
# ("neuroschistosomiasis", "TB lymphadenitis")
DX_ABBREV = {"Tuberculosis": ["TB", "MTB", "PTB", "EPTB", "TBM"], "Dengue": ["DF", "DHF", "DSS", "DENV"],
             "Leishmaniasis": ["VL", "CL", "MCL", "PKDL"], "Neurocysticercosis": ["NCC"],
             "Paracoccidioidomycosis": ["PCM"], "Zika Virus": ["ZIKV", "CZS"],
             "Viral Hemorrhagic Fevers": ["EVD", "CCHF", "MVD"]}
# disease forms named without the class word (packages 2-3: "scrofuloderma", "blackwater fever")
DX_FORMS = {"Tuberculosis": ["scrofuloderma", "spina ventosa", "tuberculid"], "Malaria": ["blackwater fever"]}
DX_RX = {c: re.compile(r"(?:" + "|".join(_word_rx(w) for w in sorted(ws + DX_FORMS.get(c, []) + ([c] if not c.startswith("_") else []),
                                                                     key=len, reverse=True)) + r")", re.I)
         for c, ws in TERMS.items()}
DX_ABBREV_RX = {c: re.compile(r"(?<![A-Za-z])(?:" + "|".join(ws) + r")(?![A-Za-z])") for c, ws in DX_ABBREV.items()}


def _dx_names(final_dx, c):
    return bool(DX_RX[c].search(final_dx) or (c in DX_ABBREV_RX and DX_ABBREV_RX[c].search(final_dx)))


def label_match(final_dx, present):
    """approximate: does the blind diagnosis name one of our label classes?"""
    final_dx = final_dx or ""
    hits = {c for c in present if _dx_names(final_dx, c)}
    others = {c for c in DX_RX if not c.startswith("_") and c not in present and _dx_names(final_dx, c)}
    return {"matches_label": sorted(hits), "names_other_class": sorted(others)}


def flags(rec, j):
    cp = j["case_prompt"]
    lk = leaks(cp)
    own = sorted({w for c in rec["present"] for w in lk.get(c, [])})
    other = sorted({w for c, ws in lk.items() if c not in rec["present"] for w in ws})
    return {"leak_label_terms": own, "leak_other_terms": other,
            "new_numbers": new_numbers(cp, rec["case_text"]),
            "figure_refs": FIG_RX.findall(cp),
            **label_match(j["final_diagnosis"], rec["present"])}


# --- validation -----------------------------------------------------------------------------------

def load_rows():
    return {json.loads(l)["case_id"]: json.loads(l) for l in open(DATA)}


def build_user(rec):
    lines = [f"S{i}: {s}" for i, s in enumerate(sentences(rec["case_text"]), 1)]
    return f"case_id: {rec['case_id']}\n\nSENTENCES:\n" + "\n".join(lines)


def quote_ok(q, sent):
    """every fragment between ellipses is in the sentence (case-insensitive)"""
    parts = [p.strip(" .,;").lower() for p in re.split(r"\.\.\.|…", norm(q))]
    parts = [p for p in parts if len(p) >= 4]
    return bool(parts) and all(p in norm(sent).lower() for p in parts)


def quote_in(q, sents, s):
    """quote found in sentence s, or across s and up to two neighbours on each side (our sentence
    splitter cuts a sentence at "(Fig." - PMC8022158_01 S48-S50 is one sentence)"""
    return quote_ok(q, sents[s - 1]) or quote_ok(q, " ".join(sents[max(0, s - 3):s + 2]))


SCORE = {1, 2, 3, 4, 5, "NA"}
YESNO = {"Yes", "No", "NA"}


def validate(text, rec):
    try:
        j = json.loads(text) if isinstance(text, str) else text
    except Exception as e:
        return False, f"not JSON: {e}"
    if not isinstance(j, dict) or j.get("case_id") != rec["case_id"]:
        return False, "case_id mismatch"
    for k in ("case_prompt", "final_diagnosis"):
        if not isinstance(j.get(k), str) or not j[k].strip():
            return False, f"{k} missing"
    if len(j["final_diagnosis"]) > 120:
        return False, "final_diagnosis too long"
    dr = j.get("diagnostic_reasoning")
    if not isinstance(dr, list):
        return False, "diagnostic_reasoning not a list"
    sents = sentences(rec["case_text"])
    for e in dr:
        if not isinstance(e, dict) or e.get("role") not in ("supports", "excludes"):
            return False, "bad diagnostic_reasoning entry"
        s = e.get("s")
        if not isinstance(s, int) or not 1 <= s <= len(sents):
            return False, f"sentence number out of range: {s}"
        if not quote_in(e.get("quote") or "", sents, s):
            return False, f"quote not found verbatim in S{s}"
    r = j.get("rubric")
    if not isinstance(r, dict):
        return False, "rubric missing"
    for k in ("case_presentation", "integrative_reasoning", "transparency"):
        if r.get(k) not in SCORE:
            return False, f"rubric {k} invalid: {r.get(k)}"
    for k in ("differential_diagnosis", "final_diagnosis_stated"):
        if r.get(k) not in YESNO:
            return False, f"rubric {k} invalid: {r.get(k)}"
    return True, j


# --- commands -------------------------------------------------------------------------------------

def cmd_build(a):
    rows = load_rows()
    ids = [l.strip() for l in open(a.ids) if l.strip()]
    bad = [i for i in ids if i not in rows or not rows[i]["present"]]
    if bad:
        sys.exit(f"unknown case ids or cases with no class: {bad[:5]}")
    os.makedirs(os.path.join(a.out, "cases"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "responses"), exist_ok=True)
    if os.listdir(os.path.join(a.out, "responses")):
        sys.exit("responses/ is not empty - refusing to rebuild over finished work")
    with open(os.path.join(a.out, "manifest.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "case_id"])          # the label is deliberately not in the package
        for k, cid in enumerate(ids, 1):
            fn = f"{k:04d}_{cid}.txt"
            open(os.path.join(a.out, "cases", fn), "w").write(
                f"=== SYSTEM PROMPT ({PROMPT_VERSION}) ===\n{SYSTEM}\n\n=== CASE ===\n{build_user(rows[cid])}\n")
            w.writerow([fn, cid])
    nch = -(-len(ids) // 10)
    open(os.path.join(a.out, "RUNNER.md"), "w").write(RUNNER_MD.format(
        k=os.path.basename(a.out).replace("package-", ""), ncases=len(ids), chunk=10, conc=30, wait=45,
        nchunks=nch, nwaves=-(-nch // 30), ver=PROMPT_VERSION))
    print(f"wrote {len(ids)} case files to {a.out}")


def cmd_check(a):
    rows = load_rows()
    c, why, fl = collections.Counter(), collections.Counter(), collections.Counter()
    rub = collections.defaultdict(collections.Counter)
    for fn in sorted(os.listdir(a.dir)):
        cid = fn.rsplit(".", 1)[0]
        if not fn.endswith(".json"):
            c["non-json files"] += 1
            continue
        if cid not in rows:
            c["not in dataset"] += 1
            continue
        ok, j = validate(open(os.path.join(a.dir, fn)).read(), rows[cid])
        if not ok:
            c["invalid"] += 1
            why[j.split(":")[0]] += 1
            print(f"  invalid {cid}: {j}")
            continue
        c["valid"] += 1
        for k, v in j["rubric"].items():
            rub[k][v] += 1
        f = flags(rows[cid], j)
        fl["leak of label terms"] += bool(f["leak_label_terms"])
        fl["leak of other-class terms"] += bool(f["leak_other_terms"])
        fl["numbers not in source"] += bool(f["new_numbers"])
        fl["figure references"] += bool(f["figure_refs"])
        fl["blind diagnosis names our label"] += bool(f["matches_label"])
        fl["blind diagnosis names another class only"] += bool(f["names_other_class"] and not f["matches_label"])
    print("files:", dict(c))
    if why:
        print("invalid reasons:", dict(why))
    print("flags (cases):", dict(fl))
    for k, v in rub.items():
        print(f"rubric {k}:", dict(sorted(v.items(), key=str)))


def cmd_apply(a):
    rows = load_rows()
    n = 0
    with open(a.out, "w") as fh:
        for fn in sorted(os.listdir(a.dir)):
            cid = fn.rsplit(".", 1)[0]
            if not fn.endswith(".json") or cid not in rows:
                continue
            ok, j = validate(open(os.path.join(a.dir, fn)).read(), rows[cid])
            if not ok:
                continue
            fh.write(json.dumps({
                "case_id": cid, "present": rows[cid]["present"], "case_prompt": j["case_prompt"],
                "diagnostic_reasoning": j["diagnostic_reasoning"], "final_diagnosis": j["final_diagnosis"],
                "rubric": j["rubric"], "think": j.get("think", {}), "note": j.get("note", ""),
                "flags": flags(rows[cid], j), "prompt_version": PROMPT_VERSION}, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} rewritten cases to {a.out}")


RUNNER_MD = _MASK_RUNNER.replace("clinical text masking job", "clinical case rewriting job")


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build"); b.add_argument("--ids", required=True); b.add_argument("--out", required=True)
    c = sp.add_parser("check"); c.add_argument("dir")
    p = sp.add_parser("apply"); p.add_argument("dir"); p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"build": cmd_build, "check": cmd_check, "apply": cmd_apply}[a.cmd](a)


if __name__ == "__main__":
    main()
