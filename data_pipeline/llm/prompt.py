#!/usr/bin/env python3
"""
The verification prompt.  Single source of truth - both the sequential runner
and the batch submitter import SYSTEM and build_user() from here.

    python3 llm/prompt.py                 # token estimate + a rendered example
    python3 llm/prompt.py --case <id>     # render a real case from the cohort

VERSION history lives in PROMPT_VERSION.  Bump it whenever SYSTEM changes, and
record it in every output row, so a mixed-prompt run is never silently merged.
"""
import argparse, json, os, sys

PROMPT_VERSION = "v3-2026-09-22"

SYSTEM = """You verify disease labels on clinical case reports.

A keyword filter tagged this case with one or more candidate diseases. The tag
came from the article's title, MeSH terms, keywords, or the case text itself.
Your job is to decide whether that tag is correct FOR THIS PATIENT.

You are not diagnosing. You are checking a claim.

THE TEST
Does the CASE TEXT show that this patient, in this episode, has the disease?
Everything below is an application of that one question.


STEP 1 - classify each matched TERM

For every term in TERMS, decide how it is used in this case:

  present       this patient has this condition in the current episode
  absent        tested for and negative, or explicitly excluded
  historical    this patient had it in the past; it is not the current illness
  differential  it was considered, then disproved or abandoned
  other_person  it refers to someone else - a relative, a donor, a study cohort
  background    it appears only in general prose about the disease, not about
                this patient
  other         none of the above fits; describe the usage in `evidence`

Quote the sentence that justifies your choice, verbatim, in `evidence`.
If no such sentence exists, leave `evidence` empty.


STEP 2 - one verdict for the whole case

This is about the case, not about any single term. A case can have several
terms with different assertions.

  present    the case text shows this patient has at least one of the candidate
             diseases - as the diagnosis of this episode, or as an active
             comorbidity being treated.

             Counts (examples, not a complete list):
             - named as the diagnosis with a confirmatory result reported
             - not named, but the text reports findings that establish it
               (e.g. caseating granulomas with positive AFB culture)
             - a second, active infection being treated alongside the main
               problem

             Does not count:
             - the disease appears only in TITLE or MESH
             - it was one item in a differential that resolved to something else
             - the patient is at risk of it, or was screened for it

  absent     the case text shows this patient does not have any candidate
             disease in this episode.

             Counts (examples, not a complete list):
             - tested for and negative
             - had it in the past, treated, not the current illness
             - it belongs to a relative, donor, or study cohort
             - it was a differential that was disproved
             - the text is general prose about the disease, not a patient
             - the patient's real diagnosis is something else and the term
               appeared incidentally - a risk factor, a test panel, a
               comparison, an introductory sentence

  uncertain  the case text does not let you commit either way.

             Common reasons (examples, not a complete list):
             - no diagnosis stated, findings fit several candidates
             - a candidate disease is named as the diagnosis but nothing in
               the text supports it beyond the naming - no test, no imaging,
               no treatment response
             - text is truncated, background prose, a protocol, or a cohort
             - TITLE names the disease and the case text neither supports nor
               contradicts it

             If none of these fit but you still cannot commit, answer
             uncertain and describe the reason in your own words.

Microbiological confirmation is NOT required. Many tropical diseases are
routinely diagnosed clinically; culture-negative extrapulmonary tuberculosis is
the norm, not the exception. A diagnosis made on clinical and imaging grounds
AND followed by a documented response to specific therapy counts as present,
not uncertain.

Do NOT answer uncertain merely because the case is complicated or rare. If the
text states the diagnosis and reports something that supports it, commit.


TWO TRAPS - read before deciding

1. TITLE and MESH are the authors' framing of the ARTICLE, not evidence about
   this patient. They are the claim you are checking, not proof of it. Papers
   are frequently written about a disease being the WRONG answer - "X mimicking
   tuberculosis", "a rare cause misdiagnosed as malaria". The title names the
   disease precisely because it was excluded.

2. One article can contain several patients. TITLE and MESH belong to the
   article and may describe a different patient than the one below.

Decide from CASE TEXT. Use TITLE, MESH and KEYWORDS only to know what to look
for.


Return JSON only, no prose outside it:

{
  "verdicts": [
    {"term": "...", "assertion": "...", "evidence": "..."}
  ],
  "primary_diagnosis": "this patient's actual diagnosis in this episode, in
                        your own words, or 'not stated'",
  "verdict": "present" | "absent" | "uncertain",
  "uncertainty_reason": "one sentence; omit unless verdict is uncertain",
  "confidence": 0.0,
  "note": "anything the categories above do not capture, or that made this
           decision hard. Empty if nothing. Do not repeat reasoning."
}"""

MAX_TERMS = 8
MAX_META  = 12


def build_user(rec):
    """Render one cohort row (from cohort_partA.jsonl) as the user message."""
    parts = [
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


# --- schema check -----------------------------------------------------------

ASSERTIONS = {"present", "absent", "historical", "differential",
              "other_person", "background", "other"}
VERDICTS   = {"present", "absent", "uncertain"}


def valid_response(text):
    """(ok, parsed_or_reason).  Used to decide whether a row needs a retry."""
    try:
        j = json.loads(text)
    except Exception as e:
        return False, f"not JSON: {e}"
    if j.get("verdict") not in VERDICTS:
        return False, f"bad verdict: {j.get('verdict')!r}"
    v = j.get("verdicts")
    if not isinstance(v, list):
        return False, "verdicts missing"
    for item in v:
        if item.get("assertion") not in ASSERTIONS:
            return False, f"bad assertion: {item.get('assertion')!r}"
    return True, j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", help="case_id to render from cohort_partA.jsonl")
    ap.add_argument("--cohort", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cohort_partA.jsonl"))
    a = ap.parse_args()

    CH = 3.8  # chars per token, clinical English
    print(f"PROMPT_VERSION {PROMPT_VERSION}")
    print(f"system prompt: {len(SYSTEM):,} chars  ~{len(SYSTEM)/CH:,.0f} tokens\n")

    rec = None
    if os.path.exists(a.cohort):
        for line in open(a.cohort):
            r = json.loads(line)
            if a.case is None or r["case_id"] == a.case:
                rec = r
                break
    if rec is None:
        rec = {"case_id": "EXAMPLE", "terms": ["tuberculosis"],
               "title": "Congenital tuberculosis complicated by interstitial "
                        "pulmonary emphysema",
               "mesh": ["Tuberculosis, Pulmonary", "Infant, Newborn"],
               "keywords": ["congenital tuberculosis", "neonate"],
               "n_cases": 4, "case_index": 3,
               "case_text": "<full case text goes here>"}
        print("(cohort not built yet - showing a synthetic example)\n")

    u = build_user(rec)
    print(f"--- user message for {rec['case_id']} "
          f"({len(u):,} chars ~{len(u)/CH:,.0f} tokens) ---")
    print(u[:1500] + ("\n..." if len(u) > 1500 else ""))
    print(f"\nestimated input  ~{(len(SYSTEM)+len(u))/CH:,.0f} tokens/case")


if __name__ == "__main__":
    main()
