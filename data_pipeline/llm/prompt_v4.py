#!/usr/bin/env python3
"""
Prompt v4: per-class verdicts against written class definitions.

    python3 llm/prompt_v4.py                 # token estimate + a rendered example
    python3 llm/prompt_v4.py --case <id>     # render a real case

What changed from v3 (llm/prompt.py, kept unchanged for the v3 results):
  - the agent sees the CANDIDATE class names and a definition of every class
  - one status per candidate class, instead of one verdict per case
  - term usage and class status are separate questions (principle 2)
  - role (main / secondary / incidental), patient species, text type
  - an open `diseases` list for diagnoses we did not search for
  - no confidence field
"""
import argparse, json, os, re

PROMPT_VERSION = "v4-2026-09-26"

SYSTEM = """You read one clinical case report and report which diseases this patient has.

A keyword filter picked this case because the case text, or its article's
title, MeSH terms or keywords, matched some search TERMS. From those terms it
guessed one or more CANDIDATE classes. The guess is often wrong. A matched
term may be a negative test, another person's illness, a past infection, a
related organism the class does not cover, or a word with another meaning.
Report what the CASE TEXT shows about THIS patient.


PRINCIPLES

1. Judge the patient from the case text. TITLE, MESH and KEYWORDS describe
   the article, which may be about a different patient or about a disease
   being the wrong answer ("X mimicking tuberculosis"). Use them only to know
   what to look for.

2. A term and a class are separate questions. A term can truly apply to this
   patient while its class is absent, because the class definition excludes
   that organism, strain, body site or state. A class can be present with no
   matched term at all, because the text calls it something else. Answer each
   question on its own. Never bend one answer to fit the other.

3. Decide each class by its definition below, including its exclusions, not
   by whether its word appears.

4. Present means the disease is active in this patient in this episode:
   diagnosed now, or being treated now. It is not present when the text shows
   only a past or healed infection, remnants (calcified or dead parasites),
   exposure or a positive screening test without disease, or a diagnosis that
   was considered and then excluded. Laboratory confirmation is not required:
   a diagnosis on clinical and imaging grounds followed by response to
   specific treatment is present.

5. Say what the case is about. A disease can be present while the report is
   about something else: a reaction to its treatment, a cancer in which the
   parasite was found, another illness. Record that in `role`. Do not change
   `status` because of it.

6. This case may contain diseases we did not search for. Besides the
   candidates, list every other diagnosis this patient has in this episode
   in `diseases`, whether or not it is in the class list.

7. Use `uncertain` when the text does not let you decide: the diagnosis is
   only suspected or suggested with nothing supporting it, the text stops
   before any diagnosis, or several patients are pooled and you cannot tell
   who had what. Do not use it only because the case is rare or complicated.

8. When no option fits, choose the closest and explain in `reason`, in your
   own words. We read every reason. An honest reason is worth more to us than
   a forced category.


EVIDENCE

Every `evidence` field is a list of sentences copied from CASE TEXT exactly,
character for character: no trimming, no joining with "...", no paraphrase.
Never quote TITLE, MESH or KEYWORDS. If nothing in the case text supports
your answer, give an empty list and explain in `reason`. Explanations go in
`reason`, never in `evidence`.


CLASS DEFINITIONS

Tuberculosis
  Active disease caused by Mycobacterium tuberculosis, in any organ,
  including drug-resistant TB, tuberculoma, Pott's disease, lupus vulgaris
  and other skin TB.
  Not: latent TB infection only; the BCG vaccine strain (M. bovis BCG);
  M. microti; nontuberculous mycobacteria (M. avium, M. abscessus, ...).

Echinococcosis
  Hydatid disease caused by Echinococcus: cystic (E. granulosus) or alveolar
  (E. multilocularis), in any organ.

Dengue
  Dengue virus infection of any severity, including severe dengue, dengue
  hemorrhagic fever and dengue shock syndrome.

Malaria
  Infection with a Plasmodium species that infects humans: P. falciparum,
  vivax, ovale, malariae or knowlesi.

Leishmaniasis
  Visceral (kala-azar), cutaneous, mucocutaneous or post-kala-azar dermal
  leishmaniasis.

Neurocysticercosis
  Taenia solium cysticercosis in the central nervous system: brain,
  ventricles, subarachnoid space or spinal cord.
  Not: cysticercosis only in skin, muscle, eye, mouth or other organs;
  intestinal tapeworm infection alone.

Leprosy
  Disease caused by M. leprae or M. lepromatosis, including leprosy
  reactions (type 1 reaction, erythema nodosum leprosum).

Leptospirosis
  Leptospira infection, including Weil's disease.

Schistosomiasis
  Infection with a Schistosoma species, in any organ.
  Not: cercarial dermatitis (swimmer's itch) from bird schistosomes.

Amebiasis
  Disease caused by Entamoeba histolytica: colitis, dysentery, liver
  abscess, ameboma, or another invasive site.
  Not: free-living amoebae (Naegleria, Acanthamoeba, Balamuthia);
  non-invasive Entamoeba species (E. dispar, E. coli).

Trypanosomiasis
  Chagas disease (Trypanosoma cruzi), or human African trypanosomiasis
  (sleeping sickness, T. brucei gambiense or rhodesiense).

Soil-Transmitted Helminths
  Infection with Ascaris lumbricoides, Trichuris trichiura, hookworm
  (Ancylostoma duodenale, Necator americanus) or Strongyloides stercoralis.
  Not: cutaneous larva migrans from animal hookworms; Toxocara, Enterobius
  and other worms.

Scrub Typhus
  Infection with Orientia tsutsugamushi.
  Not: murine or flea-borne typhus (Rickettsia typhi); epidemic typhus
  (R. prowazekii); spotted fevers and other rickettsial infections.

Talaromycosis
  Infection with Talaromyces (formerly Penicillium) marneffei.

Zika Virus
  Zika virus infection, including infection in pregnancy and congenital
  Zika syndrome.

Melioidosis
  Infection with Burkholderia pseudomallei, in any organ.
  Not: other Burkholderia species (B. cepacia, B. mallei).

Cholera
  Cholera: diarrhoeal disease caused by toxigenic Vibrio cholerae of
  serogroup O1 or O139.
  Not: infections by non-O1/non-O139 V. cholerae (bloodstream, wound, ear,
  urinary and other infections, or gastroenteritis from non-toxigenic
  strains); other Vibrio species.

Scabies
  Infestation with Sarcoptes scabiei, including crusted (Norwegian)
  scabies.

Viral Hemorrhagic Fevers
  Ebola, Marburg, Lassa or Crimean-Congo hemorrhagic fever.
  Not: other viral fevers (dengue, yellow fever, hantavirus), which are
  outside this class.

Paracoccidioidomycosis
  Infection with Paracoccidioides brasiliensis or P. lutzii.
  Not: lobomycosis (Lacazia loboi, Paracoccidioides ceti).

Mycetoma
  Eumycetoma (fungal) or actinomycetoma (bacterial): a chronic infection of
  skin and deeper tissue with swelling, draining sinuses and grains, most
  often of the foot (Madura foot).
  Not: "mycetoma" meaning a fungal ball (aspergilloma) in the lung or a
  sinus; other invasive fungal infections.

Foodborne Trematodes
  Infection with Fasciola, Clonorchis, Opisthorchis or Paragonimus.


FIELD GUIDE

patient.species       "human", "animal" or "unclear".

patient.text_type     "one_patient"      one patient, including how they
                                         presented or were diagnosed
                      "several_patients" more than one patient described
                                         together
                      "partial"          a piece of one patient's story
                                         (only follow-up, only surgery,
                                         only labs) without the diagnosis
                      "not_a_case"       no individual patient: review,
                                         study, protocol, background prose

terms[].usage         how this word is used in the case text
                      "present"      about this patient, in this episode
                                     (even if its class turns out absent -
                                     principle 2)
                      "absent"       tested negative, ruled out, or a
                                     differential that was dropped
                      "historical"   this patient, in the past
                      "other_person" a relative, donor, contact, cohort
                      "background"   general prose, not about a patient
                      "other"        none of these; say how in `reason`

diseases[]            one list with two kinds of entry:
                      - every CANDIDATE class, exactly once, in the order
                        given, with "candidate": true and a status of
                        "present", "absent" or "uncertain";
                      - every other diagnosis this patient has in this
                        episode, with "candidate": false and status
                        "present". Include diagnoses that shape this
                        episode, infectious or not; skip unrelated past
                        history.

diseases[].name       the diagnosis in your own words, e.g. "disseminated
                      talaromycosis" or "HIV infection". For an absent or
                      uncertain candidate, use the class name.

diseases[].class      one of the class names above if the diagnosis fits
                      that definition - even when it was not a candidate -
                      otherwise "other". A candidate entry always carries
                      its own class name.

diseases[].status     "present", "absent" or "uncertain", by the class
                      definition and principle 4.

diseases[].role       only when status is "present"; otherwise null
                      "main"         the report is mainly about this disease
                      "secondary"    active and managed in this episode, but
                                     the report is mainly about something
                                     else
                      "incidental"   found by chance and not managed as a
                                     problem in this episode


OUTPUT

Return one JSON object and nothing else:

{
  "patient": {
    "species": "human",
    "text_type": "one_patient",
    "reason": ""
  },
  "main_problem": "what this report is mainly about, in a few words",
  "terms": [
    {"term": "...", "usage": "present", "evidence": ["..."], "reason": ""}
  ],
  "diseases": [
    {"name": "...", "class": "...", "candidate": true,
     "status": "present", "role": "main",
     "evidence": ["..."], "reason": ""},
    {"name": "...", "class": "other", "candidate": false,
     "status": "present", "role": "secondary",
     "evidence": ["..."], "reason": ""}
  ],
  "note": ""
}

`reason` may be empty when the answer is plain, but give one sentence for
every absent or uncertain candidate. `note` is for anything the fields
above cannot hold; leave it empty otherwise."""

