from __future__ import annotations
import os
import re
import json
import argparse
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List, Set, Tuple, Any

# ==============================================================================
# VOCABULARY FILTER CONFIGURATION & SUPPLEMENTAL / EXCLUSION KEYWORDS (100% GROUNDED)
# ==============================================================================

# 1. List of 16 standard medical vocabularies in master_umls_dictionary.csv
CLEAN_VOCABULARIES: Set[str] = {
    "MSH", "SNOMEDCT_US", "NCI", "ICD10CM", "ICD10", "ICD10AM", "ICD9CM",
    "ORPHANET", "MDR", "CHV", "MEDLINEPLUS", "CSP", "SNMI", "RCD", "RCDAE", "MEDCIN"
}

# 2. Single words / phrases with stemmer errors, merged sibling CUIs, or semantic drift to block
BLACKLIST_EXACT_TERMS: Set[str] = {
    # [TIER 1] CHV stemmer error (Rows 3344, 3345) for Yaws -> collides with head yaw axis 'yaw'
    "yaw", "yawing",
    # [TIER 1] ICD-10 B47 parent code conflation (21 rows in DOID:13078) -> collides with aspergilloma & actinomycetoma
    "mycetoma", "mycetomas", "mycetomata",
    # [TIER 1] MeSH D003551 error (Rows 2924-2958) conflating Coenurosis (T. multiceps) into Cysticercosis (T. solium)
    "coenurosis", "coenuroses",
    "coenuri infection", "coenuri infections", "coenurus infection", "coenurus infections",
    # [TIER 1] MDR/SNOMED error (Rows 2874, 2884) attaching generic 'bilharzia' to child Urinary schistosomiasis
    "bilharzia infection", "cystitis with bilharziasis",
    # [TIER 1] ICD10CM error (Row 2250) abbreviated 'I leprosy' -> absorbs 'group i leprosy' & false positives 'Table I, leprosy'
    "i leprosy",
    # [TIER 1] ORPHANET error (Row 585) storing truncated species epithet 'Medinensis' without genus Dracunculus
    "medinensis",
    # [TIER 1] Generic symptoms/physicochemical terms (Rows 1161, 2627, 2628) non-specific to individual diseases
    "hydrophobia", "remittent fever", "marsh fever",
    # [TIER 1] Veterinary diseases (bovine Babesiosis / equine infectious anemia) in CHV & RCD (Rows 743-794)
    "mud fever", "swamp fever", "red water fever",
    # [TIER 1] Prevent Yaws (T. pallidum pertenue) from matching syphilis (T. pallidum)
    "treponema pallidum", "t. pallidum",
    "treponema pallidum subsp", "t. pallidum subsp",
    "treponema pallidum ssp", "t. pallidum ssp",
    "treponema pallidum subspecies", "t. pallidum subspecies",
    # [TIER 1] Prevent Trachoma from matching urogenital Chlamydia trachomatis / LGV
    "chlamydia trachomatis", "c. trachomatis",
    # [TIER 2] Veterinary hepatitis term prone to false positives (Rows 176, 179) & OCR typo 'pain' -> 'pian' (Row 3296)
    "enzootic hepatitis", "pian", "buba", "bouba",
    # [TIER 2] Generic larval tapeworm phrases in SNOMED (Rows 2929-2960), preventing confusion with Echinococcus/Sparganum
    "infection by tapeworm larvae", "infections by tapeworm larvae", "infection caused by tapeworm larvae",
}

