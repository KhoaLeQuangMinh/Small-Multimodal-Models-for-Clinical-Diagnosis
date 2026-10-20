#!/usr/bin/env python3
"""
Confirmation Strength Score (CSS): how strongly the case text proves each label.

Each (case, class) label gets the tier of the strongest evidence anywhere in the
case text, with the sentence that shows it:

    3  organism shown      the pathogen, its parts or its genetic material seen / grown / detected
    2  indirect, specific  antibodies, typical tissue reaction, or a finding specific to the disease
    1  clinical only       symptoms, exposure, non-specific tests, response to treatment
    0  stated only         the diagnosis is named but no basis is given

The agent names a test type and a tier; every test type belongs to exactly one tier,
so the two must agree.  The quote must appear word for word in the cited sentence.

    python3 llm/css_agent.py build --ids ids.txt --out handoff_css/pilot50
    python3 llm/css_agent.py check handoff_css/pilot50/responses
    python3 llm/css_agent.py apply handoff_css/pilot50/responses --out llm/css_pilot50.jsonl
"""
import argparse, collections, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mask_regex import sentences  # noqa: E402
from mask_agent import RUNNER_MD as _MASK_RUNNER  # noqa: E402

DATA = os.path.join(HERE, "partA_final.jsonl")
PROMPT_VERSION = "css-v2-2026-10-06"

TEST_TIER = {
    "microscopy": 3, "culture": 3, "molecular": 3, "antigen": 3, "histopathology_organism": 3,
    "organism_seen_gross": 3,
    "serology": 2, "histopathology_tissue": 2, "specific_finding": 2,
    "nonspecific_test": 1, "imaging_nonspecific": 1, "clinical": 1, "treatment_response": 1,
    "none": 0,
}