MAX_TERMS = 8
MAX_META  = 12

SPECIES    = {"human", "animal", "unclear"}
TEXT_TYPES = {"one_patient", "several_patients", "partial", "not_a_case"}
USAGES     = {"present", "absent", "historical", "other_person", "background",
              "other"}
STATUSES   = {"present", "absent", "uncertain"}
ROLES      = {"main", "secondary", "incidental"}
CLASSES    = re.findall(r"^([A-Z][A-Za-z\- ]+)\n  ",
                        SYSTEM.split("CLASS DEFINITIONS")[1].split("FIELD GUIDE")[0],
                        re.M)


def candidates(rec):
    """The classes the filter guessed - the ORIGINAL tags, before any clean-up."""
    return list((rec.get("diseases_tagged") or rec["diseases"]).keys())


def build_user(rec):
    """Render one cohort row as the case block."""
    parts = [
        f"CANDIDATES: {json.dumps(candidates(rec))}",
        f"TERMS: {json.dumps(sorted(set(rec['terms']))[:MAX_TERMS])}",
        f"TITLE: {rec.get('title', '')}",
        f"MESH: {'; '.join(rec.get('mesh', [])[:MAX_META])}",
        f"KEYWORDS: {'; '.join(rec.get('keywords', [])[:MAX_META])}",
    ]
    n = rec.get("n_cases", 1)
    if n > 1:
        parts.append(f"NOTE: this article contains {n} patient cases; "
                     f"the one below is case {rec.get('case_index', '?')}.")
    parts.append(f"\nCASE TEXT:\n{rec.get('case_text', '')}")
    return "\n".join(parts)


