# MultiCaRe Tropical Diseases Dataset — Curated Benchmark Release

An expert-curated, clinically audited multimodal dataset derived from open-access PubMed Central (PMC) clinical case reports in the **MultiCaRe** corpus, designed for benchmarking **Small Multimodal Models for Clinical Diagnosis (SMMCD)** on Neglected Tropical Diseases (NTDs) and related infectious diseases.

---

## 1. Executive Summary & Quality Audit Overview

Following an exhaustive audit comparing extraction keywords against source article titles, medical microbiology taxonomy, and clinical ground truth, **four major diagnostic bugs in naive UMLS extraction were identified and resolved**:

1. **Yaws Disambiguation:** 288 out of 289 initial "Yaws" rows were actually **Syphilis** (*Treponema pallidum* subsp. *pallidum*). True Yaws (*T. pallidum* subsp. *pertenue*) has only **1 true case** in MultiCaRe and has been moved to the omitted tail group.
2. **Trachoma Disambiguation:** 85 out of 90 initial "Trachoma" rows were **Genital Chlamydia** (serovars D–K: epididymitis, pelvic inflammatory disease, proctitis). True blinding ocular Trachoma (serovars A–C) has only **5 true cases** and has been moved to the omitted tail group.
3. **Subtype Deduplication:** 61 redundant rows caused by patients matching multiple subtypes of the same parent (e.g. *P. falciparum* + *P. vivax* in mixed malaria) were collapsed, guaranteeing **one row per confirmed patient-disease diagnosis**.
4. **Sibling Exclusion Gate Disambiguation:** The old gate blindly dropped real cystic echinococcosis cases whenever a non-target sibling (*alveolar echinococcosis*) was discussed as a *differential diagnosis*. This was replaced with child-first scanning and masked parent fallback, rescuing 15 verified cystic cases.

### Dataset Metric Comparison

| Metric | Cleaned Final Gold Benchmark (`chosen_26`) | Intermediate Hard Filter (`hard_filtered`) |
|:---|:---:|:---:|
| **Total Diagnostic Rows** | **2,674** | 2,967 |
| **Unique Patients (`case_id`)** | **2,140** | 2,351 |
| **Unique Source Articles (`article_id`)** | **1,951** | 2,138 |
| **Target Disease Classes** | **26** | 50 |
| **Single-Label Patients** | **1,791 (83.7%)** | 1,952 (83.0%) |
| **Multi-Label Patients** | **349 (16.3%)** | 399 (17.0%) |
| **Syphilis False Positives in Yaws** | **0** (288 purged) | 0 (purged in engine) |
| **Genital Chlamydia False Positives in Trachoma** | **0** (85 purged) | 0 (purged in engine) |
| **Duplicate Mixed-Subtype Rows** | **0** (61 deduplicated) | 0 (deduplicated) |
| **Omitted Classes (Tail $\le 20$ / Unspecified / Incidental)** | **24** | 0 |

---

## 2. Deep-Dive Audit: Problems Found & How They Were Solved

### Bug 1: Yaws Was 99.7% Syphilis (288 / 289 Rows)
* **The Mechanism:** In `SUPPLEMENTAL_SEEDS`, Yaws was seeded with its subspecies: `"treponema pallidum pertenue"`. When `expand_pathogen_abbreviations()` processed this term, two lines at the top of the function unconditionally generated the two-word binomial `genus + species`, adding `"treponema pallidum"` and `"t. pallidum"` to Yaws.
* **The Clinical Error:** *Treponema pallidum* is the species responsible for **Syphilis** (*T. pallidum* subsp. *pallidum*). Yaws is an endemic non-venereal skin and bone NTD. Because Syphilis is a common global STI, 288 papers discussing neurosyphilis, congenital syphilis, and primary chancres matched and were mislabeled as Yaws. None of the 279 titles mentioned yaws; 84 explicitly mentioned syphilis.
* **The Fix:** 
  1. Handled trinomial expansions conditionally in `expand_pathogen_abbreviations()` so that `expanded.add(f"{genus} {species}")` never fires when a subspecies is present for *Treponema pallidum*.
  2. Added an explicit post-expansion guard `_is_contaminated_pathogen_term()` that discards any bare `"treponema pallidum"` or `"t. pallidum"` term without `"pertenue"`.
