#!/usr/bin/env python3
"""
Agent-assisted masking of test-case narratives.

The agent never rewrites text. It returns an edit list (delete sentence k, mask
an exact phrase in sentence k, tag clue sentences, judge usability); this
script checks the edits and applies them, so the output stays verbatim.

    python3 llm/mask_agent.py build  --ids ids.txt --out handoff_mask/pilot50
    python3 llm/mask_agent.py check  handoff_mask/pilot50/responses
    python3 llm/mask_agent.py apply  handoff_mask/pilot50/responses --out llm/masked_pilot50.jsonl

Two versions are written per case:
  text_a   deletions + masks applied, clue sentences kept
  text_b   as text_a, but clue sentences removed too
"""
import argparse, collections, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from mask_regex import mask_terms, sentences, MASK, WORD_RX  # noqa: E402

DATA = os.path.join(HERE, "partA_final.jsonl")
PROMPT_VERSION = "mask-v1-2026-09-29"
CLASSES = ["Amebiasis", "Cholera", "Dengue", "Echinococcosis", "Foodborne Trematodes", "Leishmaniasis",
           "Leprosy", "Leptospirosis", "Malaria", "Melioidosis", "Mycetoma", "Neurocysticercosis",
           "Paracoccidioidomycosis", "Scabies", "Schistosomiasis", "Scrub Typhus", "Soil-Transmitted Helminths",
           "Talaromycosis", "Trypanosomiasis", "Tuberculosis", "Viral Hemorrhagic Fevers", "Zika Virus"]
CLUE_KINDS = {"organism_seen", "pathognomonic_finding", "specific_treatment"}
USABLE = {"yes", "too_little_info", "not_a_patient_case", "fragment"}

SYSTEM = f"""You are preparing a clinical case report for a diagnosis test. A reader will later try to
diagnose the patient from the text. Your job is to hide the answer while keeping every clinical
clue a doctor would use to reach it.

You will get:
  HIDE        the diagnosis to hide (disease class and what the report says the patient had)
  SENTENCES   the case text, one numbered sentence per line. Obvious disease and organism names
              are already replaced by {MASK}. Sentences marked * were quoted by an earlier
              reviewer as stating the diagnosis - a hint, not an instruction.

You may only do three things. You never write or rephrase case text.

1. DELETE a whole sentence when its purpose is to state or confirm the diagnosis: the final
   diagnosis, "was diagnosed with ...", a positive test result that names or implies it.
   If such a sentence also carries a clinical clue that appears nowhere else (a symptom, an
   exam finding, the presentation), do not delete it - mask the revealing words instead.

2. MASK an exact phrase inside a sentence. The phrase is replaced by {MASK}. Mask anything that
   still names or directly gives away the hidden diagnosis:
     - disease names, synonyms, and abbreviations, including abbreviations the text never
       defines (e.g. "HD" for hydatid disease, "DF" for dengue fever, "DLL")
     - organisms at any level: genus, species, strain, serovar, lineage (e.g. "DTU II")
     - tests, reagents, primers, or media named after the organism or used only for it
     - "history of <the same disease>", "suspected <disease>", "endemic for <disease>"
   Also mask names of any of the other listed disease classes when they appear, so that the
   masking does not single out the answer. Keep masks as short as possible: mask the name,
   not the clinical finding around it.

3. TAG a sentence as a clue sentence when it describes the finding that confirms the diagnosis
   rather than a clinical clue: the organism seen on microscopy or grown in culture
   ("organism_seen"), a finding that is specific to this one disease ("pathognomonic_finding"),
   or a treatment regimen that identifies the disease ("specific_treatment"). Do not delete or
   mask these for being clues; just tag them. A sentence cannot be both deleted and tagged.

KEEP everything else untouched: symptoms, signs, examination, general laboratory values, imaging
descriptions, travel, occupation, animal, food and water exposure, and non-specific treatment.

Then judge the result:
  usable            yes | too_little_info | not_a_patient_case | fragment
                    too_little_info  - after your edits nothing specific enough is left to reason from
                    not_a_patient_case - a review, a method description, or research summary
                    fragment         - a short piece of a multi-patient report that depends on text
                                       outside it
  remaining_clues   one sentence: which clinical clues left in the text point to the diagnosis

Return ONLY this JSON object, no prose, no markdown fences:
{{
  "case_id": "<as given>",
  "delete":  [{{"s": <sentence number>, "reason": "<short>"}}],
  "mask":    [{{"s": <sentence number>, "text": "<exact phrase copied from that sentence>", "reason": "<short>"}}],
  "clue_sentences": [{{"s": <sentence number>, "kind": "organism_seen|pathognomonic_finding|specific_treatment", "reason": "<short>"}}],
  "usable": "yes|too_little_info|not_a_patient_case|fragment",
  "remaining_clues": "<one sentence>",
  "note": "<optional, empty if nothing>"
}}

Rules for "mask": "text" must be copied character for character from sentence s as shown
(including any {MASK} already there if you include it). Do not mask a whole sentence - delete it
instead. Lists may be empty.

The disease classes in this dataset: {", ".join(CLASSES)}."""


