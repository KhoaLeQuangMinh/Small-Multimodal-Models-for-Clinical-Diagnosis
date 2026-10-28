# smmcd-data-pipeline

Code for building **Part A**, a multimodal dataset of 1,797 published patient cases covering 22 tropical and infectious diseases, from the MultiCaRe collection of open-access PubMed Central case reports. Every label comes with exact quotes from the case text, and each label is graded against that disease's published case definition (WHO, CDC/CSTE, EORTC/MSGERC, …).

The dataset itself (cases, images, rewrites, case-definition grading) is published on Kaggle with a detailed README. This repository holds the scripts and prompts that produced it.

## Pipeline Components

The `data_pipeline/` module houses two complementary clinical extraction and curation frameworks:

1. **LLM Extraction & Verification Suite (`data_pipeline/llm/`):**
   - Multi-stage LLM-assisted clinical extraction requiring exact verbatim evidence quotes.
   - MedCaseReasoning blind case rewriting removing diagnostic spoilers from admission vignettes.
   - Algorithmic case-definition checklists (22 WHO/CDC classes).
   - Generates the 1,797-case `partA_final.jsonl` cohort.

2. **UMLS Regex Extraction & Taxonomic Routing Engine (`data_pipeline/regex_pipeline/`):**
   - Grounded in 74 DOID ontology nodes and 16 clean medical vocabularies in the UMLS Metathesaurus.
   - Implements two-pass hierarchical scanning (Child-First -> Sibling Differential Masking Fallback).
   - Solves critical microbiological disambiguations (Yaws vs Syphilis, Trachoma vs Urogenital Chlamydia).
   - Produces the 26-class gold benchmark dataset (`multicare_tropical_disease_final.parquet`, 2,674 rows).
   - Full documentation and usage guide: see [`data_pipeline/regex_pipeline/README.md`](regex_pipeline/README.md).

## LLM Pipeline (Part A)

```
MultiCaRe: 76,137 case reports
  │ Stage 1   keyword search                         → 2,437 candidate cases
  │ Stage 2   LLM labelling with exact quotes         → 1,797 cases, 1,800 labels
  │ Stage 3   non-clinical images removed             → 2,812 image panels
  │ Stage 4   blind rewrite (MedCaseReasoning)        → 1,783 rewrites
  │ Stage 5   case-definition checklist               → 1,820 labels graded
```

Design rules used throughout:
- **The LLM extracts, a script decides.** In stage 5, for example, the agent only ticks criteria (met / not met / not mentioned, with a quote), and `casedef_agent.py` applies the published rule.
- **Every quote is verified.** An answer whose quote is not found word for word in the cited sentence is rejected and re-run.
- **No API calls from these scripts.** Each LLM stage writes a self-contained *package* (one prompt file per case, a manifest and a `RUNNER.md`), which is run by LLM subagents in Google Antigravity, one case per task. The scripts then check and merge the answers.

## Scripts by stage

All scripts are in `llm/` and are run from the repository root.

| Stage | Script | What it does |
|---|---|---|
| 1 | `build_partA.py` | Keyword search over MultiCaRe with one inclusion rule per class (term in title/MeSH/keywords/captions and/or case text) → `llm/cohort_partA.jsonl` |
| 2a | `prompt.py`, `make_handoff.py`, `merge_responses.py`, `check_quotes.py` | First labelling round (prompt v3): packages, merge, quote check |
| — | *(one-off clean-up passes)* | Scope, animal cases, latent TB, labelling mistakes, not-main cases → `llm/partA_present.jsonl` (1,797 cases) |
| 2b | `prompt_v4.py` | Labelling prompt v4: per-class verdict (present / absent / uncertain), role (main / secondary / incidental), exact evidence quotes, against written definitions of the 22 classes |
| 2b | `make_handoff_v4.py`, `split_package_v4.py` | Build the v4 packages (split by article, stratified by class, a calibration set in every package) |
| 2b | `check_v4.py`, `merge_v4.py` | Validate the answers and merge them → `llm/partA_final.jsonl` |
| 3 | *(one-off)* | Removal of non-clinical panels (charts, ECG/EEG traces, gels, maps, diagrams, blank panels) |
| 4 | `rewrite_agent.py` | Blind rewrite adapted from MedCaseReasoning (Wu et al., 2025): case presentation up to the diagnosis, reasoning with exact quotes, blind final diagnosis, quality rubric. Script flags: label terms leaked, numbers not in source, figure references, blind diagnosis vs label |
| 5 | `casedef_agent.py` | Case-definition checklist: 22 checklists from published sources, the agent's ticks, quote checks, and the 22 rule functions that assign confirmed / probable / possible / insufficient |
| validation | `css_agent.py` | Evidence-strength tiers (organism shown / indirect but specific / clinical only / stated only), used for the 500-case validation |