SYSTEM = """You are grading how strongly a clinical case report proves a diagnosis. You do not decide
whether the diagnosis is right - it is given. You decide what kind of evidence for it the case
text reports.

You will get:
  GRADE       the disease class(es) to grade for this case
  SENTENCES   the case text, one numbered sentence per line

For EACH class in GRADE, find the STRONGEST evidence anywhere in the case text and report
its tier, its test type, and the one sentence that shows it.

TIERS AND TEST TYPES  (each test type belongs to exactly one tier)

  Tier 3 - the organism itself, its parts or its genetic material, in this patient's sample
    microscopy               smear, wet mount, KOH, Gram/Ziehl-Neelsen/Giemsa stain, dermoscopy
                             that shows the organism itself
    culture                  organism grown and identified (including VITEK, MALDI-TOF on the isolate)
    molecular                PCR, GeneXpert, line probe assay, mNGS, sequencing detecting the organism
    antigen                  a test for the organism's antigen (dengue NS1, malaria RDT, cholera
                             rapid test, schistosome CCA, Talaromyces Mp1p, Entamoeba antigen)
    histopathology_organism  tissue or cytology showing the organism (AFB in tissue, amastigotes,
                             yeasts, eggs, larvae, protoscolices, hooklets, laminated membrane,
                             fungal grains with hyphae, viral antigen on immunostaining)
    organism_seen_gross      a worm, larva, mite or fluke seen by eye, at endoscopy or surgery,
                             or expelled by the patient
  Tier 2 - indirect but specific to this disease
    serology                 antibodies (IgM/IgG ELISA, IFA, MAT, Weil-Felix, rK39, DAT, IHA,
                             immunodiffusion, EITB, PRNT, anti-PGL-1)
    histopathology_tissue    a tissue reaction typical of the disease without the organism seen
                             (caseating granuloma without AFB, granulomas along nerves)
    specific_finding         an imaging, surgical, endoscopic or clinical finding that occurs in
                             almost no other disease (see the class notes)
  Tier 1 - clinical only
    nonspecific_test         a test that is positive in many conditions or shows only exposure
                             (eosinophilia, ADA, TST, IGRA, leishmanin skin test, Gram stain
                             without identification)
    imaging_nonspecific      imaging that fits but is not specific (cavity, ring-enhancing lesion,
                             liver abscess, miliary pattern)
    clinical                 symptoms, signs, exposure, epidemiology, a typical clinical picture
    treatment_response       improvement on disease-specific or empirical treatment
  Tier 0 - stated only
    none                     the diagnosis is named but the text gives no basis for it at all

GENERAL RULES
  - Only evidence about THIS patient counts. Not relatives, not other patients in the report,
    not literature or discussion of other cases.
  - A negative, pending, planned or not-performed test never counts.
  - If the text names the test but not the details ("confirmed by PCR", "biopsy showed
    amastigotes"), grade by the test named. "The diagnosis was confirmed" with no test
    named is tier 0 unless other evidence exists.
  - A biopsy or histology that "confirmed" or "was positive for" the disease, without
    describing the organism, is histopathology_tissue (tier 2). Use histopathology_organism
    only when the text says the organism (or its eggs, larvae, parts) was seen.
  - A test from an earlier episode of the same disease counts if the text reports its result.
  - If several sentences show the same top tier, cite the clearest one.
  - Grade what the text reports, even if the evidence seems weak or the label seems doubtful.

CLASS NOTES  (typical evidence per tier; anything that fits the definitions above also counts)
  Tuberculosis   3: AFB in sputum/fluid/tissue, M. tuberculosis (complex) culture, Xpert/PCR/LPA/mNGS
                 2: caseating or necrotizing granuloma without organism
                 1: TST/IGRA, ADA, cavity or miliary pattern, empirical anti-TB response
  Leprosy        3: AFB on slit-skin smear or in biopsy (Fite), M. leprae PCR
                 2: typical histology without bacilli (granulomas around nerves, foamy macrophages,
                    grenz zone), anti-PGL-1 serology
                 1: anaesthetic patch, thickened nerve (WHO cardinal signs)
  Dengue         3: NS1, RT-PCR, virus isolation      2: IgM, IgG seroconversion
                 1: fever + thrombocytopenia, plasma leakage, tourniquet test
  Malaria        3: Plasmodium on thick/thin smear, RDT, PCR     1: clinical, empirical antimalarials
  Leishmaniasis  3: amastigotes / LD bodies in smear, aspirate or biopsy, culture, PCR
                 2: rK39, DAT, IFAT      1: leishmanin skin test, clinical, treatment response
  Echinococcosis 3: protoscolices, hooklets or laminated/germinal membrane on microscopy or
                    histology, PCR
                 2: serology; daughter cysts, water-lily sign, hydatid sand, typical WHO CE stage
                    on imaging; daughter cysts or membranes seen at surgery
                 1: a simple cyst on imaging, treatment response
  Neurocysticercosis 3: parasite or scolex on histology
                 2: cyst with a visible scolex on CT/MRI, racemose cysts, EITB or other serology
                 1: calcifications or ring-enhancing lesions without scolex, response to albendazole
  Cholera        3: V. cholerae culture, PCR, rapid antigen test   1: profuse rice-water diarrhoea
  Scrub Typhus   3: O. tsutsugamushi PCR, culture     2: IgM ELISA, IFA, Weil-Felix OX-K
                 1: eschar, fever, response to doxycycline
  Leptospirosis  3: PCR, culture    2: MAT, IgM ELISA    1: clinical, exposure
  Melioidosis    3: B. pseudomallei culture or PCR    2: IHA serology
                 1: clinical; bipolar Gram-negative rods without identification
  Talaromycosis  3: culture (red pigment, dimorphic), yeasts with transverse septa on smear or
                    histology, PCR/mNGS, Mp1p antigen     1: umbilicated papules in HIV, clinical
  Paracoccidioidomycosis 3: multiple-budding ("pilot's wheel") yeasts on direct exam or
                    histology, culture, PCR      2: serology (immunodiffusion, CIE)
  Mycetoma       3: grains with hyphae or filaments on microscopy/histology, culture or
                    sequencing identifying the agent
                 2: grains seen grossly in discharge, "dot-in-circle" sign on MRI
                 1: swelling with sinuses, clinical
  Scabies        3: mite, eggs or scybala on microscopy of scrapings; mite seen on dermoscopy
                    (delta-wing / triangle sign)
                 2: burrows      1: itch pattern, affected contacts, response to permethrin
  Schistosomiasis 3: eggs in stool, urine or tissue, PCR, CCA/CAA antigen
                 2: serology; periportal ("pipe-stem") fibrosis      1: exposure, eosinophilia
  Soil-Transmitted Helminths 3: eggs, larvae or worms in stool, sputum, BAL, tissue, or a worm
                    seen at endoscopy or expelled; PCR
                 2: Strongyloides serology      1: eosinophilia, response to anthelmintics
  Foodborne Trematodes 3: eggs in stool, sputum or bile, an adult fluke recovered, PCR
                 2: serology; tunnel / track-like lesions on liver imaging
                 1: eosinophilia, raw food exposure
  Trypanosomiasis 3: trypomastigotes in blood, CSF or chancre aspirate, amastigotes in tissue,
                    PCR, culture or xenodiagnosis
                 2: serology (Chagas ELISA/IFA, CATT)    1: chancre, Romana sign, cardiomyopathy + exposure
  Zika Virus     3: RT-PCR (blood, urine, amniotic fluid, tissue), viral antigen in tissue
                 2: IgM, PRNT     1: clinical, epidemiology, congenital findings without testing
  Viral Hemorrhagic Fevers 3: RT-PCR, antigen, virus isolation    2: IgM, IgG seroconversion
                 1: clinical + exposure
  Amebiasis      3: trophozoites (or E. histolytica/dispar cysts) on microscopy, E. histolytica
                    antigen, PCR
                 2: serology; "anchovy paste" aspirate     1: liver abscess with metronidazole response

Return ONLY this JSON object, no prose, no markdown fences:
{
  "case_id": "<as given>",
  "labels": [
    {"class": "<a class from GRADE>",
     "tier": <0-3>,
     "test": "<one test type from the list>",
     "s": <sentence number, or null for tier 0>,
     "quote": "<the part of sentence s that states the positive result, copied character for character; empty for tier 0>",
     "reason": "<one short sentence>"}
  ],
  "note": "<optional, empty if nothing>"
}

One entry per class in GRADE - no more, no fewer. "tier" must be the tier of "test"."""