def load_rows():
    return {json.loads(l)["case_id"]: json.loads(l) for l in open(DATA)}


def case_sentences(rec):
    """numbered sentences, regex pre-masked, and the indices v4 quoted as evidence"""
    quotes = [q for c in rec["present"] for q in rec["candidates"][c]["evidence"]]
    frags = [p.strip(" .,;") for q in quotes for p in re.split(r"\.\.\.|…|\[\.\.\.\]", re.sub(r"\s+", " ", q))
             if len(p.strip()) > 15]
    raw = sentences(rec["case_text"])
    marked = {i for i, s in enumerate(raw, 1) if any(f in s or s.strip(" .") in f for f in frags)}
    return [mask_terms(s) for s in raw], marked


def hide_line(rec):
    parts = ", ".join(rec["present"]) or "(none recorded)"
    return f"{parts} - {rec.get('main_problem') or ''}".strip(" -")


def build_user(rec):
    sents, marked = case_sentences(rec)
    lines = [f"{'*' if i in marked else ' '}S{i}: {s}" for i, s in enumerate(sents, 1)]
    return f"case_id: {rec['case_id']}\nHIDE: {hide_line(rec)}\n\nSENTENCES:\n" + "\n".join(lines)


def validate(text, rec):
    try:
        j = json.loads(text) if isinstance(text, str) else text
    except Exception as e:
        return False, f"not JSON: {e}"
    sents, _ = case_sentences(rec)
    n = len(sents)
    if j.get("case_id") != rec["case_id"]:
        return False, "case_id mismatch"
    for k in ("delete", "mask", "clue_sentences"):
        if not isinstance(j.get(k), list):
            return False, f"{k} not a list"
    dels = {d.get("s") for d in j["delete"]}
    clues = {c.get("s") for c in j["clue_sentences"]}
    for s in dels | clues | {m.get("s") for m in j["mask"]}:
        if not isinstance(s, int) or not 1 <= s <= n:
            return False, f"sentence number out of range: {s}"
    if dels & clues:
        return False, f"sentence both deleted and tagged: {sorted(dels & clues)}"
    for m in j["mask"]:
        t = m.get("text") or ""
        if not t or t not in sents[m["s"] - 1]:
            return False, f"mask text not found verbatim in S{m['s']}: {t!r}"
        if t.strip() == sents[m["s"] - 1].strip():
            return False, f"mask covers whole S{m['s']} (should be a delete)"
    for c in j["clue_sentences"]:
        if c.get("kind") not in CLUE_KINDS:
            return False, f"bad clue kind: {c.get('kind')}"
    if j.get("usable") not in USABLE:
        return False, f"bad usable: {j.get('usable')}"
    return True, j