Shared modules:
- `mask_regex.py`: the sentence splitter and the per-class term lists (names, synonyms, organisms, tests, drugs) used in stages 1, 4 and 5.
- `mask_agent.py`: an earlier masking stage, no longer part of the pipeline. It is kept because stages 4 and 5 reuse its `RUNNER_MD` template.

Data files in `llm/`:
- `css_pilot50_ids.txt`, `css_package{1,2,3}_ids.txt`: the case lists for the pilot and the three packages of stages 4 and 5 (split by article, no overlap).
- `label_additions.jsonl`: 20 diseases (19 cases) that the labeller named but that were never keyword candidates; checked in stage 5, not merged into the labels.

## Running a stage

```bash
# Stage 4: build a package, run it in Antigravity (see RUNNER.md inside), then check and apply
python3 llm/rewrite_agent.py build --ids llm/css_package1_ids.txt --out handoff_rewrite/package-1
python3 llm/rewrite_agent.py check handoff_rewrite/package-1/responses
python3 llm/rewrite_agent.py apply handoff_rewrite/package-1/responses --out llm/rewrite_package1.jsonl

# Stage 5: same pattern
python3 llm/casedef_agent.py build --ids llm/css_package1_ids.txt --out handoff_casedef/package-1
python3 llm/casedef_agent.py check handoff_casedef/package-1/responses
python3 llm/casedef_agent.py apply handoff_casedef/package-1/responses --out llm/casedef_package1.jsonl
```

`build` refuses to overwrite a package whose `responses/` folder already has answers.

## Data you need

Nothing under `Archive-001/`, `llm/*.jsonl` (except `label_additions.jsonl`) or the package folders is committed (see `.gitignore`).
- **Stage 1** needs the MultiCaRe files in `Archive-001/`: `cases.parquet`, `metadata.parquet`, `case_images.parquet`, `captions_and_labels.csv` and the image folders.
- **Stages 4–5** need `llm/partA_final.jsonl`, which is in the Kaggle dataset; copy it into `llm/`. Its `images[].path` there is relative to the Kaggle folder.

Requirements: Python 3.9+. Stage 1 also needs `pyarrow`; everything else uses the standard library only.

## Documentation

- `docs/case_definitions.md`: the 22 checklists, their sources and verification status, the choices made where a source is unclear (cautious reading used, liberal reading reported as a sensitivity analysis), and the changes made after the pilot.
- `docs/references.md`: citations and links for every case definition and method paper.

## Main references

- Nievas Offidani M, Delrieux C. The MultiCaRe dataset: a multimodal case report dataset with clinical cases, labeled images and captions from open access PMC articles. *Data in Brief* 2024.
- Wu K, Wu E, Thapa R, et al. MedCaseReasoning: evaluating and learning diagnostic reasoning from clinical case reports. arXiv:2505.11733, 2025.
- Bonhoeffer J, et al. The Brighton Collaboration: addressing the need for standardized case definitions of adverse events following immunization. *Vaccine* 2002;21:298–302.
