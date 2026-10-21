"""
Regex pre-mask for test-case narratives (step 1 of masking; the agent pass in
mask_agent.py does the rest).

1. remove the sentences that hold the v4 evidence quotes for the present classes
   (except the first sentence of the case, which is kept and masked instead,
   because it is usually the presentation)
2. mask, for ALL 22 classes: disease names, synonyms, abbreviations, organisms,
   disease-specific tests and drugs; abbreviations the text defines for a masked
   term, e.g. "hydatid disease (HD)", are masked too
"""
import re

MASK = "[MASK]"

# words matched case-insensitively, as whole words; a trailing * means "any ending"
TERMS = {
    "Tuberculosis": ["tuberculosis", "tuberculous", "tubercular", "tuberculoma*", "antitubercul*",
                     "anti-tubercul*", "koch's", "pott's", "pott disease", "scrofula", "lupus vulgaris",
                     "isoniazid", "rifampicin", "rifampin", "rifapentine", "pyrazinamide", "ethambutol",
                     "genexpert", "xpert", "quantiferon", "t-spot*", "tuberculin", "mantoux", "igra"],
    "Leprosy": ["lepros*", "leprous", "lepromatous", "lepromatosis", "leprae", "leprosum", "hansen's disease",
                "hansen disease", "hansen's", "antileprosy", "anti-leprosy", "dapsone", "clofazimine",
                "ml flow", "tuberculoid", "lucio"],
    "Dengue": ["dengue", "breakbone"],
    "Malaria": ["malaria*", "antimalarial*", "anti-malarial*", "plasmodi*", "falciparum", "vivax", "ovale",
                "knowlesi", "malariae", "artesunate", "artemether", "artemisinin*", "lumefantrine", "chloroquine",
                "hydroxychloroquine", "primaquine", "tafenoquine", "quinine", "mefloquine", "atovaquone",
                "proguanil", "piperaquine", "pfhrp*", "hrp-2", "hrp2", "binaxnow"],
    "Leishmaniasis": ["leishmania*", "leishmanial", "kala-azar", "kala azar", "leishman-donovan", "leishman",
                      "rk39", "rk-39", "antimonial*", "antimony", "stibogluconate", "meglumine", "glucantime",
                      "pentostam", "miltefosine", "impavido", "paromomycin", "donovani", "infantum",
                      "braziliensis", "amazonensis", "guyanensis", "panamensis"],
    "Echinococcosis": ["echinococc*", "hydatid*", "hydatidosis", "granulosus", "multilocularis", "scolicid*",
                       "casoni"],
    "Neurocysticercosis": ["neurocysticerc*", "cysticerc*", "taenia*", "taeniasis", "solium"],
    "Cholera": ["cholera*", "choleragen", "vibrio", "el tor", "inaba", "ogawa", "o139"],
    "Scrub Typhus": ["scrub typhus", "scrub", "tsutsugamushi", "orientia", "rickettsi*", "weil-felix",
                     "weil felix", "typhus"],
    "Leptospirosis": ["leptospir*", "leptospira", "interrogans", "weil's disease", "weil disease",
                      "microscopic agglutination test", "bataviae", "icterohaemorrhagiae", "serovar", "serogroup"],
    "Melioidosis": ["melioid*", "pseudomallei", "burkholderia", "whitmore*"],
    "Talaromycosis": ["talaromyc*", "marneffei", "penicillios*", "penicilliosis"],
    "Paracoccidioidomycosis": ["paracoccidioid*", "paracoccidoid*", "brasiliensis", "lutzii"],
    "Mycetoma": ["mycetoma*", "eumycetoma*", "actinomycetoma*", "maduromycosis", "madura", "madurella",
                 "mycetomatis", "actinomadura", "madurae", "eumycete*"],
    "Scabies": ["scabies", "scabiei", "sarcoptes", "sarcoptic", "permethrin", "benzyl benzoate", "ascabiol",
                "crotamiton", "lindane", "norwegian"],
    "Schistosomiasis": ["schistosom*", "bilharzi*", "mansoni", "haematobium", "hematobium", "japonicum",
                        "katayama"],
    "Soil-Transmitted Helminths": ["strongyloid*", "stercoralis", "hookworm*", "ancylostom*", "necator",
                                   "ascari*", "lumbricoides", "trichur*", "trichiura", "whipworm*", "roundworm*",
                                   "larva currens", "larva migrans"],
    "Foodborne Trematodes": ["paragonim*", "westermani", "kellicotti", "fasciol*", "hepatica", "gigantica",
                             "clonorch*", "opisthorch*", "viverrini", "fluke*", "triclabendazole"],
    "Trypanosomiasis": ["trypanosom*", "cruzi", "brucei", "gambiense", "rhodesiense", "chagas*", "chagasic",
                        "chagoma", "sleeping sickness", "benznidazole", "nifurtimox", "suramin", "melarsoprol",
                        "fexinidazole", "eflornithine", "tesa-blot", "tesa blot"],
    "Zika Virus": ["zika"],
    "Viral Hemorrhagic Fevers": ["ebola*", "marburg", "lassa", "filovir*", "arenavir*", "crimean-congo",
                                 "hantavir*", "yellow fever", "rift valley", "machupo", "junin", "hantaan",
                                 "haemorrhagic fever*", "hemorrhagic fever*", "filo"],
    "Amebiasis": ["amoeb*", "ameb*", "entamoeba", "histolytica", "diloxanide", "tiliquinol", "tilbroquinol",
                  "iodoquinol", "dispar"],
    # broad antiparasitic drugs: they reveal a helminth diagnosis, so they are masked too
    "_antiparasitic": ["albendazole", "mebendazole", "praziquantel", "ivermectin", "niclosamide",
                       "anthelmint*", "antihelmint*", "anti-helmint*", "vermifug*"],
}

