# References for the data pipeline

> The PDFs and pages listed here are **not** in this repository (they belong to their publishers). Every entry has its citation and link; the file names are those used in the authors' local copy.

Copies of the sources behind Stage 4 (blind rewrite) and Stage 7 (case-definition checklists), downloaded 2026-10-16. The checklists and rules that actually run are in `llm/casedef_agent.py`; the choices table is in `llm/case_definitions_draft.md`.

## Case definitions (`case_definitions/`)

| Disease | File | Citation | Section used |
|---|---|---|---|
| Tuberculosis | `01_tuberculosis_WHO_definitions_2013rev_Dec2014.pdf` | WHO. *Definitions and reporting framework for tuberculosis – 2013 revision* (updated Dec 2014 and Jan 2020). WHO/HTM/TB/2013.2. https://www.who.int/publications/i/item/9789241505345 | §2.1, p. 1 ("bacteriologically confirmed" / "clinically diagnosed"). The copy is the Dec 2014 print; the Jan 2020 update only adds LF-LAM to the rapid tests, which our T3 item already includes |
| Malaria | `02_malaria_WHO_terminology_2021.pdf` | WHO. *WHO malaria terminology, 2021 update*. https://www.who.int/publications/i/item/9789240038400 | Glossary: "case, malaria", "case, presumed", "case, suspected malaria", "malaria infection" |
| Dengue | `03_dengue_CDC_CSTE_2015.html` | CDC/CSTE. *Dengue virus infections, 2015 case definition* (NNDSS). https://ndc.services.cdc.gov/case-definitions/dengue-virus-infections-2015/ | Clinical and laboratory criteria, case classification |
| Zika virus | `04_zika_CDC_CSTE_2016.html` | CDC/CSTE. *Zika virus disease and Zika virus infection, 2016 case definition*. https://ndc.services.cdc.gov/case-definitions/zika-virus-disease-and-zika-virus-infection-2016/ | Laboratory criteria, case classification |
| Leptospirosis | `05_leptospirosis_CDC_CSTE_2013.html` | CDC/CSTE. *Leptospirosis, 2013 case definition* (position statement 12-ID-02). https://ndc.services.cdc.gov/case-definitions/leptospirosis-2013/ | Clinical, laboratory, case classification |
| Melioidosis | `06_melioidosis_CDC_CSTE_2012.html` | CDC/CSTE. *Melioidosis, 2012 case definition*. https://ndc.services.cdc.gov/case-definitions/melioidosis-2012/ | Laboratory criteria, case classification |
| Scabies | `07_scabies_IACS_2020_Engelman_BJD.xml` (full text) | Engelman D, et al. The 2020 International Alliance for the Control of Scabies Consensus Criteria for the Diagnosis of Scabies. *Br J Dermatol* 2020;183(5):808–820. doi:10.1111/bjd.18943. PMC7687112 | Table 1 (levels A/B/C) |
| Talaromycosis, Paracoccidioidomycosis | `08-09_talaromycosis_PCM_EORTC-MSGERC_2020_Donnelly_CID.xml` (full text) | Donnelly JP, et al. Revision and update of the consensus definitions of invasive fungal disease from the EORTC and the MSGERC. *Clin Infect Dis* 2020;71(6):1367–1376. doi:10.1093/cid/ciz1008. PMC7486838 | Endemic mycoses: proven / probable |
| Neurocysticercosis | `10_neurocysticercosis_DelBrutto_2017_JNeurolSci.pdf` | Del Brutto OH, et al. Revised diagnostic criteria for neurocysticercosis. *J Neurol Sci* 2017;372:202–210. doi:10.1016/j.jns.2016.11.045 | Table 1 |
| Echinococcosis | `11_echinococcosis_Brunetti_WHO-IWGE_2010_ActaTrop.pdf` | Brunetti E, Kern P, Vuitton DA; WHO-IWGE Writing Panel. Expert consensus for the diagnosis and treatment of cystic and alveolar echinococcosis in humans. *Acta Trop* 2010;114(1):1–16. doi:10.1016/j.actatropica.2009.11.001 | §3.3 C (cystic), §4.4.1 C (alveolar): possible / probable / confirmed |
| Leishmaniasis | `12_leishmaniasis_WHO_TRS949_2010.pdf` | WHO Expert Committee. *Control of the leishmaniases*. WHO Technical Report Series 949, 2010 | Annex 3, "WHO recommended case definitions" (pp. 173–175) |
| Leprosy | `13_leprosy_WHO_guidelines_2018_exec_summary.pdf` | WHO. *Guidelines for the diagnosis, treatment and prevention of leprosy*, 2018 (executive summary) | The three cardinal signs |
| Cholera | `14_cholera_GTFCC_surveillance_2024.pdf` | GTFCC. *Public health surveillance for cholera: guidance document 2024* | §I "Case definitions" (p. xi) |
| Trypanosomiasis (Chagas) | `15_chagas_PAHO_guidelines_2019.pdf` | PAHO. *Guidelines for the diagnosis and treatment of Chagas disease*. Washington DC: PAHO; 2019 (Spanish ed. 2018). ISBN 978-92-75-12043-9 | Recommendation 1: two serological tests = "diagnostic gold standard" for chronic infection |
| Viral hemorrhagic fevers | `16_VHF_CDC_CSTE_2025.html` | CDC/CSTE. *Viral hemorrhagic fever, 2025 case definition* (position statement 24-ID-12). https://ndc.services.cdc.gov/case-definitions/viral-hemorrhagic-fever-vhf/ | Laboratory criteria, case classification |
| Scrub typhus | `17_scrub_typhus_DHR-ICMR_rickettsial_2015.pdf` | Rahi M, et al. DHR-ICMR guidelines for diagnosis & management of rickettsial diseases in India. *Indian J Med Res* 2015;141(4):417–422. PMC4510721 | §3.1 case definition; §3.2.1 Weil-Felix |