# 4. Supplemental standard keywords & causative pathogen names (Grounded in doid.obo & ICD-10)
SUPPLEMENTAL_SEEDS: Dict[str, List[str]] = {
    # [TIER 1] Resolve 7 DOID codes with overwritten CUIs or missing official names in master_umls_dictionary.csv
    "DOID:1395": [
        "schistosomiasis", "schistosomiases", "schistosomal", "bilharziasis",
        "bilharzia", "katayama fever", "snail fever", "schistosoma infection"
    ],
    "DOID:1495": [
        "cystic echinococcosis", "cystic hydatid disease", "cystic hydatidosis",
        "echinococcus granulosus"
    ],
    "DOID:13078": [
        "eumycotic mycetoma", "eumycetoma", "fungal mycetoma",
        "maduromycosis", "maduramycosis", "madura foot"
    ],
    "DOID:10079": [
        "cysticercosis", "neurocysticercosis", "cysticercus", "cysticerci"
    ],
    "DOID:1394": [
        "urinary schistosomiasis", "urogenital schistosomiasis",
        "schistosoma haematobium", "schistosoma hematobium"
    ],
    "DOID:0050597": [
        "intestinal schistosomiasis", "schistosoma mansoni",
        "schistosoma japonicum", "schistosoma mekongi", "schistosoma intercalatum"
    ],
    "DOID:0050596": [
        "taeniasis", "taenia saginata", "taenia solium", "taenia asiatica", "pork tapeworm"
    ],
    # [TIER 2] Add causative pathogen names strictly aligned with 'def:' annotations in doid.obo
    "DOID:0050192": ["nipah virus", "nipah encephalitis"],
    "DOID:0050256": ["angiostrongyliasis", "angiostrongylosis", "angiostrongylus cantonensis", "angiostrongylus costaricensis"],
    "DOID:10844":   ["japanese encephalitis", "japanese encephalitis virus"],
    "DOID:10955":   ["strongyloidiasis", "strongyloides stercoralis"],
    "DOID:11265":   ["trachoma", "trachomatous"],
    "DOID:12841":   ["ancylostomiasis", "ancylostoma duodenale", "ancylostoma ceylanicum"],
    "DOID:2790":    ["necatoriasis", "necator americanus"],
    "DOID:3983":    ["oesophagostomiasis", "esophagostomiasis", "oesophagostomum bifurcum"],
    "DOID:456":     ["ascariasis", "ascaris lumbricoides"],
    "DOID:885":     ["fascioliasis", "fasciola hepatica", "fasciola gigantica"],
    "DOID:888":     ["fasciolopsiasis", "fasciolopsis buski"],
    "DOID:9181":    ["amebiasis", "amoebiasis", "entamoeba histolytica", "amebic liver abscess", "amoebic liver abscess", "amebic dysentery", "amoebic dysentery"],
    "DOID:13767":   ["clonorchiasis", "clonorchis sinensis"],
    "DOID:13768":   ["opisthorchiasis", "opisthorchis viverrini", "opisthorchis felineus"],
    "DOID:14418":   ["dracunculiasis", "dracunculus medinensis", "guinea worm"],
    "DOID:14484":   ["sporotrichosis", "sporothrix schenckii", "sporothrix brasiliensis"],
    "DOID:1562":    ["chromoblastomycosis", "chromomycosis", "fonsecaea pedrosoi", "cladophialophora carrionii"],
    "DOID:12662":   ["paracoccidioidomycosis", "paracoccidioides brasiliensis", "paracoccidioides lutzii"],
    "DOID:2297":    ["leptospirosis", "leptospira interrogans", "leptospira borgpetersenii", "leptospira kirschneri"],
    "DOID:10371":   ["yaws", "framboesia", "frambesia", "treponema pallidum pertenue", "treponema pertenue"],
    "DOID:1081":    ["mansonelliasis", "mansonella perstans", "mansonella ozzardi", "mansonella streptocerca"],
    "DOID:12211":   ["filarial elephantiasis", "lymphatic filariasis", "wuchereria bancrofti", "brugia malayi", "brugia timori"],
    "DOID:9146":    ["visceral leishmaniasis", "kala-azar", "kala azar", "leishmania donovani", "leishmania infantum", "leishmania chagasi"],
    "DOID:9111":    ["cutaneous leishmaniasis", "oriental sore", "aleppo boil", "delhi boil", "baghdad boil", "leishmania major", "leishmania tropica", "leishmania mexicana"],
    "DOID:9155":    ["mucocutaneous leishmaniasis", "espundia", "leishmania braziliensis"],
    "DOID:10112":   ["sleeping sickness", "human african trypanosomiasis", "trypanosoma brucei gambiense", "trypanosoma brucei rhodesiense"],
    "DOID:12140":   ["chagas disease", "trypanosoma cruzi"],
    "DOID:14067":   ["plasmodium falciparum"],
    "DOID:12978":   ["plasmodium vivax"],
    "DOID:14324":   ["plasmodium malariae"],
    "DOID:12919":   ["plasmodium ovale"],
    "DOID:8295":    ["scabies", "sarcoptes scabiei", "scabietic"],
}

# 5. List of 38 pathogen genera across the 74 diseases for automatic "G. species" abbreviation generation
#    ('chlamydia' removed so DOID:11265 Trachoma cannot expand urogenital C. trachomatis from UMLS strings)
KNOWN_PATHOGEN_GENERA: Set[str] = {
    "mycobacterium", "vibrio", "burkholderia", "pseudomonas", "salmonella",
    "orientia", "rickettsia", "leptospira", "treponema",
    "paracoccidioides", "sporothrix", "fonsecaea", "cladophialophora",
    "plasmodium", "leishmania", "trypanosoma", "entamoeba",
    "schistosoma", "echinococcus", "taenia", "wuchereria", "brugia",
    "onchocerca", "mansonella", "dracunculus", "clonorchis", "opisthorchis",
    "fasciola", "fasciolopsis", "paragonimus", "ascaris", "trichuris",
    "ancylostoma", "necator", "angiostrongylus", "oesophagostomum",
    "strongyloides", "sarcoptes"
}

# 6. Exclusion gates for omitted sibling diseases present in doid.obo but
#    NOT included in the 74 disease target list, preventing them from falling into Parent_Unspecified
OMITTED_SIBLING_EXCLUSION_REGEXES: Dict[str, re.Pattern] = {
    # Exclude DOID:12148 (alveolar echinococcosis) & DOID:0050218 (polycystic echinococcosis)
    "DOID:1496": re.compile(
        r"(?i)\b(?:alveolar\s+echinococcos(?:is|es)|alveolar\s+hydatid|echinococcus\s+multilocularis|"
        r"e\.?\s*multilocularis|polycystic\s+echinococcos(?:is|es)|polycystic\s+hydatid|"
        r"echinococcus\s+vogeli|e\.?\s*vogeli|echinococcus\s+oligarthrus|e\.?\s*oligarthrus)\b"
    ),
    # Exclude DOID:1082 (dirofilariasis), DOID:14422 (dipetalonemiasis), DOID:4514 (setariasis)
    "DOID:1080": re.compile(
        r"(?i)\b(?:dirofilarias(?:is|es)|dirofilaria\s+immitis|d\.?\s*immitis|"
        r"dirofilaria\s+repens|d\.?\s*repens|dipetalonemias(?:is|es)|setarias(?:is|es))\b"
    ),
    # Exclude DOID:8889 (cercarial dermatitis / swimmer's itch caused by avian schistosome Trichobilharzia)
    "DOID:1395": re.compile(
        r"(?i)\b(?:cercarial\s+dermatitis|swimmer'?s\s+itch|trichobilharzia)\b"
    ),
    # Exclude DOID:0050143 (asymptomatic dengue)
    "DOID:12205": re.compile(
        r"(?i)\b(?:asymptomatic\s+dengue)\b"
    ),
    # Exclude atypical veterinary Trypanosomes (T. evansi / surra, T. lewisi, T. congolense)
    "DOID:10113": re.compile(
        r"(?i)\b(?:trypanosoma\s+evansi|t\.?\s*evansi|trypanosoma\s+lewisi|t\.?\s*lewisi|trypanosoma\s+congolense)\b"
    ),
}

# ==============================================================================
# TARGET DIAGNOSIS LABEL RESOLUTION CONFIGURATION (RULE-BASED)
# ==============================================================================

