#!/usr/bin/env python3
"""
Build the 22-disease "Part A" cohort.

Each disease carries its own inclusion rule (the 3-way hybrid):

    S1   = article title + MeSH + author keywords + this case's image captions
    S2   = this case's case_text
    Both = S1 AND S2        Setup1 = S1 only        Setup3 = S1 OR S2

    python3 llm/build_partA.py            ->  llm/cohort_partA.jsonl
    python3 llm/build_partA.py --stats    ->  per-disease breakdown, no write

Expected: ~2,437 unique cases / ~2,100 articles / ~1,885 with images.

MATCHING.  Text is normalised so every run of non-alphanumeric characters
becomes one space, then a term matches as the substring " term ".  That is
equivalent to \\b...\\b on BOTH sides.  Without it "hepatitis a" matches
"hepatitis and" and you inherit a few hundred junk cases.
"""
import argparse, collections, json, os, re, sys

import pyarrow.parquet as pq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_DATA = os.path.join(ROOT, "Archive-001")
if not os.path.exists(DEFAULT_DATA):
    multicare = os.path.join(os.path.dirname(ROOT), "Official_MultiCaRe", "whole_multicare_dataset")
    if os.path.exists(multicare):
        DEFAULT_DATA = multicare
DATA = os.environ.get("MULTICARE_DATA", DEFAULT_DATA)
OUT  = os.path.join(HERE, "cohort_partA.jsonl")

# rule -> "both" | "s1" | "s3"
# Terms are the 22-disease specification.  Two leishmaniasis terms
# ("leishman-donovan bodies", "ld bodies") are additions to that list; every
# count quoted for this cohort was measured with them included.
TAXONOMY = {
    "Tuberculosis": ("both", [
        "tuberculosis", "mycobacterium tuberculosis", "m. tuberculosis",
        "tuberculoma", "pott disease", "pott spine", "scrofula",
        "tuberculous meningitis"]),
    "Echinococcosis": ("both", [
        "echinococcosis", "echinococcus", "echinococcus granulosus",
        "echinococcus multilocularis", "hydatid cyst", "hydatid disease",
        "hydatid sand", "water lily sign"]),
    "Dengue": ("both", [
        "dengue", "dengue fever", "severe dengue", "dengue hemorrhagic fever",
        "breakbone fever", "dengue shock syndrome", "denv"]),
    "Malaria": ("both", [
        "malaria", "plasmodium", "falciparum", "plasmodium vivax",
        "plasmodium ovale", "plasmodium malariae", "plasmodium knowlesi",
        "blackwater fever", "cerebral malaria", "quartan malaria",
        "tertian malaria"]),

    "Leishmaniasis": ("s1", [
        "visceral leishmaniasis", "kala-azar", "kala azar", "dumdum fever",
        "leishmania donovani", "leishmania infantum", "cutaneous leishmaniasis",
        "mucocutaneous leishmaniasis", "leishmania major", "leishmania tropica",
        "leishmania braziliensis", "oriental sore", "chiclero ulcer",
        "delhi boil", "espundia", "aleppo boil",
        "leishman-donovan bodies", "ld bodies"]),
    "Neurocysticercosis": ("s1", [
        "neurocysticercosis", "cysticercosis", "taenia solium", "cysticercus",
        "cysticerci"]),
    "Leprosy": ("s1", [
        "leprosy", "hansen disease", "hansen's disease", "mycobacterium leprae",
        "lepromatous leprosy", "tuberculoid leprosy"]),
    "Leptospirosis": ("s1", [
        "leptospirosis", "leptospira", "weil disease", "weil's disease"]),
    "Schistosomiasis": ("s1", [
        "schistosomiasis", "schistosoma", "schistosoma mansoni",
        "schistosoma haematobium", "schistosoma japonicum", "bilharzia",
        "bilharziasis", "katayama fever", "symmers pipestem"]),
    "Amebiasis": ("s1", [
        "amebiasis", "amoebiasis", "entamoeba histolytica",
        "amoebic liver abscess", "amebic liver abscess", "amoebic colitis",
        "amebic dysentery"]),
    "Trypanosomiasis": ("s1", [
        "chagas disease", "american trypanosomiasis", "trypanosoma cruzi",
        "chagasic cardiomyopathy", "romana sign", "chagasic megaesophagus",
        "chagas megacolon", "sleeping sickness", "african trypanosomiasis",
        "trypanosoma brucei", "trypanosoma gambiense",
        "trypanosoma rhodesiense", "winterbottom sign"]),

    "Soil-Transmitted Helminths": ("s3", [
        "ascariasis", "ascaris lumbricoides", "hookworm disease",
        "ancylostoma duodenale", "necator americanus",
        "strongyloides stercoralis", "strongyloidiasis", "trichuris trichiura",
        "whipworm"]),
    "Scrub Typhus": ("s3", [
        "scrub typhus", "orientia tsutsugamushi", "tsutsugamushi disease",
        "murine typhus", "epidemic typhus", "rickettsia typhi",
        "rickettsia prowazekii"]),
    "Talaromycosis": ("s3", [
        "talaromycosis", "talaromyces marneffei", "penicillium marneffei"]),
    "Zika Virus": ("s3", ["zika", "zikv", "congenital zika"]),
    "Melioidosis": ("s3", [
        "melioidosis", "burkholderia pseudomallei", "whitmore disease"]),
    "Cholera": ("s3", ["cholera", "vibrio cholerae"]),
    "Scabies": ("s3", [
        "scabies", "sarcoptes scabiei", "crusted scabies", "norwegian scabies"]),
    "Viral Hemorrhagic Fevers": ("s3", [
        "ebola", "marburg virus", "lassa fever", "lassa virus",
        "crimean-congo hemorrhagic fever", "cchf"]),
    "Paracoccidioidomycosis": ("s3", [
        "paracoccidioidomycosis", "paracoccidioides",
        "south american blastomycosis"]),
    # Safeguard: "mycetoma" also appears inside "aspergilloma"-style reports as
    # a homonym.  The LLM pass is what catches those; no string rule can.
    "Mycetoma": ("s3", [
        "mycetoma", "madura foot", "madurella mycetomatis", "actinomycetoma",
        "eumycetoma"]),
    "Foodborne Trematodes": ("s3", [
        "fascioliasis", "fasciola hepatica", "clonorchiasis",
        "clonorchis sinensis", "paragonimiasis", "paragonimus westermani",
        "opisthorchiasis"]),
}