### Not stored (you need to get these)

| Disease | Citation | Why missing |
|---|---|---|
| Human African trypanosomiasis | CDC. Clinical guidance for human African trypanosomiasis. https://www.cdc.gov/sleeping-sickness/hcp/clinical-guidance/index.html | The CDC site blocks scripted downloads. Save the page from your browser |
| Mycetoma (derived checklist) | Zijlstra EE, et al. Mycetoma: a unique neglected tropical disease. *Lancet Infect Dis* 2016;16(1):100–112 | Paywalled; background only |

The five derived checklists (STH, schistosomiasis, amebiasis, foodborne trematodes, mycetoma) have no official case definition to store. They follow CDC's generic confirmed/probable/suspected structure.

## Method papers (`methods/`)

| File | Citation | What we take from it |
|---|---|---|
| `MedCaseReasoning_Wu2025_arXiv2505.11733.pdf` | Wu K, Wu E, Thapa R, et al. MedCaseReasoning: Evaluating and learning diagnostic reasoning from clinical case reports. arXiv:2505.11733, 2025 | Stage 4 rewrite prompts and rubric; Stage 6 Editor audit |
| `TrialGPT_Jin2024_NatCommun.xml` | Jin Q, et al. Matching patients to clinical trials with large language models. *Nat Commun* 2024;15:9074. doi:10.1038/s41467-024-53081-z | An LLM judging eligibility criteria one by one, citing the sentences it used, reached 87.3% criterion-level accuracy, "close to the expert performance" (Stage 7 design) |
| `MedR-Bench_2025_NatCommun.xml` | Qiu P, Wu C, Liu S, et al. Quantifying the reasoning abilities of LLMs on clinical cases. *Nat Commun* 2025;16:9799. doi:10.1038/s41467-025-64769-1 | Case reports as a source for diagnostic-reasoning benchmarks |
| `Murad2018_case_report_quality_BMJ-EBM.xml` | Murad MH, et al. Methodological quality and synthesis of case series and case reports. *BMJ Evid Based Med* 2018;23(2):60–63 | Quality appraisal of case reports |

Not stored (paywalled, cite only):
- Bonhoeffer J, et al. The Brighton Collaboration: addressing the need for standardized case definitions of adverse events following immunization (AEFI). *Vaccine* 2002;21(3–4):298–302. This is the model for Stage 7: reviewers tick criteria, and an algorithm assigns the level of certainty.
- Botsis T, et al. Text mining for the Vaccine Adverse Event Reporting System: medical text classification using informative feature selection. *J Am Med Inform Assoc* 2011;18(5):631–638. This is automated classification of case reports against Brighton criteria.