# 7 Parent hierarchies that roll up to the PARENT disease name as official label (label_disease_name)
PARENT_LABEL_HIERARCHIES: Set[str] = {
    "DOID:12205",  # dengue disease (aggregates DHF and DSS)
    "DOID:1024",   # leprosy (aggregates Ridley-Jopling spectrum subtypes)
    # malaria (aggregates Plasmodium species and pernicious complications)
    "DOID:12365",
    "DOID:1395",   # schistosomiasis (aggregates organ localization subtypes)
    # echinococcosis (aggregates cystic echinococcosis / hydatidosis)
    "DOID:1496",
    "DOID:10371",  # yaws (aggregates early yaws and late yaws stages)
    # scabies (aggregates classical scabies and norwegian/crusted scabies)
    "DOID:8295",
}

# 4 Parent hierarchies that retain distinct CHILD disease names as official label (label_disease_name)
CHILD_LABEL_HIERARCHIES: Set[str] = {
    "DOID:10113",    # trypanosomiasis -> distinguish 'Chagas disease' vs 'sleeping sickness'
    # taeniasis -> distinguish 'taeniasis' (intestinal tapeworm) vs 'cysticercosis' (larval tissue/CNS)
    "DOID:0050596",
    "DOID:1080",     # filariasis -> distinguish 'filarial elephantiasis', 'onchocerciasis', 'loiasis', 'mansonelliasis'
    "DOID:9065",     # leishmaniasis -> distinguish 'visceral', 'cutaneous', 'mucocutaneous leishmaniasis'
}


def resolve_final_diagnosis_label(
    folder_type: str,
    parent_doid: str,
    parent_name: str,
    assigned_doid: str,
    assigned_disease_name: str,
    routing_level: str,
) -> Tuple[str, str, str]:
    """
    Rule-based mapping deciding 'label_doid', 'label_disease_name', and 'label_resolution_rule'
    for the clinical diagnosis task.
    """
    # 1. Standalone diseases (33) -> Use assigned disease directly
    if folder_type == "Standalone":
        return assigned_doid, assigned_disease_name, "Standalone_Direct"

    # 2. Hierarchies designated for parent label rollup (7 parents) -> Always roll up to parent
    if parent_doid in PARENT_LABEL_HIERARCHIES:
        return parent_doid, parent_name, "Rollup_To_Parent"

    # 3. Hierarchies designated for child label distinction (4 parents):
    if parent_doid in CHILD_LABEL_HIERARCHIES:
        if routing_level == "Specific_Child":
            return assigned_doid, assigned_disease_name, "Use_Specific_Child"
        # For DOID:0050596 (taeniasis): non-cysticercosis cases represent adult intestinal tapeworm infection
        if parent_doid == "DOID:0050596":
            return parent_doid, parent_name, "Use_Adult_Taeniasis_Parent"
        # For trypanosomiasis, filariasis, and leishmaniasis matching only generic parent terms:
        return parent_doid, parent_name, "Parent_Unspecified_Needs_Subtype"

    return assigned_doid, assigned_disease_name, "Default"


# ==============================================================================
# STEP 1: CLEANING, PATHOGEN ABBREVIATION EXPANSION & PARENT-CHILD KEYWORD SUBTRACTION
# ==============================================================================

def clean_single_umls_string(raw_name: Any, term_type: str = "") -> str | None:
    """
    Clean an individual raw UMLS string from master_umls_dictionary.csv:
    - Retain inverted phrase structures (both unpunctuated from CHV/MDR and comma-separated from MeSH)
      to maximize recall aligning with clinical note patterns and mesh_terms structures.
    """
    if not isinstance(raw_name, str):
        return None
    # Drop multi-fragment machine permutations (Term Type PM)
    if term_type == "PM":
        return None

    s = raw_name.strip()

    # 1. Only drop strings containing semicolon ';' (index phrase truncations from ICPC2)
    if ";" in s:
        return None

    # 2. Drop strings containing administrative classification tags (unspecified, NOS, any site, other specified, NEC)
    #    Executed BEFORE comma processing to drop terms like "Cholera, unspecified" immediately
    if re.search(
        r"\b(?:unspecified|not otherwise specified|nos|any site|other specified|nec)\b",
        s,
        flags=re.IGNORECASE,
    ):
        return None

    # 3. Block short uppercase acronyms <= 5 characters (e.g., DF, YF, EHF, JE, VL, CL, DSS)
    if re.match(r"^[A-Z0-9]{1,5}$", s):
        return None

    # 4. Strip acronym code prefixes with whitespace around hyphen (e.g., "JE - Japanese encephalitis")
    s = re.sub(r"^\[[A-Z0-9]+\]\s*", "", s)
    s = re.sub(r"^[A-Z0-9]{1,6}\s+-\s+", "", s)

    # 5. Strip trailing bracketed classification qualifiers like (disorder), (diagnosis), [group B]...
    s = re.sub(
        r"\s*[\(\[](?:disorder|diagnosis|finding|disease|organism|infection|syndrome|"
        r"physical finding|group\s+[a-z0-9]+|type\s+[a-z0-9]+|active stage|"
        r"benign tertian|malignant tertian|kala-azar|leprosy|guinea worm|tuberculoid)[\)\]]\s*$",
        "",
        s,
        flags=re.IGNORECASE,
    )

    # 6. If brackets/parentheses remain inside string or trailing ' - ' -> drop
    if any(ch in s for ch in "[]()") or " - " in s:
        return None

    # 7. Convert comma ',' in medical inverted phrases (e.g., "Malaria, Falciparum") into whitespace
    #    (When compiled into regex with [\s,\-:]+, it matches both punctuated and unpunctuated variants!)
    s = s.replace(",", " ")
    s = re.sub(r"\s+", " ", s.lower().strip())

    # 8. Validate against BLACKLIST_EXACT_TERMS only (INVERTED_PHRASES_TO_DROP is completely removed)
    if s in BLACKLIST_EXACT_TERMS:
        return None

    if len(s) <= 2:
        return None

    return s