* **The Result:** Yaws drops to **1 true case** (`PMC3557992_01`). Because $\le 20$ cases cannot support statistical training or validation splits, Yaws moves into the **Omitted Tail Diseases** group.

### Bug 2: Trachoma Was 94.4% Genital Chlamydia (85 / 90 Rows)
* **The Mechanism:** `SUPPLEMENTAL_SEEDS` attached `"chlamydia trachomatis"` to `DOID:11265` (Trachoma). The expander added `"c. trachomatis"`.
* **The Clinical Error:** *Chlamydia trachomatis* has distinct serovars:
  - Serovars **A, B, Ba, C** cause **Trachoma** (blinding ocular keratoconjunctivitis).
  - Serovars **D–K** cause **Urogenital Chlamydia** (urethritis, epididymitis, PID, proctitis).
  - Serovars **L1–L3** cause **Lymphogranuloma Venereum (LGV)**.
  Adding the bare species name caused 85 cases of chronic epididymitis, pelvic inflammatory disease, and routine STI screening to be labeled as Trachoma.
* **The Fix:** Removed `"chlamydia trachomatis"` from `SUPPLEMENTAL_SEEDS["DOID:11265"]` and removed `chlamydia` from `KNOWN_PATHOGEN_GENERA`. Trachoma now strictly matches `["trachoma", "trachomatous"]`.
* **The Result:** Trachoma drops to **5 true cases** (all ocular). With $\le 20$ cases, Trachoma moves into the **Omitted Tail Diseases** group.

### Bug 3: Duplicate Mixed-Subtype Rows (61 Redundant Rows)
* **The Mechanism:** In parent rollup hierarchies (like Malaria), when a patient had mixed infections (*P. falciparum* and *P. vivax* in `PMC3350299_01`), each child hit appended a row. Both rolled up to `label_disease_name = "malaria"`, creating duplicate identical rows for the same patient.
* **The Fix:** Applied `.drop_duplicates(subset=["case_id", "label_disease_name"])` before saving.
* **The Result:** 61 redundant rows (54 in malaria, 7 in schistosomiasis) were removed. Every patient has exactly one row per distinct disease diagnosis.

### Bug 4: Sibling Exclusion Gate (Differential Diagnosis False Negatives)
* **The Mechanism:** The code previously checked:
  ```python
  sibling_excl_regex = OMITTED_SIBLING_EXCLUSION_REGEXES.get(pdoid)
  if sibling_excl_regex and sibling_excl_regex.search(text):
      continue
  ```
* **The Clinical Error:** In clinical case reports, doctors extensively discuss differential diagnoses. In case `PMC3350145_01`, the author wrote: *"Pathology confirmed cystic echinococcosis caused by Echinococcus granulosus; we never encounter hydatid disease secondary to Echinococcus multilocularis."* Because `"echinococcus multilocularis"` appeared in the differential diagnosis, the entire patient was discarded!
* **The Fix:** Replaced the global `continue` check with a two-pass architecture:
  1. **Pass 1 (Child-First):** Specific target children (e.g. `DOID:1495` cystic echinococcosis) are scanned against the unmasked text. If matched, recorded directly as `Specific_Child`.
  2. **Pass 2 (Masked Fallback):** If no child matched, sibling mentions are masked out: `parent_search_text = sibling_excl_regex.sub(" ", text)`. Then `parent_regex` is scanned.
* **The Result:** Rescued 15 legitimate cases of cystic echinococcosis (increasing from 356 to 371), while ensuring pure alveolar cases are masked out and cleanly excluded.

---

## 3. Directory Structure & File Manifest

All files in this directory (`data_pipeline/regex_pipeline/`) represent the curated pipeline:

```text
data_pipeline/regex_pipeline/
│
├── README.md                                    # This comprehensive dataset documentation
├── disease_post_filtering.txt                   # Flat 26-disease taxonomy organized by pathogen class
├── disease_pre_filtering.txt                    # Original 74-DOID hierarchical taxonomy (11 parent + 33 standalone)
│
├── multicare_tropical_disease_final.parquet     # Official clean gold benchmark dataset (2,674 rows, 2,140 patients, 26 classes)
├── multicare_tropical_disease_final.csv         # CSV counterpart of the final gold dataset
│
├── multicare_tropical_diseases_hard_filtered.parquet # Intermediate extraction before post-filtering (50 classes, 2,967 rows)
├── multicare_tropical_diseases_hard_filtered.csv     # CSV counterpart of the hard-filtered extraction
│
├── verified_74_doid_keywords.csv                # Audited, cleaned dictionary of keywords and routing rules
├── dataset_runner.py                            # Unified regex extraction & hierarchy routing engine
│
├── UMLS/                                        # Master UMLS dictionary and cleaned keyword caches (78 disease CSVs)
│   ├── master_umls_dictionary.csv
│   └── UMLS_LOOKUP_TABLE.md
└── UMLS_raw_backup/                             # Raw concept definitions and backups (if present locally)
```

---

## 4. End-to-End Pipeline Architecture

```
[doid.obo & UMLS Metathesaurus]
             │
             ▼
[Stage 1: Taxonomy Grounding (74 DOID Nodes)] ───► disease_pre_filtering.txt
             │
             ▼
[Stage 2: Semantic Disambiguation & Regex Engine]
  - Filter 16 clean medical vocabularies (MeSH, SNOMED, ICD-10...)
  - Blacklist stemmer errors & homonyms ("yaw", "mycetoma", "pian", "coenurosis")
  - Inject Supplemental Seeds (Tier 1 CUI recovery + Tier 2 causative pathogens)
  - Latin binomial expansion across 39 genera ("V. cholerae", "P. falciparum")
  - Purge Syphilis species terms from Yaws terms ("treponema pallidum", "t. pallidum")
  - Remove bare "chlamydia trachomatis" from Trachoma terms
  - Subtract generic parent terms from children (parent_exclusion_set)
  - Subsumption pruning & compile with (?<!pseudo)(?<!non)(?<!anti) boundaries
             │
             ▼
[Stage 3: MultiCaRe Joint Extraction & Hierarchy Routing] ───► dataset_runner.py
  - Search article title, case narrative, figure captions, MeSH terms
  - Single-case papers: Prepend article metadata to case text
  - Multi-case papers: Restrict search to patient's individual narrative (no bleeding)
  - Scan Standalone Leaf Direct (33 nodes)
  - Scan Parent Hierarchies (11 nodes): Child-First Scan ──► Masked Sibling Parent Fallback
  - Resolve training label: Rollup_To_Parent (7) vs Use_Specific_Child (4)
  - Deduplicate on (case_id, label_disease_name)
             │
             ▼
[Stage 4: Intermediate Hard Filtered Dataset] ───► multicare_tropical_diseases_hard_filtered.* (50 classes, 2,967 rows)
             │
             ▼
[Stage 5: Clinical Post-Filtering Refinement]
  - Eliminate 3 ambiguous parent fallbacks (unspecified leishmaniasis/filariasis/trypanosomiasis)
  - Omit 18 ultra-rare tail diseases (<= 20 cases), including Yaws (1) and Trachoma (5)
  - Omit 3 diseases with non-standardized/polymorphic criteria (ascariasis, fascioliasis, sporotrichosis)
  - Flatten taxonomy into 26 gold benchmark targets across 6 pathogen classes
             │
             ▼
[Stage 6: Final Curated Gold Dataset] ───► multicare_tropical_disease_final.parquet (2,674 rows, 2,140 patients)
                                     ───► disease_post_filtering.txt (26 classes)
```

---

## 5. The Final 26 Disease Classes & Complete Distribution Table

The table below reflects the clean, verified statistics of **`multicare_tropical_disease_final`**:

| # | Disease Name | Pathogen Class | DOID | Origin Type | Resolution Rule | Total Cases | Unique Articles | Single Cases | Single % | Multi Cases | Multi % | Avg Multi Size | Avg Extra |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **malaria** | Protozoan | DOID:12365 | Parent_Hierarchy | Rollup_To_Parent | 436 | 406 | 273 | 62.6% | 163 | 37.4% | 2.75 | +1.75 |
| **2** | **echinococcosis** | Helminth | DOID:1496 | Parent_Hierarchy | Rollup_To_Parent | 371 | 350 | 344 | 92.7% | 27 | 7.3% | 2.67 | +1.67 |
| **3** | **dengue disease** | Viral | DOID:12205 | Parent_Hierarchy | Rollup_To_Parent | 332 | 280 | 159 | 47.9% | 173 | 52.1% | 2.80 | +1.80 |
| **4** | **leptospirosis** | Bacterial | DOID:2297 | Standalone | Standalone_Direct | 141 | 129 | 78 | 55.3% | 63 | 44.7% | 2.98 | +1.98 |
| **5** | **typhoid fever** | Bacterial | DOID:13258 | Standalone | Standalone_Direct | 136 | 129 | 68 | 50.0% | 68 | 50.0% | 2.93 | +1.93 |
| **6** | **cysticercosis** | Helminth | DOID:10079 | Parent_Hierarchy | Use_Specific_Child | 132 | 126 | 119 | 90.2% | 13 | 9.8% | 2.46 | +1.46 |
| **7** | **leprosy** | Bacterial | DOID:1024 | Parent_Hierarchy | Rollup_To_Parent | 124 | 119 | 108 | 87.1% | 16 | 12.9% | 2.38 | +1.38 |
| **8** | **schistosomiasis** | Helminth | DOID:1395 | Parent_Hierarchy | Rollup_To_Parent | 98 | 94 | 74 | 75.5% | 24 | 24.5% | 2.75 | +1.75 |
| **9** | **amebiasis** | Protozoan | DOID:9181 | Standalone | Standalone_Direct | 91 | 88 | 62 | 68.1% | 29 | 31.9% | 2.62 | +1.62 |
| **10** | **visceral leishmaniasis** | Protozoan | DOID:9146 | Parent_Hierarchy | Use_Specific_Child | 87 | 81 | 51 | 58.6% | 36 | 41.4% | 2.50 | +1.50 |
| **11** | **scrub typhus** | Bacterial | DOID:13371 | Standalone | Standalone_Direct | 64 | 61 | 27 | 42.2% | 37 | 57.8% | 3.32 | +2.32 |
| **12** | **cutaneous leishmaniasis** | Protozoan | DOID:9111 | Parent_Hierarchy | Use_Specific_Child | 60 | 60 | 34 | 56.7% | 26 | 43.3% | 2.27 | +1.27 |
| **13** | **strongyloidiasis** | Helminth | DOID:10955 | Standalone | Standalone_Direct | 59 | 56 | 43 | 72.9% | 16 | 27.1% | 2.19 | +1.19 |
| **14** | **chikungunya** | Viral | DOID:0050012 | Standalone | Standalone_Direct | 58 | 55 | 13 | 22.4% | 45 | 77.6% | 3.31 | +2.31 |
| **15** | **rabies** | Viral | DOID:11260 | Standalone | Standalone_Direct | 58 | 51 | 49 | 84.5% | 9 | 15.5% | 3.00 | +2.00 |
| **16** | **cholera** | Bacterial | DOID:1498 | Standalone | Standalone_Direct | 56 | 51 | 42 | 75.0% | 14 | 25.0% | 2.71 | +1.71 |
| **17** | **melioidosis** | Bacterial | DOID:5052 | Standalone | Standalone_Direct | 56 | 54 | 45 | 80.4% | 11 | 19.6% | 2.55 | +1.55 |
| **18** | **Chagas disease** | Protozoan | DOID:12140 | Parent_Hierarchy | Use_Specific_Child | 53 | 43 | 41 | 77.4% | 12 | 22.6% | 3.00 | +2.00 |
| **19** | **scabies** | Ectoparasitic | DOID:8295 | Parent_Hierarchy | Rollup_To_Parent | 50 | 43 | 46 | 92.0% | 4 | 8.0% | 2.00 | +1.00 |
| **20** | **Japanese encephalitis** | Viral | DOID:10844 | Standalone | Standalone_Direct | 41 | 41 | 24 | 58.5% | 17 | 41.5% | 3.24 | +2.24 |
| **21** | **paracoccidioidomycosis** | Fungal | DOID:12662 | Standalone | Standalone_Direct | 41 | 40 | 29 | 70.7% | 12 | 29.3% | 2.42 | +1.42 |
| **22** | **Zika fever** | Viral | DOID:0060478 | Standalone | Standalone_Direct | 34 | 33 | 18 | 52.9% | 16 | 47.1% | 3.06 | +2.06 |
| **23** | **filarial elephantiasis** | Helminth | DOID:12211 | Parent_Hierarchy | Use_Specific_Child | 27 | 27 | 21 | 77.8% | 6 | 22.2% | 2.83 | +1.83 |
| **24** | **yellow fever** | Viral | DOID:9682 | Standalone | Standalone_Direct | 27 | 26 | 5 | 18.5% | 22 | 81.5% | 3.23 | +2.23 |
| **25** | **mucocutaneous leishmaniasis** | Protozoan | DOID:9155 | Parent_Hierarchy | Use_Specific_Child | 21 | 20 | 4 | 19.0% | 17 | 81.0% | 2.35 | +1.35 |
| **26** | **Ebola virus disease** | Viral | DOID:4325 | Standalone | Standalone_Direct | 21 | 21 | 14 | 66.7% | 7 | 33.3% | 3.14 | +2.14 |