def valid_response(text, rec=None):
    """(True, parsed) or (False, reason).  With rec, also checks that every
    candidate appears exactly once, in order, and every term is answered."""
    try:
        j = json.loads(text) if isinstance(text, str) else text
    except Exception as e:
        return False, f"not JSON: {e}"
    if not isinstance(j, dict):
        return False, "not an object"
    p = j.get("patient") or {}
    if p.get("species") not in SPECIES:
        return False, f"bad species {p.get('species')!r}"
    if p.get("text_type") not in TEXT_TYPES:
        return False, f"bad text_type {p.get('text_type')!r}"
    for t in j.get("terms") or []:
        if t.get("usage") not in USAGES:
            return False, f"bad usage {t.get('usage')!r}"
        if not isinstance(t.get("evidence", []), list):
            return False, "term evidence is not a list"
    ds = j.get("diseases")
    if not isinstance(ds, list):
        return False, "diseases missing"
    for d in ds:
        if d.get("status") not in STATUSES:
            return False, f"bad status {d.get('status')!r}"
        if d.get("status") == "present" and d.get("role") not in ROLES:
            return False, f"bad role {d.get('role')!r}"
        if d.get("class") not in CLASSES and d.get("class") != "other":
            return False, f"bad class {d.get('class')!r}"
        if not isinstance(d.get("evidence", []), list):
            return False, "disease evidence is not a list"
        if not d.get("candidate") and d.get("status") != "present":
            return False, "non-candidate entry that is not present"
    if rec is not None:
        want = candidates(rec)
        got = [d.get("class") for d in ds if d.get("candidate")]
        if got != want:
            return False, f"candidates {got} != {want}"
        want_t = set(sorted(set(rec["terms"]))[:MAX_TERMS])
        got_t = {t.get("term") for t in j.get("terms") or []}
        if want_t - got_t:
            return False, f"terms not answered: {sorted(want_t - got_t)}"
    return True, j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("--cohort", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "partA_present.jsonl"))
    a = ap.parse_args()
    CH = 3.8
    print(f"PROMPT_VERSION {PROMPT_VERSION}   classes defined: {len(CLASSES)}")
    print(f"system prompt: {len(SYSTEM):,} chars  ~{len(SYSTEM)/CH:,.0f} tokens\n")
    for line in open(a.cohort):
        r = json.loads(line)
        if a.case is None or r["case_id"] == a.case:
            u = build_user(r)
            print(f"--- case block for {r['case_id']} ({len(u):,} chars) ---")
            print(u[:1500] + ("\n..." if len(u) > 1500 else ""))
            break


if __name__ == "__main__":
    main()