def expand_pathogen_abbreviations(terms: Set[str]) -> Set[str]:
    """
    Automatically extract Latin binomial and trinomial species names (Genus species [subsp. subspec])
    from phrases such as 'vibrio cholerae infection' -> add 'vibrio cholerae' and 'v. cholerae'.
    Safely handles 'subsp.' / 'ssp.' / 'subspecies' qualifiers and prevents collapsing
    'treponema pallidum [subsp.] pertenue' into the syphilis organism 'treponema pallidum'.
    """
    expanded = set(terms)
    genera_pattern = "|".join(sorted(KNOWN_PATHOGEN_GENERA))
    binomial_regex = re.compile(
        rf"\b({genera_pattern})\s+([a-z]{{4,}})"
        rf"(?:\s+(?:(?:subsp|ssp|subspecies)\.?\s+)?([a-z]{{4,}}))?\b"
    )

    non_species_words = {
        "infection", "infections", "disease", "diseases", "fever", "fevers",
        "syndrome", "virus", "viral", "gastroenteritis", "encephalitis", "malaria",
        "infestation", "infestations", "ulcer", "ulcers", "cystitis", "granuloma",
        "granulomas", "subsp", "ssp", "subspecies"
    }

    for term in list(terms):
        for match in binomial_regex.finditer(term):
            genus, species, subspec = (
                match.group(1),
                match.group(2),
                match.group(3),
            )
            if species in non_species_words:
                continue
            if subspec and subspec not in non_species_words:
                expanded.add(f"{genus} {species} {subspec}")
                expanded.add(f"{genus[0]}. {species} {subspec}")
                expanded.add(f"{genus[0]}. {species[0]}. {subspec}")
                expanded.add(f"{genus} {species} subsp. {subspec}")
                expanded.add(f"{genus[0]}. {species} subsp. {subspec}")
                expanded.add(f"{genus} {species} ssp. {subspec}")
                expanded.add(f"{genus[0]}. {species} ssp. {subspec}")
            else:
                # Never collapse Treponema pallidum into bare binomial (syphilis organism)
                if genus == "treponema" and species == "pallidum":
                    continue
                expanded.add(f"{genus} {species}")
                expanded.add(f"{genus[0]}. {species}")

    return expanded - BLACKLIST_EXACT_TERMS


def _is_contaminated_pathogen_term(term: str) -> bool:
    """
    Post-expansion guard ensuring:
    1. No term in BLACKLIST_EXACT_TERMS survives.
    2. No bare 'treponema pallidum' or 't. pallidum' phrase (without 'pertenue') survives.
    3. No 'chlamydia trachomatis' or 'c. trachomatis' phrase survives.
    """
    if term in BLACKLIST_EXACT_TERMS:
        return True
    if ("treponema pallidum" in term or "t. pallidum" in term) and "pertenue" not in term:
        return True
    if "chlamydia trachomatis" in term or "c. trachomatis" in term:
        return True
    return False


# ==============================================================================
# STEP 2: SAFE REGEX COMPILATION (NEGATIVE PREFIX BOUNDARIES + UK/US NORMALIZATION)
# ==============================================================================

def term_to_regex_fragment(term: str) -> str:
    """
    Convert a clean keyword into a regex pattern supporting:
    - UK/US spelling variants (ae / oe / e) for Greek-Latin roots
    - Flexible whitespace or hyphens between words
    - Optional period after genus/subspecies abbreviation (e.g., 'p. falciparum', 'subsp. pertenue')
    """
    tokens = term.split(" ")
    processed_tokens = []

    for tok in tokens:
        if re.match(r"^(?:[a-z]|subsp|ssp)\.$", tok):
            prefix = tok[:-1]
            processed_tokens.append(rf"{prefix}\.?\s*")
            continue

        escaped = re.escape(tok)
        escaped = re.sub(r"(?:ae|oe)", "(?:ae|oe|e)", escaped)
        escaped = re.sub(r"\bameb", "(?:ae|oe|e)m(?:ae|oe|e)b", escaped)
        escaped = re.sub(r"hemorrhag", "h(?:ae|e)morrhag", escaped)
        escaped = re.sub(r"hemoglobin", "h(?:ae|e)moglobin", escaped)
        escaped = re.sub(r"hemoptys", "h(?:ae|e)moptys", escaped)
        escaped = re.sub(r"hematob", "h(?:ae|e)matob", escaped)

        processed_tokens.append(escaped)

    pattern = ""
    for i, ptok in enumerate(processed_tokens):
        if i == 0:
            pattern += ptok
        else:
            if processed_tokens[i - 1].endswith(r"\.?\s*"):
                pattern += ptok
            else:
                # Allow whitespace, comma, colon, or hyphen between words
                pattern += r"[\s,\-:]+" + ptok

    return pattern


def prune_subsumed_phrases(terms: Set[str]) -> List[str]:
    """
    Prune redundant phrases via Substring Subsumption:
    If a shorter term like 'cholera' is present, automatically drop 'asiatic cholera', 'epidemic cholera'.
    """
    sorted_terms = sorted(terms, key=lambda x: (len(x), x))
    kept: List[str] = []
    kept_regexes: List[re.Pattern] = []

    for candidate in sorted_terms:
        if any(r.search(candidate) for r in kept_regexes):
            continue
        kept.append(candidate)
        frag = term_to_regex_fragment(candidate)
        kept_regexes.append(re.compile(rf"(?i)\b{frag}(?:'s|s|es)?\b"))

    return kept


def compile_disease_regex(terms: List[str]) -> re.Pattern:
    """
    Compile the keyword list of a DOID into a single unified regex pattern:
    - Negative lookbehinds against false/negation prefixes (pseudo-, non-, anti-)
    - Optional plural and possessive suffixes ('s, s, es) at word boundaries
    """
    fragments = [term_to_regex_fragment(
        t) for t in sorted(terms, key=len, reverse=True)]
    alternation = "|".join(fragments)
    full_pattern = (
        r"(?i)(?<!pseudo)(?<!pseudo-)(?<!non)(?<!non-)(?<!anti)(?<!anti-)"
        r"\b(?:" + alternation + r")(?:'s|s|es)?\b"
    )
    return re.compile(full_pattern)