def load_rows():
    return {json.loads(l)["case_id"]: json.loads(l) for l in open(DATA)}


norm = lambda s: re.sub(r"\s+", " ", s).strip()


def build_user(rec):
    lines = [f"S{i}: {s}" for i, s in enumerate(sentences(rec["case_text"]), 1)]
    return f"case_id: {rec['case_id']}\nGRADE: {'; '.join(rec['present'])}\n\nSENTENCES:\n" + "\n".join(lines)


def validate(text, rec):
    try:
        j = json.loads(text) if isinstance(text, str) else text
    except Exception as e:
        return False, f"not JSON: {e}"
    if j.get("case_id") != rec["case_id"]:
        return False, "case_id mismatch"
    labs = j.get("labels")
    if not isinstance(labs, list):
        return False, "labels not a list"
    got = [l.get("class") for l in labs]
    if sorted(got) != sorted(rec["present"]):
        return False, f"classes {got} != {rec['present']}"
    sents = sentences(rec["case_text"])
    for l in labs:
        t, test = l.get("tier"), l.get("test")
        if test not in TEST_TIER:
            return False, f"bad test type: {test}"
        if t != TEST_TIER[test]:
            return False, f"tier/test mismatch: {test} is tier {TEST_TIER[test]}, got {t}"
        if t == 0:
            continue
        s = l.get("s")
        if not isinstance(s, int) or not 1 <= s <= len(sents):
            return False, f"sentence number out of range: {s}"
        q = norm(l.get("quote") or "")
        if len(q) < 8 or q not in norm(sents[s - 1]):
            return False, f"quote not found verbatim in S{s}"
    return True, j


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
    c, why, tiers = collections.Counter(), collections.Counter(), collections.Counter()
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
        tiers.update(l["tier"] for l in j["labels"])
    print("files:", dict(c))
    if why:
        print("invalid reasons:", dict(why))
    print("labels by tier:", dict(sorted(tiers.items(), reverse=True)))


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
            for l in j["labels"]:
                fh.write(json.dumps({"case_id": cid, "class": l["class"], "tier": l["tier"], "test": l["test"],
                                     "s": l.get("s"), "quote": l.get("quote", ""), "reason": l.get("reason", ""),
                                     "prompt_version": PROMPT_VERSION}, ensure_ascii=False) + "\n")
                n += 1
    print(f"wrote {n} graded labels to {a.out}")


RUNNER_MD = _MASK_RUNNER.replace("clinical text masking job", "clinical evidence grading job")


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