_WS = re.compile(r"[^a-z0-9]+")


def norm(s):
    """Lowercase, collapse non-alphanumerics to single spaces, pad with spaces."""
    return " " + _WS.sub(" ", str(s).lower()).strip() + " "


def hits(text, terms):
    """Terms present in already-normalised `text`, in their original spelling."""
    return [t for t, p in terms if p in text]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA,
                    help="path to dataset directory containing MultiCaRe parquet files")
    ap.add_argument("--stats", action="store_true",
                    help="print the per-disease breakdown and exit without writing")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    data_dir = a.data

    # pre-normalise every term once
    pats = {d: (rule, [(t, norm(t)) for t in ts])
            for d, (rule, ts) in TAXONOMY.items()}

    print(f"loading {data_dir} ...", file=sys.stderr)
    md = {r["article_id"]: (r["article_metadata"] or {})
          for r in pq.read_table(f"{data_dir}/metadata.parquet").to_pylist()}

    n_img = collections.Counter()
    caps  = collections.defaultdict(list)
    for r in pq.read_table(f"{data_dir}/case_images.parquet").to_pylist():
        for entry in (r["case_images"] or []):
            cid = entry.get("case_id")
            for im in (entry.get("case_image_list") or []):
                n_img[cid] += 1
                caps[cid].append(im.get("caption") or "")

    seen = kept = with_img = tot_img = 0
    per_disease = collections.Counter()
    per_stratum = collections.Counter()
    arts = set()
    fh = None if a.stats else open(a.out, "w")

    for row in pq.read_table(f"{data_dir}/cases.parquet").to_pylist():
        aid = row["article_id"]
        m = md.get(aid, {}) or {}
        title    = str(m.get("title") or "")
        mesh     = [str(x) for x in (m.get("mesh_terms") or [])]
        keywords = [str(x) for x in (m.get("keywords") or [])]
        meta_txt = norm(" ".join([title, " ".join(keywords), " ".join(mesh)]))

        cases = row["cases"] or []
        for idx, c in enumerate(cases, 1):
            seen += 1
            cid  = c["case_id"]
            body = norm(str(c.get("case_text") or ""))
            cap  = norm(" ".join(caps.get(cid, [])))

            diseases, matched = {}, []
            for d, (rule, terms) in pats.items():
                h1 = hits(meta_txt, terms) + hits(cap, terms)
                h2 = hits(body, terms)
                in1, in2 = bool(h1), bool(h2)
                ok = (in1 and in2) if rule == "both" else \
                     (in1 if rule == "s1" else (in1 or in2))
                if not ok:
                    continue
                stratum = "both" if (in1 and in2) else ("only_S1" if in1 else "only_S2")
                diseases[d] = stratum
                matched += h1 + h2
                per_disease[d] += 1
                per_stratum[stratum] += 1

            if not diseases:
                continue
            kept += 1
            arts.add(aid)
            ni = n_img.get(cid, 0)
            with_img += ni > 0
            tot_img += ni
            if fh:
                fh.write(json.dumps({
                    "case_id":    cid,
                    "article_id": aid,
                    "diseases":   diseases,               # name -> stratum
                    "terms":      sorted(set(matched)),
                    "title":      title,
                    "mesh":       mesh,
                    "keywords":   keywords,
                    "n_cases":    len(cases),             # cases in this article
                    "case_index": idx,
                    "n_images":   ni,
                    "case_text":  str(c.get("case_text") or ""),
                }, ensure_ascii=False) + "\n")
    if fh:
        fh.close()

    print(f"\nsearched {seen:,} cases")
    print(f"cohort   {kept:,} cases across {len(arts):,} articles")
    print(f"images   {with_img:,} cases carry images, {tot_img:,} images total")
    print(f"\n{'disease':30}{'rule':>7}{'cases':>8}")
    for d, n in per_disease.most_common():
        print(f"{d:30}{TAXONOMY[d][0]:>7}{n:>8}")
    print(f"\n{'stratum':30}{'':>7}{'labels':>8}")
    for s in ("both", "only_S1", "only_S2"):
        print(f"{s:30}{'':>7}{per_stratum[s]:>8}")
    print(f"{'TOTAL LABELS':30}{'':>7}{sum(per_stratum.values()):>8}")
    if not a.stats:
        print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