def apply_edits(rec, j):
    sents, _ = case_sentences(rec)
    sents = list(sents)
    for m in sorted(j["mask"], key=lambda m: -len(m["text"])):
        sents[m["s"] - 1] = sents[m["s"] - 1].replace(m["text"], MASK)
    tidy = lambda t: re.sub(r"\[MASK\](?:[\s-]+\[MASK\])+", MASK, t)
    dels = {d["s"] for d in j["delete"]}
    clues = {c["s"] for c in j["clue_sentences"]}
    a = tidy(" ".join(s for i, s in enumerate(sents, 1) if i not in dels))
    b = tidy(" ".join(s for i, s in enumerate(sents, 1) if i not in dels | clues))
    return a, b


def leftover_terms(rec, text):
    """own-case terms (from v4) that still appear - a sanity check on the agent"""
    own = {t["term"].lower() for t in rec["terms"]} | {c.lower() for c in rec["present"]}
    hits = {t for t in own if re.search(r"\b" + re.escape(t) + r"\b", text, re.I)}
    return sorted(hits | {m.group(0).lower() for m in WORD_RX.finditer(text)})


RUNNER_MD = open(os.path.join(HERE, "make_handoff_v4.py")).read().split('RUNNER_MD = """', 1)[1].split('"""', 1)[0]
RUNNER_MD = RUNNER_MD.replace("clinical NLP annotation job", "clinical text masking job").replace(
    "  - Do not answer any case yourself, and do not edit a model's answer.",
    "  - Do not answer any case yourself, and do not edit a model's answer.\n"
    "  - Only write responses for case_ids that exist in `cases/`. Never invent a case_id,\n"
    "    and never write the same answer under two names.")


def cmd_build(a):
    rows = load_rows()
    ids = [l.strip() for l in open(a.ids) if l.strip()]
    missing = [i for i in ids if i not in rows]
    if missing:
        sys.exit(f"unknown case ids: {missing[:5]}")
    os.makedirs(os.path.join(a.out, "cases"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "responses"), exist_ok=True)
    if os.listdir(os.path.join(a.out, "responses")):
        sys.exit("responses/ is not empty - refusing to rebuild over finished work")
    with open(os.path.join(a.out, "manifest.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "case_id", "present"])
        for k, cid in enumerate(ids, 1):
            fn = f"{k:04d}_{cid}.txt"
            open(os.path.join(a.out, "cases", fn), "w").write(
                f"=== SYSTEM PROMPT ({PROMPT_VERSION}) ===\n{SYSTEM}\n\n=== CASE ===\n{build_user(rows[cid])}\n")
            w.writerow([fn, cid, ";".join(rows[cid]["present"])])
    nch = -(-len(ids) // 10)
    open(os.path.join(a.out, "RUNNER.md"), "w").write(RUNNER_MD.format(
        k=os.path.basename(a.out).replace("package-", ""), ncases=len(ids), chunk=10, conc=30, wait=45,
        nchunks=nch, nwaves=-(-nch // 30), ver=PROMPT_VERSION))
    print(f"wrote {len(ids)} case files to {a.out}")


def cmd_check(a):
    rows = load_rows()
    c, why, use, kinds, left = collections.Counter(), collections.Counter(), collections.Counter(), \
        collections.Counter(), 0
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
            continue
        c["valid"] += 1
        use[j["usable"]] += 1
        kinds.update(x["kind"] for x in j["clue_sentences"])
        ta, _ = apply_edits(rows[cid], j)
        left += bool(leftover_terms(rows[cid], ta))
    print("files:", dict(c))
    if why:
        print("invalid reasons:", dict(why))
    print("usable:", dict(use))
    print("clue sentence kinds:", dict(kinds))
    print("valid cases with a leftover term in text_a:", left)


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
            ta, tb = apply_edits(rows[cid], j)
            fh.write(json.dumps({
                "case_id": cid, "present": rows[cid]["present"], "usable": j["usable"],
                "text_a": ta, "text_b": tb, "remaining_clues": j.get("remaining_clues", ""),
                "leftover_terms": leftover_terms(rows[cid], ta), "edits": j,
                "prompt_version": PROMPT_VERSION}, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} masked cases to {a.out}")


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