# short abbreviations, matched case-sensitively as whole words
ABBREV = ["TB", "MTB", "M.tb", "ATT", "HRZE", "MDT", "DF", "DHF", "DSS", "DENV", "NS1", "VL", "CL", "MCL",
          "PKDL", "NCC", "PCM", "EBOV", "DLL", "EHF", "CCHF", "HFRS", "ZIKV", "CZS", "ALA", "MAT", "CLM", "SHS",
          "HRE"]

GENUS_INITIAL = ["tuberculosis", "leprae", "falciparum", "vivax", "ovale", "malariae", "knowlesi", "histolytica",
                 "granulosus", "multilocularis", "solium", "cholerae", "tsutsugamushi", "interrogans",
                 "pseudomallei", "marneffei", "brasiliensis", "lutzii", "mycetomatis", "madurae", "scabiei",
                 "mansoni", "haematobium", "japonicum", "stercoralis", "duodenale", "americanus", "lumbricoides",
                 "trichiura", "westermani", "kellicotti", "hepatica", "gigantica", "sinensis", "viverrini",
                 "cruzi", "brucei", "donovani", "infantum", "braziliensis", "major", "tropica", "mexicana",
                 "amazonensis", "guyanensis", "panamensis", "lepromatosis"]


def _word_rx(w):
    if w.endswith("*"):
        return re.escape(w[:-1]) + r"[\w'-]*"
    return re.escape(w)


ALL_WORDS = sorted({w for ws in TERMS.values() for w in ws}, key=len, reverse=True)
WORD_RX = re.compile(r"(?<![\w-])(?:" + "|".join(_word_rx(w) for w in ALL_WORDS) + r")(?![\w])", re.I)
SPECIES_RX = re.compile(r"\b[A-Z]\.\s?(?:" + "|".join(GENUS_INITIAL) + r")\b")
ABBREV_RX = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(a) for a in ABBREV) + r")(?![A-Za-z0-9])")
DEF_RX = re.compile(r"\(([A-Z][A-Za-z0-9-]{1,7})\)")


def defined_abbrevs(text):
    """abbreviations the text introduces right after a masked term, e.g. 'hydatid disease (HD)'"""
    out = set()
    for m in DEF_RX.finditer(text):
        # only the few words directly before the parenthesis count
        tail = re.split(r"[,;:.()]", text[max(0, m.start() - 60):m.start()])[-1]
        tail = " ".join(tail.split()[-4:])
        if WORD_RX.search(tail) or SPECIES_RX.search(tail):
            out.add(m.group(1))
    return out


def mask_terms(text):
    extra = defined_abbrevs(text)
    text = SPECIES_RX.sub(MASK, text)
    text = WORD_RX.sub(MASK, text)
    text = ABBREV_RX.sub(MASK, text)
    if extra:
        text = re.sub(r"(?<![A-Za-z0-9])(?:" + "|".join(map(re.escape, extra)) + r")(?![A-Za-z0-9])", MASK, text)
    text = re.sub(r"\[MASK\](?:[\s-]+\[MASK\])+", MASK, text)
    return text


norm = lambda s: re.sub(r"\s+", " ", s).strip()


def sentences(t):
    t = re.sub(r"(?<=[a-z0-9)]\.)(?=[A-Z][a-z]{2,})", " ", norm(t))   # "positive.Chest" -> 2 sentences
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\[])", t) if s]


def frags(q):
    return [p.strip(" .,;") for p in re.split(r"\.\.\.|…|\[\.\.\.\]", norm(q)) if len(p.strip()) > 15]


def mask_case(rec):
    quotes = [q for c in rec["present"] for q in rec["candidates"][c]["evidence"]]
    fr = [f for q in quotes for f in frags(q)]
    kept, removed = [], []
    for i, s in enumerate(sentences(rec["case_text"])):
        hit = any(f in s or s.strip(" .") in f for f in fr)
        (removed if hit and i > 0 else kept).append(s)
    return mask_terms(" ".join(kept)), removed