def build_ontology_regex_engine(csv_path: str) -> Dict[str, Any]:
    """
    Read master_umls_dictionary.csv and construct the complete dictionary + regex engine
    for 33 Standalone diseases and 11 Parent folders (along with 30 Child diseases).
    """
    df = pd.read_csv(csv_path)

    meta_df = (
        df[["DOID", "Disease_Name", "Parent_Folder", "Is_Parent"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    df_clean = df[df["Vocabulary"].isin(CLEAN_VOCABULARIES)].copy()
    df_clean["cleaned_term"] = [
        clean_single_umls_string(n, t)
        for n, t in zip(df_clean["Name"], df_clean["Term Type"])
    ]

    raw_terms_by_doid: Dict[str, Set[str]] = {}
    for _, row in meta_df.iterrows():
        doid = row["DOID"]
        dname = str(row["Disease_Name"]).strip().lower()
        initial_set: Set[str] = set()
        if dname not in BLACKLIST_EXACT_TERMS:
            initial_set.add(dname)
        for seed in SUPPLEMENTAL_SEEDS.get(doid, []):
            seed_clean = seed.lower().strip()
            if seed_clean not in BLACKLIST_EXACT_TERMS:
                initial_set.add(seed_clean)
        raw_terms_by_doid[doid] = initial_set

    for _, row in df_clean.dropna(subset=["cleaned_term"]).iterrows():
        raw_terms_by_doid[row["DOID"]].add(row["cleaned_term"])

    for doid in raw_terms_by_doid:
        expanded_terms = expand_pathogen_abbreviations(raw_terms_by_doid[doid])
        raw_terms_by_doid[doid] = {
            t for t in expanded_terms if not _is_contaminated_pathogen_term(t)
        }

    standalone_nodes: Dict[str, Dict[str, Any]] = {}
    parent_folders: Dict[str, Dict[str, Any]] = {}

    standalone_df = meta_df[meta_df["Parent_Folder"] == "Standalone"]
    for _, row in standalone_df.iterrows():
        doid = row["DOID"]
        pruned_terms = prune_subsumed_phrases(raw_terms_by_doid[doid])
        standalone_nodes[doid] = {
            "doid": doid,
            "disease_name": row["Disease_Name"],
            "terms": pruned_terms,
            "regex": compile_disease_regex(pruned_terms),
        }

    hierarchy_df = meta_df[meta_df["Parent_Folder"] != "Standalone"]
    for pfolder_name, grp in hierarchy_df.groupby("Parent_Folder"):
        parent_row = grp[grp["Is_Parent"] == True].iloc[0]
        parent_doid = parent_row["DOID"]
        parent_raw_terms = raw_terms_by_doid[parent_doid]
        parent_pruned_terms = prune_subsumed_phrases(parent_raw_terms)

        parent_exclusion_set = set(parent_raw_terms) | set(parent_pruned_terms)
        for pt in list(parent_exclusion_set):
            parent_exclusion_set.add(pt + "s")
            parent_exclusion_set.add(pt + "es")

        children_dict: Dict[str, Dict[str, Any]] = {}
        child_rows = grp[grp["Is_Parent"] == False]
        for _, crow in child_rows.iterrows():
            cdoid = crow["DOID"]
            child_distinguishing_terms = {
                t for t in raw_terms_by_doid[cdoid] if t not in parent_exclusion_set
            }
            child_pruned_terms = prune_subsumed_phrases(
                child_distinguishing_terms)
            children_dict[cdoid] = {
                "doid": cdoid,
                "disease_name": crow["Disease_Name"],
                "terms": child_pruned_terms,
                "regex": compile_disease_regex(child_pruned_terms),
            }

        parent_folders[parent_doid] = {
            "parent_doid": parent_doid,
            "parent_name": parent_row["Disease_Name"],
            "folder_name": pfolder_name,
            "parent_terms": parent_pruned_terms,
            "parent_regex": compile_disease_regex(parent_pruned_terms),
            "children": children_dict,
        }

    return {
        "standalone": standalone_nodes,
        "parent_folders": parent_folders,
    }


# ==============================================================================
# STEP 3 & 4: JOIN MULTICARE TABLES, ROUTING & TARGET LABEL ASSIGNMENT
# ==============================================================================

def format_metadata_field(val: Any) -> str:
    """Safely convert list/array/string columns in metadata.parquet to string."""
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        return " ; ".join(str(x) for x in val if x is not None)
    if hasattr(val, "tolist"):
        return " ; ".join(str(x) for x in val.tolist() if x is not None)
    if pd.isna(val):
        return ""
    return str(val)


def export_cleaned_dictionary_preview(engine: Dict[str, Any], out_csv: str) -> None:
    """Export final cleaned keywords of 74 DOID codes along with target label rules to CSV."""
    rows = []
    for doid, node in engine["standalone"].items():
        lbl_doid, lbl_name, lbl_rule = resolve_final_diagnosis_label(
            "Standalone", doid, node["disease_name"], doid, node["disease_name"], "Standalone_Leaf"
        )
        rows.append({
            "Folder_Type": "Standalone",
            "Parent_DOID": doid,
            "Parent_Name": node["disease_name"],
            "DOID": doid,
            "Disease_Name": node["disease_name"],
            "Role": "Standalone_Leaf",
            "Target_Label_DOID": lbl_doid,
            "Target_Label_Disease_Name": lbl_name,
            "Label_Resolution_Rule": lbl_rule,
            "Keyword_Count": len(node["terms"]),
            "Cleaned_Keywords": " | ".join(node["terms"]),
        })

    for pdoid, pfolder in engine["parent_folders"].items():
        lbl_doid, lbl_name, lbl_rule = resolve_final_diagnosis_label(
            "Parent_Hierarchy", pdoid, pfolder["parent_name"], pdoid, pfolder["parent_name"], "Parent_Unspecified"
        )
        rows.append({
            "Folder_Type": "Parent_Hierarchy",
            "Parent_DOID": pdoid,
            "Parent_Name": pfolder["parent_name"],
            "DOID": pdoid,
            "Disease_Name": pfolder["parent_name"],
            "Role": "Parent_Base",
            "Target_Label_DOID": lbl_doid,
            "Target_Label_Disease_Name": lbl_name,
            "Label_Resolution_Rule": lbl_rule,
            "Keyword_Count": len(pfolder["parent_terms"]),
            "Cleaned_Keywords": " | ".join(pfolder["parent_terms"]),
        })
        for cdoid, cnode in pfolder["children"].items():
            clbl_doid, clbl_name, clbl_rule = resolve_final_diagnosis_label(
                "Parent_Hierarchy", pdoid, pfolder["parent_name"], cdoid, cnode["disease_name"], "Specific_Child"
            )
            rows.append({
                "Folder_Type": "Parent_Hierarchy",
                "Parent_DOID": pdoid,
                "Parent_Name": pfolder["parent_name"],
                "DOID": cdoid,
                "Disease_Name": cnode["disease_name"],
                "Role": "Child_Distinguishing (Subtracted Parent)",
                "Target_Label_DOID": clbl_doid,
                "Target_Label_Disease_Name": clbl_name,
                "Label_Resolution_Rule": clbl_rule,
                "Keyword_Count": len(cnode["terms"]),
                "Cleaned_Keywords": " | ".join(cnode["terms"]),
            })

    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(
        f"-> Exported cleaned keywords table with label rules for 74 DOID codes to: {out_csv}")


def _scan_chunk(args: Tuple[pd.DataFrame, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Worker function wrapping the scanning loop for parallel execution across CPU processes."""
    chunk_df, engine = args
    matched_records: List[Dict[str, Any]] = []

    standalone_nodes = engine["standalone"]
    parent_folders = engine["parent_folders"]

    for row in chunk_df.itertuples(index=False):
        text = row.search_text
        if not text:
            continue

        # BRANCH A: Scan 33 standalone disease folders
        for doid, node in standalone_nodes.items():
            m = node["regex"].search(text)
            if m:
                lbl_doid, lbl_name, lbl_rule = resolve_final_diagnosis_label(
                    "Standalone", doid, node["disease_name"], doid, node["disease_name"], "Standalone_Leaf"
                )
                matched_records.append({
                    "case_id": row.case_id,
                    "article_id": row.article_id,
                    "case_count_in_article": row.case_count,
                    "folder_type": "Standalone",
                    "parent_doid": doid,
                    "parent_name": node["disease_name"],
                    "assigned_doid": doid,
                    "assigned_disease_name": node["disease_name"],
                    "routing_level": "Standalone_Leaf",
                    "label_doid": lbl_doid,
                    "label_disease_name": lbl_name,
                    "label_resolution_rule": lbl_rule,
                    "matched_keyword": m.group(0).lower(),
                })

        # BRANCH B: Scan 11 parent disease hierarchies (Child-First -> Masked Parent Fallback)
        for pdoid, pfolder in parent_folders.items():
            child_hits: List[Tuple[str, str, str]] = []
            for cdoid, cnode in pfolder["children"].items():
                cm = cnode["regex"].search(text)
                if cm:
                    child_hits.append(
                        (cdoid, cnode["disease_name"], cm.group(0).lower()))

            if child_hits:
                for cdoid, cname, ckw in child_hits:
                    lbl_doid, lbl_name, lbl_rule = resolve_final_diagnosis_label(
                        "Parent_Hierarchy", pdoid, pfolder["parent_name"], cdoid, cname, "Specific_Child"
                    )
                    matched_records.append({
                        "case_id": row.case_id,
                        "article_id": row.article_id,
                        "case_count_in_article": row.case_count,
                        "folder_type": "Parent_Hierarchy",
                        "parent_doid": pdoid,
                        "parent_name": pfolder["parent_name"],
                        "assigned_doid": cdoid,
                        "assigned_disease_name": cname,
                        "routing_level": "Specific_Child",
                        "label_doid": lbl_doid,
                        "label_disease_name": lbl_name,
                        "label_resolution_rule": lbl_rule,
                        "matched_keyword": ckw,
                    })
            else:
                # Mask out omitted sibling mentions (e.g., 'alveolar echinococcosis', 'asymptomatic dengue')
                # rather than dropping the entire case if mentioned in the differential diagnosis
                sibling_excl_regex = OMITTED_SIBLING_EXCLUSION_REGEXES.get(
                    pdoid)
                parent_search_text = (
                    sibling_excl_regex.sub(
                        " ", text) if sibling_excl_regex else text
                )
                pm = pfolder["parent_regex"].search(parent_search_text)
                if pm:
                    lbl_doid, lbl_name, lbl_rule = resolve_final_diagnosis_label(
                        "Parent_Hierarchy", pdoid, pfolder["parent_name"], pdoid, pfolder[
                            "parent_name"], "Parent_Unspecified"
                    )
                    matched_records.append({
                        "case_id": row.case_id,
                        "article_id": row.article_id,
                        "case_count_in_article": row.case_count,
                        "folder_type": "Parent_Hierarchy",
                        "parent_doid": pdoid,
                        "parent_name": pfolder["parent_name"],
                        "assigned_doid": pdoid,
                        "assigned_disease_name": pfolder["parent_name"],
                        "routing_level": "Parent_Unspecified",
                        "label_doid": lbl_doid,
                        "label_disease_name": lbl_name,
                        "label_resolution_rule": lbl_rule,
                        "matched_keyword": pm.group(0).lower(),
                    })

    return matched_records


def filter_and_route_multicare(
    cases_parquet_path: str,
    metadata_parquet_path: str,
    csv_dictionary_path: str,
    output_parquet_path: str = "multicare_tropical_diseases_hard_filtered.parquet",
    output_csv_path: str = "multicare_tropical_diseases_hard_filtered.csv",
    workers: int = 8,
) -> pd.DataFrame:
    print("1. Compiling regex engine from master_umls_dictionary.csv...")
    engine = build_ontology_regex_engine(csv_dictionary_path)

    print("2. Reading cases.parquet and metadata.parquet...")
    cases_table = pq.read_table(cases_parquet_path)
    cases_raw_df = cases_table.to_pandas()

    if "cases" in cases_raw_df.columns:
        exploded = cases_raw_df.explode("cases").dropna(
            subset=["cases"]).reset_index(drop=True)
        cases_df = pd.json_normalize(exploded["cases"])
        cases_df["article_id"] = exploded["article_id"].values
    else:
        cases_df = cases_raw_df

    if "case_id" not in cases_df.columns:
        cases_df["case_id"] = cases_df.index.astype(str)
    if "case_text" not in cases_df.columns:
        text_cols = [c for c in cases_df.columns if "text" in c.lower()]
        cases_df["case_text"] = cases_df[text_cols[0]] if text_cols else ""

    cases_df = cases_df[["article_id", "case_id", "case_text"]]

    meta_raw = pd.read_parquet(metadata_parquet_path)
    if "article_metadata" in meta_raw.columns:
        meta_df = pd.json_normalize(meta_raw["article_metadata"])
        meta_df["article_id"] = meta_raw["article_id"].values
    else:
        meta_df = meta_raw

    if "case_amount" in meta_df.columns:
        meta_df["case_count"] = meta_df["case_amount"].fillna(1).astype(int)
    elif "amount of clinical cases" in meta_df.columns:
        meta_df["case_count"] = meta_df["amount of clinical cases"].fillna(
            1).astype(int)
    else:
        counts = cases_df.groupby("article_id")["case_id"].transform("count")
        meta_df = meta_df.merge(
            cases_df[["article_id"]].assign(
                case_count=counts).drop_duplicates("article_id"),
            on="article_id",
            how="left"
        )
        meta_df["case_count"] = meta_df["case_count"].fillna(1).astype(int)

    meta_df["article_meta_text"] = (
        meta_df.get("title", pd.Series("", index=meta_df.index)
                    ).apply(format_metadata_field)
        + " | "
        + meta_df.get("mesh_terms", pd.Series("", index=meta_df.index)
                      ).apply(format_metadata_field)
        + " | "
        + meta_df.get("major_mesh_terms", pd.Series("",
                      index=meta_df.index)).apply(format_metadata_field)
        + " | "
        + meta_df.get("keywords", pd.Series("", index=meta_df.index)
                      ).apply(format_metadata_field)
    )

    merged_df = cases_df.merge(
        meta_df[["article_id", "case_count", "article_meta_text"]],
        on="article_id",
        how="left",
    )
    merged_df["case_count"] = merged_df["case_count"].fillna(1).astype(int)

    is_single_case = merged_df["case_count"] == 1
    merged_df["search_text"] = merged_df["case_text"].fillna("")
    merged_df.loc[is_single_case, "search_text"] = (
        merged_df.loc[is_single_case, "article_meta_text"].fillna("")
        + "\n"
        + merged_df.loc[is_single_case, "case_text"].fillna("")
    )

    workers = max(1, workers)
    print(
        f"3. Scanning and routing {len(merged_df):,} clinical cases across 74 disease nodes on {workers} CPU workers...")
    cols_df = merged_df[["case_id", "article_id", "case_count", "search_text"]]
    chunk_size = max(1, (len(cols_df) + workers - 1) // workers)
    chunks = [
        (cols_df.iloc[i: i + chunk_size], engine)
        for i in range(0, len(cols_df), chunk_size)
    ]

    matched_records: List[Dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for res in executor.map(_scan_chunk, chunks):
            matched_records.extend(res)

    result_df = pd.DataFrame(matched_records)
    if not result_df.empty:
        raw_match_count = len(result_df)
        # Deduplicate on (case_id, label_disease_name) when multiple child subtypes
        # (e.g., P. falciparum + P. vivax) roll up to the same parent diagnosis label
        result_df = (
            result_df.drop_duplicates(
                subset=["case_id", "label_disease_name"], keep="first"
            )
            .reset_index(drop=True)
        )
        dedup_removed = raw_match_count - len(result_df)

        result_df.to_parquet(output_parquet_path, index=False)
        result_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")
        print(f"\n✅ COMPLETED!")
        print(
            f"   - Total deduplicated routing records: {len(result_df):,} (removed {dedup_removed:,} duplicate case-label rows)")
        print(
            f"   - Total unique case_id count        : {result_df['case_id'].nunique():,}")
        print(f"   - Results saved to                  : {output_csv_path}")

        print("\n--- SUMMARY BY TARGET LABEL (label_disease_name) ---")
        label_summary = (
            result_df.groupby(
                ["label_doid", "label_disease_name", "label_resolution_rule"])["case_id"]
            .nunique()
            .reset_index(name="unique_cases")
            .sort_values("unique_cases", ascending=False)
        )
        print(label_summary.head(30).to_string(index=False))
    else:
        print("No matching cases found.")

    return result_df


# ==============================================================================
# STEP 5: CLINICAL POST-FILTERING (STAGE 5 REFINEMENT)
# ==============================================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent  # Datasets/ repository root

TARGET_26_BENCHMARK_CLASSES: Set[str] = {
    "malaria", "amebiasis", "visceral leishmaniasis", "cutaneous leishmaniasis",
    "Chagas disease", "mucocutaneous leishmaniasis", "echinococcosis", "cysticercosis",
    "schistosomiasis", "strongyloidiasis", "filarial elephantiasis", "leptospirosis",
    "typhoid fever", "leprosy", "scrub typhus", "cholera", "melioidosis",
    "dengue disease", "chikungunya", "rabies", "yellow fever", "Japanese encephalitis",
    "Zika fever", "Ebola virus disease", "paracoccidioidomycosis", "scabies",
}


def load_post_filtering_classes(txt_path: str | Path | None = None) -> Set[str]:
    """Parse disease_post_filtering.txt if available, falling back to TARGET_26_BENCHMARK_CLASSES."""
    if txt_path and Path(txt_path).exists():
        classes: Set[str] = set()
        pattern = re.compile(r"^[│\s]*[├└]──\s+DOID:\S+\s+([^(]+?)\s+\(")
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    classes.add(m.group(1).strip())
        if len(classes) == 26:
            return classes
    return set(TARGET_26_BENCHMARK_CLASSES)


def apply_clinical_post_filtering(
    hard_filtered_df: pd.DataFrame,
    output_parquet_path: str | Path,
    output_csv_path: str | Path,
    post_filter_txt_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Stage 5: Filter hard-filtered dataset (50 classes) to the 26 target benchmark classes.
    Eliminates 18 ultra-rare tail diseases (<= 20 cases), 3 parent fallbacks lacking definitive guidelines,
    and 3 incidental/polymorphic diseases.
    """
    target_classes = load_post_filtering_classes(post_filter_txt_path)
    final_df = hard_filtered_df[
        hard_filtered_df["label_disease_name"].isin(target_classes)
    ].reset_index(drop=True)

    output_parquet_path = Path(output_parquet_path)
    output_csv_path = Path(output_csv_path)
    output_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    final_df.to_parquet(output_parquet_path, index=False)
    final_df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

    print(f"\n✅ POST-FILTERING STAGE 5 COMPLETED (Final Benchmark Dataset):")
    print(f"   - Total gold records                : {len(final_df):,}")
    print(f"   - Total unique case_id count        : {final_df['case_id'].nunique():,}")
    print(f"   - Target disease classes            : {final_df['label_disease_name'].nunique():,}")
    print(f"   - Saved final parquet to            : {output_parquet_path}")
    print(f"   - Saved final csv to                : {output_csv_path}")

    return final_df


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = BASE_DIR.parent.parent  # Datasets/ root

    DEFAULT_DICT = BASE_DIR / "UMLS" / "master_umls_dictionary.csv"
    DEFAULT_POST_TXT = BASE_DIR / "disease_post_filtering.txt"

    parser = argparse.ArgumentParser(
        description="MultiCaRe Tropical Diseases Regex Extraction & Taxonomy Routing Runner"
    )
    parser.add_argument("--cases", type=Path, default=None, help="Path to cases.parquet")
    parser.add_argument("--metadata", type=Path, default=None, help="Path to metadata.parquet")
    parser.add_argument("--dict", type=Path, default=DEFAULT_DICT, help="Path to master_umls_dictionary.csv")
    parser.add_argument("--out-dir", type=Path, default=BASE_DIR, help="Directory to save generated outputs")
    parser.add_argument("--workers", type=int, default=min(os.cpu_count() or 4, 8), help="CPU workers for parallel scan")
    parser.add_argument("--skip-scan", action="store_true", help="Compile and export dictionary preview only (no MultiCaRe scan)")

    args = parser.parse_args()

    # 1. Compile engine and export keyword preview
    engine_info = build_ontology_regex_engine(str(args.dict))
    print(
        f"Successfully compiled {len(engine_info['standalone'])} Standalone diseases and {len(engine_info['parent_folders'])} Parent hierarchies."
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    export_cleaned_dictionary_preview(
        engine_info,
        str(args.out_dir / "verified_74_doid_keywords.csv")
    )

    if args.skip_scan:
        print("\n✅ Dictionary compilation complete. Scanning skipped per --skip-scan flag.")
        exit(0)

    # 2. Resolve cases.parquet and metadata.parquet
    def resolve_candidate(provided: Path | None, filename: str) -> Path | None:
        if provided and provided.exists():
            return provided
        env_val = os.getenv(f"MULTICARE_{filename.split('.')[0].upper()}")
        if env_val and Path(env_val).exists():
            return Path(env_val)
        candidates = [
            BASE_DIR / filename,
            PROJECT_ROOT / "Official_MultiCaRe" / "whole_multicare_dataset" / filename,
            PROJECT_ROOT / "Archive-001" / filename,
            PROJECT_ROOT / "medical_datasets" / "whole_multicare_dataset" / filename,
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    cases_path = resolve_candidate(args.cases, "cases.parquet")
    metadata_path = resolve_candidate(args.metadata, "metadata.parquet")

    if cases_path and metadata_path:
        print(f"\n📂 Using input datasets:")
        print(f"   - Cases parquet   : {cases_path}")
        print(f"   - Metadata parquet: {metadata_path}")
        hard_filtered_df = filter_and_route_multicare(
            cases_parquet_path=str(cases_path),
            metadata_parquet_path=str(metadata_path),
            csv_dictionary_path=str(args.dict),
            output_parquet_path=str(args.out_dir / "multicare_tropical_diseases_hard_filtered.parquet"),
            output_csv_path=str(args.out_dir / "multicare_tropical_diseases_hard_filtered.csv"),
            workers=args.workers,
        )
        if not hard_filtered_df.empty:
            apply_clinical_post_filtering(
                hard_filtered_df=hard_filtered_df,
                output_parquet_path=args.out_dir / "multicare_tropical_disease_final.parquet",
                output_csv_path=args.out_dir / "multicare_tropical_disease_final.csv",
                post_filter_txt_path=DEFAULT_POST_TXT,
            )
    else:
        print("\n⚠️ MultiCaRe dataset parquets not found in default paths.")
        print("   Searched locations:")
        print(f"   - {BASE_DIR}")
        print(f"   - {PROJECT_ROOT / 'Official_MultiCaRe' / 'whole_multicare_dataset'}")
        print(f"   - {PROJECT_ROOT / 'Archive-001'}")
        print("\n   To run the full extraction, provide explicit paths via:")
        print("   python dataset_runner.py --cases /path/to/cases.parquet --metadata /path/to/metadata.parquet")