---

## 6. Omitted Classes (24 Entities Excluded from Benchmark)

A total of **24 disease entities** are excluded from model training and evaluation due to case sparsity, lack of standardized diagnostic guidelines, or non-specific clinical presentations:

1. **3 Unspecified Parent Fallbacks (Ambiguous Clinical Presentation):**
   - `leishmaniasis` (unspecified, 46 cases) — Lacks anatomical/subtype distinction (visceral vs. cutaneous vs. mucocutaneous).
   - `filariasis` (unspecified, 20 cases) — Lacks species/presentation distinction (elephantiasis vs. loiasis vs. onchocerciasis).
   - `trypanosomiasis` (unspecified, 4 cases) — Lacks distinction between American (Chagas) and African (sleeping sickness).

2. **3 Difficult Guidelines / Incidental / Polymorphic Infections:**
   - `sporotrichosis` (41 cases) — Polymorphic fungal infection (lymphocutaneous, pulmonary, osteoarticular) lacking unified non-invasive diagnostic guidelines.
   - `ascariasis` (32 cases) — Highly variable, frequently incidental gastrointestinal finding rather than acute diagnostic challenge.
   - `fascioliasis` (23 cases) — Hepatic fluke with variable/non-standardized imaging criteria and challenging differential diagnosis guidelines.

3. **18 Ultra-Rare Tail Classes ($\le 20$ Verified Cases in MultiCaRe):**
   - `chromoblastomycosis` (14 cases)
   - `clonorchiasis` (13 cases)
   - `Buruli ulcer disease` (13 cases)
   - `eumycotic mycetoma` (13 cases)
   - `angiostrongyliasis` (12 cases)
   - `paragonimiasis` (11 cases)
   - `taeniasis` (adult intestinal, 8 cases)
   - `Rift Valley fever` (7 cases)
   - `ancylostomiasis` (7 cases)
   - `trichuriasis` (6 cases)
   - `sleeping sickness` (5 cases)
   - `onchocerciasis` (5 cases)
   - `trachoma` (5 cases — 85 genital chlamydia false positives purged)
   - `loiasis` (4 cases)
   - `dracunculiasis` (1 case)
   - `mansonelliasis` (1 case)
   - `necatoriasis` (1 case)
   - `yaws` (1 case — 288 syphilis false positives purged)

---

## 7. Data Schema & Field Reference

Every row in `multicare_tropical_disease_final.parquet` and `.csv` contains 13 fields:

| Field Name | Type | Description | Example |
|:---|:---:|:---|:---|
| `case_id` | string | Unique patient case identifier in MultiCaRe | `PMC5585634_01` |
| `article_id` | string | PubMed Central article accession ID | `PMC5585634` |
| `case_count_in_article` | int64 | Number of patient cases reported in the source paper | `1` |
| `folder_type` | string | Origin classification in initial ontology (`Standalone` or `Parent_Hierarchy`) | `Parent_Hierarchy` |
| `parent_doid` | string | Disease Ontology ID of the parent folder | `DOID:12365` |
| `parent_name` | string | Normalized name of the parent folder | `malaria` |
| `assigned_doid` | string | Specific DOID matched by the regex engine before rollup | `DOID:14067` |
| `assigned_disease_name` | string | Disease or subtype name matched before rollup | `Plasmodium falciparum malaria` |
| `routing_level` | string | Hierarchy scanning level (`Standalone_Leaf`, `Specific_Child`, `Parent_Unspecified`) | `Specific_Child` |
| `label_doid` | string | **Official target label DOID for model training/evaluation** | `DOID:12365` |
| `label_disease_name` | string | **Official target disease class name for model training/evaluation** | `malaria` |
| `label_resolution_rule` | string | Clinical rule applied (`Rollup_To_Parent`, `Use_Specific_Child`, `Standalone_Direct`) | `Rollup_To_Parent` |
| `matched_keyword` | string | Exact keyword string matched in text | `falciparum malaria` |

---

## 8. Quick Start: Loading and Inspecting the Data

### A. Loading the Dataset in Python

```python
import pandas as pd
from pathlib import Path

# Cross-platform relative path
DATA_DIR = Path(__file__).resolve().parent if "__file__" in locals() else Path("data_pipeline/regex_pipeline")

# 1. Load the official gold dataset
df = pd.read_parquet(DATA_DIR / "multicare_tropical_disease_final.parquet")
print(f"Loaded {len(df)} records across {df['case_id'].nunique()} unique patients.")

# 2. Inspect patient label degrees (single vs multi-label)
patient_degrees = df.groupby("case_id")["label_disease_name"].nunique()
print(f"Single-label cases: {(patient_degrees == 1).sum()} ({(patient_degrees == 1).mean():.1%})")
print(f"Multi-label cases:  {(patient_degrees > 1).sum()} ({(patient_degrees > 1).mean():.1%})")

# 3. View top co-occurring disease pairs
from itertools import combinations
from collections import Counter

multi_patients = df.groupby("case_id")["label_disease_name"].unique()
pairs = Counter()
for labels in multi_patients:
    if len(labels) > 1:
        for p in combinations(sorted(labels), 2):
            pairs[p] += 1

print("\nTop 5 Co-occurring Disease Pairs:")
for pair, count in pairs.most_common(5):
    print(f"  {pair[0]} + {pair[1]}: {count} cases")
```

### B. Running the Dataset Extraction & Routing Engine

```bash
# 1. Compile regex dictionary and preview keywords only (fast smoke test):
python3 data_pipeline/regex_pipeline/dataset_runner.py --skip-scan

# 2. Run full extraction over MultiCaRe (auto-detects Official_MultiCaRe/whole_multicare_dataset):
python3 data_pipeline/regex_pipeline/dataset_runner.py

# 3. Or provide custom file locations explicitly:
python3 data_pipeline/regex_pipeline/dataset_runner.py \
    --cases Official_MultiCaRe/whole_multicare_dataset/cases.parquet \
    --metadata Official_MultiCaRe/whole_multicare_dataset/metadata.parquet \
    --workers 8
```

---

## 9. Integrity Guarantees & Verification Checklist

- [x] **0 Syphilis False Positives in Yaws:** *Treponema pallidum* is purged from Yaws; Yaws reflects true endemic *pertenue* cases only.
- [x] **0 Genital Chlamydia False Positives in Trachoma:** *C. trachomatis* genital infections purged; Trachoma reflects true ocular keratoconjunctivitis only.
- [x] **0 Duplicate Mixed-Subtype Rows:** Deduplicated on `(case_id, label_disease_name)` to ensure 1 row per confirmed disease.
- [x] **0 Differential Diagnosis Drops:** Sibling exclusion gate removed, rescuing genuine cases where siblings were discussed in differential diagnoses.
- [x] **Zero Nulls:** Every row has complete, non-null values across all 13 columns.
- [x] **Format Parity:** Identical values, row orders, and counts in `.parquet` and `.csv`.
