# Case-definition checklists

This is Stage 7 of the pipeline. For each label, an agent ticks every criterion of that disease's checklist as **met / not met / not mentioned**, with the sentence number and an exact quote. A script then applies the rule. The agent never decides the level itself.

## Final version used in Stage 7 (2026-10-16)

The checklists and rules actually run are in `llm/casedef_agent.py` (prompt `casedef-v1-2026-10-16`). Where the per-disease draft sections below differ, the code is authoritative. Changes after checking the sources: cholera, scrub typhus, VHF, leishmaniasis, PCM and dengue.

| Disease | Source | Status |
|---|---|---|
| Tuberculosis | WHO, *Definitions and reporting framework for tuberculosis*, 2013 rev. (2020) | ✅ verbatim |
| Malaria | WHO, *Malaria terminology*, 2021 update ("case, malaria"; "case, presumed"; "malaria infection") | ✅ verbatim |
| Dengue | CDC/CSTE 2015 | ✅ |
| Zika | CDC/CSTE 2016 | ✅ |
| Leptospirosis | CSTE 12-ID-02 | ✅ |
| Melioidosis | CDC/CSTE 2012 | ✅ |
| Scabies | IACS 2020 (Engelman, BJD 183:808–820) | ✅ |
| Talaromycosis, Paracoccidioidomycosis | EORTC/MSGERC 2020 (Donnelly, CID 71:1367–1376) | ✅ |
| Leishmaniasis | WHO TRS 949 (2010), Annex 3 (VL, PKDL, CL, MCL) | ✅ verbatim |
| Leprosy | WHO 2018 guidelines (three cardinal signs) | ✅ verbatim |
| Cholera | GTFCC 2024 surveillance guidance (suspected / confirmed only) | ✅ verbatim |
| Viral hemorrhagic fevers | CDC/CSTE 2025 (24-ID-12): suspect / confirmed only | ✅ verbatim |
| Scrub typhus | DHR-ICMR 2015 (Rahi, IJMR 141:417–422), §3.1 | ✅ verbatim |
| Trypanosomiasis | PAHO 2019 (Chagas: two serologies = "diagnostic gold standard", Recommendation 1); CDC (HAT: microscopy; serology not confirmatory) | ✅ Chagas verbatim; 🟡 HAT (CDC web page, not stored) |
| Neurocysticercosis | Del Brutto 2017 (J Neurol Sci 372:202–210), Table 1 | ✅ verbatim (all items and both rule sets match) |
| Echinococcosis | Brunetti / WHO-IWGE 2010 (Acta Trop 114:1–16), §3.3 C (CE) and §4.4.1 C (AE) | ✅ verbatim |
| STH, Schistosomiasis, Amebiasis, Foodborne trematodes, Mycetoma | No formal case definition: CDC generic structure with standard diagnostic tests | 🔶 derived |

Fixes after checking the sources:
- **Cholera:** GTFCC defines only suspected and confirmed cases; the rapid test classifies outbreaks, not cases. The draft "probable (RDT)" level is removed. Suspected = acute watery diarrhoea with severe dehydration, or during an outbreak.
- **VHF:** CSTE 2025 has only suspect and confirmed. IgM ELISA is now confirmatory; antigen detection is not listed (recorded, gives "possible" only).
- **Scrub typhus:** an eschar only makes a suspected case (ICMR §3.1.1). Weil-Felix ≥1:80 alone is "possible infection" (ICMR §3.2.1). IgM ELISA → probable.
- **Leishmaniasis:** separate rules for VL, CL/MCL and PKDL, as in TRS 949.
- **PCM:** the Brazilian-consensus serology route could not be verified. PCM follows EORTC strictly: serology is recorded but never above "possible".

### Choices where the source is unclear (cautious reading used)

Each choice is a flag in `CAUTIOUS` in the code. The liberal reading is computed for every case as a sensitivity analysis (`common_level_liberal`).

| Flag | Question | Cautious reading (used) | Liberal reading (reported alongside) |
|---|---|---|---|
| `tb_tissue_afb_confirms` | WHO says "positive by smear microscopy". Is acid-fast bacilli in a **tissue section** a smear? | No: tissue AFB can be non-tuberculous mycobacteria. Counts as clinical diagnosis (probable) when a clinician treated TB. | Yes → confirmed |
| `dengue_single_igm_confirms` | Single positive IgM | Probable (WHO 2009; IgM cross-reacts with other flaviviruses) | Confirmed (CSTE 2015 when no other flavivirus is mentioned) |
| `leprosy_cardinal_sign_confirms` | WHO accepts one cardinal sign as a full diagnosis | Mapped to probable: no bacteriological proof | Confirmed |
| `leprosy_tissue_afb_confirms` | AFB in a skin or nerve biopsy (WHO names the slit-skin smear) | Probable, same reasoning as TB | Confirmed |
| `echino_histology_confirms` | Is cyst-wall (laminated layer) histology a confirmed case? | **Resolved: no.** Brunetti 2010 confirms CE only by protoscoleces/their components in cyst contents (microscopy or molecular) or ultrasound change; histopathology confirms only alveolar echinococcosis. | Same (no longer a choice) |
| `leish_vl_serology_confirms` | WHO counts clinical signs + positive serology as a VL case | Probable on our common scale (no parasite shown) | Confirmed |
| `leish_cl_pcr_confirms` | PCR is not in the WHO CL definition | Probable | Confirmed |

Other rules applied the same way everywhere:
- A positive laboratory test without the definition's clinical criteria documented → possible, never confirmed (and never "insufficient"; added in v2 after the pilot).
- Derived checklists (v2): "compatible clinical findings" and "exposure" are separate items. Probable = specific serology + compatible clinical findings; exposure is recorded but not required, since case reports often omit it.
- v2 prompt: an item with several parts is met only when every part is stated (e.g. *V. cholerae* without a serogroup does not meet "O1 or O139"); in neurocysticercosis each lesion counts for one imaging criterion only.
- Scabies cases that are crusted, bullous, immunocompromised or elderly/bedridden are still graded but tagged `outside_definition_scope` (IACS).
- Extra labels from `llm/label_additions.jsonl` (20 diseases in 19 cases that the labeller named but the keyword stage never made candidates) are checked too.

## Verification status

| Mark | Meaning |
|---|---|
| ✅ | Wording checked against the official or primary text |
| 🟡 | Structure checked; some items taken from a secondary source or from memory. **Verify against the paper before use** |
| 🔶 | No single formal case definition exists. Criteria are built on CDC's generic structure (laboratory-confirmed / probable / suspected) from standard diagnostic methods. **Must be presented as "derived"** |

## Common scale

This scale is used for the cross-disease chart. Each disease also keeps its own official level names.

| Common level | Meaning |
|---|---|
| **Confirmed** | The disease's own confirmatory criteria are met (usually the organism is shown) |
| **Probable** | Supportive laboratory or clinical criteria of the official definition are met |
| **Possible** | Only the clinical / exposure criteria are met |
| **Insufficient information** | The report does not document enough to meet any level (Brighton level 4). This does **not** mean the diagnosis is wrong |

## General rules for ticking (same for every disease)

- **met:** the text states the finding was positive **in this patient, in this episode**.
- **not met:** the text states the test was done and was negative or normal.
- **not mentioned:** the text doesn't say.
- A past or healed infection, a planned test, or a test on another person is **never** "met".
- Every "met" needs a sentence number and an exact quote.
- **J** marks criteria that need clinical judgment. Agreement on these is reported separately.

---

## 1. Tuberculosis ✅

**Source:** WHO, *Definitions and reporting framework for tuberculosis*, 2013 revision (updated Dec 2014 and Jan 2020), WHO/HTM/TB/2013.2, §A.1.

Verbatim from the source:
> "A bacteriologically confirmed TB case is one from whom a biological specimen is positive by smear microscopy, culture or WRD (such as Xpert MTB/RIF)."
> "A clinically diagnosed TB case is one who does not fulfil the criteria for bacteriological confirmation but has been diagnosed with active TB by a clinician or other medical practitioner who has decided to give the patient a full course of TB treatment. This definition includes cases diagnosed on the basis of X-ray abnormalities or suggestive histology and extrapulmonary cases without laboratory confirmation."

| ID | Criterion |
|---|---|
| T1 | A biological specimen is positive by smear microscopy (acid-fast bacilli) |
| T2 | Culture grew *M. tuberculosis* (complex) |
| T3 | WHO-recommended rapid / molecular test positive for *M. tuberculosis* (e.g. Xpert MTB/RIF, other NAAT/PCR) |
| T4 | Diagnosed with active TB by a clinician who decided to give a full course of TB treatment (includes X-ray abnormalities, suggestive histology, extrapulmonary TB without laboratory confirmation) |

**Rule:**
- T1 or T2 or T3 → **Bacteriologically confirmed** (Confirmed).
- Otherwise T4 → **Clinically diagnosed** (Probable).
- Otherwise → Insufficient.

**Decision needed:** AFB seen on a *tissue* stain (Ziehl-Neelsen on biopsy). Count it as T1, since WHO says "a biological specimen … positive by smear microscopy"? Proposed: yes.

---

## 2. Malaria 🟡

**Source:** WHO, *Malaria terminology* (2021 update). Definitions stated from memory; verify the wording.
- Confirmed malaria = parasite detected by microscopy, a rapid diagnostic test or a molecular test.
- Suspected malaria = illness suspected by a health worker to be due to malaria.

| ID | Criterion |
|---|---|
| M1 | *Plasmodium* seen on blood film microscopy |
| M2 | Malaria rapid diagnostic test (antigen) positive |
| M3 | Molecular test (PCR) positive for *Plasmodium* |
| M4 | Clinician suspected malaria and treated it as malaria |

**Rule:**
- Any of M1–M3 → **Confirmed**.
- Otherwise M4 → **Suspected** (Possible).
- Otherwise → Insufficient.

---

## 3. Dengue ✅

**Source:** CDC/CSTE, *Dengue virus infections, 2015 case definition* (NNDSS).

| ID | Criterion |
|---|---|
| D0 | Clinical: fever plus ≥1 of nausea/vomiting, rash, aches and pains, positive tourniquet test, leukopenia (WBC < 5,000/mm³), or any warning sign of severe dengue |
| D1 | DENV nucleic acid detected (RT-PCR) in blood, CSF, other body fluid or tissue |
| D2 | DENV antigen in tissue (immunofluorescence or immunohistochemistry) |
| D3 | NS1 antigen positive in serum/plasma |
| D4 | DENV isolated in cell culture |
| D5 | IgM seroconversion between acute and convalescent specimens |
| D6 | IgG seroconversion or ≥4-fold titre rise, confirmed by neutralisation testing |
| D7 | IgM anti-DENV positive (single specimen) |
| D8 | J: Evidence of another flavivirus transmission, co-infection or recent flavivirus vaccination |
| D9 | Epidemiological link: travel to or residence in a dengue-endemic area within 2 weeks before onset, or contact with a dengue case |

**Rule:**
- D0 and any of D1–D6 → **Confirmed**.
- D0 and D7:
  - without D8 → **Confirmed**, per CSTE;
  - with D8 → **Probable**.
- D0 and D9 → **Suspected** (Possible).
- Otherwise → Insufficient.

**Decision needed:** case reports rarely say whether other flaviviruses circulate. Choose one:
- (a) Follow CSTE: IgM alone = confirmed unless the text mentions D8.
- (b) Follow WHO 2009: single IgM = probable.

Proposed: (b), the conservative choice, with (a) reported as a sensitivity analysis.

---

## 4. Zika Virus ✅

**Source:** CDC/CSTE, *Zika virus disease and Zika virus infection, 2016 case definition* (NNDSS). The congenital and non-congenital variants share the same laboratory logic.

| ID | Criterion |
|---|---|
| Z1 | Zika virus detected by culture, viral antigen or viral RNA (RT-PCR) in any specimen (for congenital cases: fetal tissue, cord blood, amniotic fluid, or neonatal specimens within 2 days of birth) |
| Z2 | Zika IgM positive **and** Zika neutralising antibody positive **and** dengue neutralising antibody negative |
| Z3 | Zika IgM positive with neutralising antibody positive to both Zika and dengue/other flaviviruses, **or** Zika IgM positive with dengue IgM negative and no neutralisation test |
| Z4 | Clinical criteria of Zika disease, or congenital Zika syndrome criteria |
| Z5 | Epidemiological link (residence in or travel to an area with Zika transmission; sexual contact; mother's exposure for congenital cases) |

**Rule:**
- Z1 or Z2 → **Confirmed**.
- Otherwise Z3 and Z5 → **Probable**.
- Otherwise Z4 and Z5 → Possible. This is not a CSTE level; it is our common-scale mapping.
- Otherwise → Insufficient.

---

## 5. Leptospirosis ✅

**Source:** CSTE position statement 12-ID-02 (adopted 2013), §VII.

| ID | Criterion |
|---|---|
| L0 | Clinical: history of fever within 2 weeks plus ≥2 of myalgia, headache, jaundice, conjunctival suffusion without purulent discharge, rash; **or** ≥1 of aseptic meningitis, GI symptoms, pulmonary complications, cardiac arrhythmia/ECG abnormality, renal insufficiency, haemorrhage, jaundice with acute renal failure |
| L1 | *Leptospira* isolated from a clinical specimen |
| L2 | ≥4-fold rise in agglutination titre between acute and convalescent sera |
| L3 | *Leptospira* demonstrated in tissue by direct immunofluorescence |
| L4 | MAT titre ≥ 800 in one or more sera |
| L5 | Pathogenic *Leptospira* DNA detected (e.g. PCR) |
| L6 | MAT titre ≥ 200 but < 800 |
| L7 | Anti-*Leptospira* antibodies by indirect immunofluorescence |
| L8 | *Leptospira* seen by dark-field microscopy |
| L9 | IgM against *Leptospira* in acute-phase serum |
| L10 | Epidemiological link to an exposure event with confirmed cases |

**Rule:**
- L0 and any of L1–L5 → **Confirmed**.
- L0 and (any of L6–L9, or L10) → **Probable**.
- Otherwise → Insufficient.

---

## 6. Melioidosis ✅

**Source:** CDC/CSTE, *Melioidosis, 2012 case definition* (NNDSS).

| ID | Criterion |
|---|---|
| B1 | *B. pseudomallei* isolated from a clinical specimen |
| B2 | ≥4-fold rise in *B. pseudomallei* antibody titre (IHA) |
| B3 | *B. pseudomallei* DNA detected (e.g. PCR) |
| B4 | Clinically compatible illness (localised, pulmonary, bloodstream or disseminated infection) |
| B5 | Travel to or residence in an endemic region, or other known exposure |

**Rule:**
- B1 → **Confirmed**.
- Otherwise B4 and (B2 or B3) and B5 → **Probable**.
- Otherwise → Insufficient.

**Note:** CDC classes PCR as *probable* for melioidosis, unlike most other diseases here.

---

## 7. Scabies ✅

**Source:** Engelman D et al., *The 2020 International Alliance for the Control of Scabies Consensus Criteria for the Diagnosis of Scabies*, Br J Dermatol 2020;183(5):808–820 (PMC7687112).

| ID | Criterion |
|---|---|
| A1 | Mites, eggs or faecal pellets seen on light microscopy of skin samples |
| A2 | Mites, eggs or faecal pellets seen on the individual with a high-powered imaging device |
| A3 | Mite seen on dermoscopy |
| B1 | Scabies burrows |
| B2 | Typical lesions on the male genitalia |
| B3 | Typical lesions in a typical distribution |
| C2 | J: Atypical lesions or atypical distribution |
| H1 | Itch |
| H2 | Positive contact history (close contact with an itchy person or one with typical lesions) |

**Rule:**
- Any of A1–A3 → **Confirmed** (level A).
- Otherwise B1 or B2, or (B3 and H1 and H2) → **Clinical** (Probable, level B).
- Otherwise (B3 and (H1 or H2)) or (C2 and H1 and H2) → **Suspected** (Possible, level C).
- Otherwise → Insufficient.

**Note:** IACS says the criteria are not intended for crusted or bullous scabies, immunocompromised people, or elderly/bedridden people. Such cases are tagged `outside_definition_scope`.

---

## 8. Talaromycosis ✅ and 9. Paracoccidioidomycosis ✅ / 🟡

**Source:** Donnelly JP et al., EORTC/MSGERC 2020 consensus definitions, Clin Infect Dis 2020;71(6):1367–1376 (PMC7486838), Tables 1 and 3, endemic mycoses. Both *Talaromyces marneffei* and *Paracoccidioides* are covered.

| ID | Criterion |
|---|---|
| F1 | Histopathology or direct microscopy of a specimen from an affected site shows the distinctive form of the fungus |
| F2 | Culture of the fungus from a specimen from an affected site |
| F3 | Blood culture yields the fungus |
| F4 | Geographic or occupational exposure to the fungus (including remote) and a compatible clinical illness |
| F5 | (PCM only) 🟡 Specific serology positive (e.g. immunodiffusion) |

**Rule:**
- Any of F1–F3 → **Proven** (Confirmed).
- PCM only: otherwise F4 and F5 → Probable 🟡. EORTC gives **no** serological criterion for *P. brasiliensis* or *T. marneffei* ("no approved serologic tests"). The PCM serology route comes from the Brazilian consensus (Shikanai-Yasuda et al. 2017) and needs verification.
- Otherwise → Insufficient.

**Decision needed:** talaromycosis antigen tests (e.g. Mp1p) are not EORTC-approved. Proposed: record them, but do not let them change the level.

---

## 10. Neurocysticercosis 🟡

**Source:** Del Brutto OH et al., *Revised diagnostic criteria for neurocysticercosis*, J Neurol Sci 2017;372:202–210.
- **Checked:** the categories, the neuroimaging criteria and the certainty rules, via Guzman & Garcia, Res Rep Trop Med 2021;12:197–203.
- **From memory:** the clinical/exposure items. **Verify against Table 1 of the original.**

| ID | Criterion | Group |
|---|---|---|
| N-A1 | Histological demonstration of the parasite from a biopsy of a brain or spinal cord lesion | Absolute |
| N-A2 | Cystic lesion showing the scolex on CT or MRI | Absolute |
| N-A3 | Direct visualisation of subretinal parasites by fundoscopy | Absolute |
| N-M1 | Cystic lesions without a discernible scolex | Major neuroimaging |
| N-M2 | Enhancing lesions | Major neuroimaging |
| N-M3 | Multilobulated cystic lesions in the subarachnoid space | Major neuroimaging |
| N-M4 | Typical parenchymal brain calcifications | Major neuroimaging |
| N-K1 | Resolution of cystic lesions after cysticidal drug therapy | Confirmative neuroimaging |
| N-K2 | Spontaneous resolution of single small enhancing lesions | Confirmative neuroimaging |
| N-K3 | Migration of ventricular cysts on sequential imaging | Confirmative neuroimaging |
| N-m1 | Obstructive hydrocephalus or abnormal enhancement of the basal leptomeninges | Minor neuroimaging |
| N-E1 | 🟡 Specific anticysticercal antibodies or cysticercal antigens by well-standardised tests | Major clinical/exposure |
| N-E2 | 🟡 Cysticercosis outside the CNS | Major clinical/exposure |
| N-E3 | 🟡 Household contact with *T. solium* infection | Major clinical/exposure |
| N-E4 | 🟡 Clinical manifestations suggestive of neurocysticercosis | Minor clinical/exposure |
| N-E5 | 🟡 Coming from or living in an area where cysticercosis is endemic | Minor clinical/exposure |
| N-X | J: Other pathologies producing similar imaging excluded | — |

**Rule: Definitive (Confirmed)** if any of:
1. any absolute criterion;
2. ≥2 major neuroimaging + any clinical/exposure;
3. 1 major neuroimaging + 1 confirmative + any clinical/exposure;
4. 1 major neuroimaging + 2 clinical/exposure (including ≥1 major) + N-X.

**Rule: Probable** if any of:
1. 1 major neuroimaging + any 2 clinical/exposure;
2. 1 minor neuroimaging + ≥1 major clinical/exposure.

Otherwise → Insufficient.

---

## 11. Echinococcosis 🟡

**Source:** Brunetti E, Kern P, Vuitton DA; WHO-IWGE Writing Panel, *Expert consensus for the diagnosis and treatment of cystic and alveolar echinococcosis in humans*, Acta Trop 2010;114:1–16.

- **Checked (verbatim):** possible and probable.
  - Possible: "Any patient with a clinical or epidemiological history, and imaging findings or serology positive for CE."
  - Probable: "Any patient with the combination of clinical history, epidemiological history, imaging findings and serology positive for CE on two tests."
- **From memory:** the confirmed-case wording. Verify §3.3.4.

| ID | Criterion |
|---|---|
| E1 | Clinical history compatible with CE |
| E2 | Epidemiological history (residence or exposure in an endemic area, dogs, livestock) |
| E3 | Imaging findings of an echinococcal cyst (US / CT / MRI) |
| E4 | Serology positive for CE (one test) |
| E5 | Serology positive on two tests |
| E6 | 🟡 Protoscoleces or their components (e.g. hooklets) shown by direct microscopy or molecular biology in cyst contents (percutaneous aspiration or surgery) |
| E7 | 🟡 Characteristic change in ultrasound appearance over time (e.g. CE1 → CE3a after endocyst detachment; CE2/CE3b → CE4 solidification), spontaneous or after albendazole |
| E8 | 🟡 Histopathology showing the cyst's laminated / germinal layer |
| E9 | (Alveolar only) Histopathology compatible with AE and/or *E. multilocularis* DNA detected |

**Rule:**
- (E1 or E2) and (E3 or E4) and (E6 or E7, or E8 if confirmed) → **Confirmed**.
- Otherwise E1 and E2 and E3 and E5 → **Probable**.
- Otherwise (E1 or E2) and (E3 or E4) → **Possible**.
- Otherwise → Insufficient.
- For AE: probable criteria + E9 → Confirmed.

**Decision needed:** whether E8 (cyst wall histology after surgery, which is very common in our cases) counts as confirmation. Check §3.3.4 of Brunetti 2010.

---

## 12. Leishmaniasis 🟡

**Source:** WHO Expert Committee, *Control of the leishmaniases*, WHO Technical Report Series 949 (2010). Taken from secondary sources; **verify against TRS 949.**

| ID | Criterion |
|---|---|
| Le1 | Amastigotes seen on smear or histology (spleen, bone marrow or lymph-node aspirate; skin or mucosal lesion) |
| Le2 | *Leishmania* grown in culture |
| Le3 | *Leishmania* DNA detected (PCR) |
| Le4 | (VL) Serology positive (rK39 rapid test, DAT, IFAT, ELISA) |
| Le5 | (VL) Clinical: fever > 2 weeks with splenomegaly and/or weight loss in a person from an endemic area |
| Le6 | (CL/MCL) Typical skin or mucosal lesion in a person exposed in an endemic area |

**Rule:**
- Any of Le1–Le3 → **Confirmed**.
- Otherwise (VL) Le5 and Le4 → **Probable**. WHO elimination programmes count rK39 + clinical as confirmed; to decide.
- Otherwise Le5 or Le6 → **Suspected** (Possible).
- Otherwise → Insufficient.

---

## 13. Leprosy 🟡

**Source:** WHO, *Guidelines for the diagnosis, treatment and prevention of leprosy* (2018). Cardinal signs stated from memory; verify the wording.

| ID | Criterion |
|---|---|
| Lp1 | Definite loss of sensation in a pale (hypopigmented) or reddish skin patch (cardinal sign 1) |
| Lp2 | Thickened or enlarged peripheral nerve with loss of sensation and/or weakness of the muscles it supplies (cardinal sign 2) |
| Lp3 | Acid-fast bacilli in a slit-skin smear (cardinal sign 3) |
| Lp4 | Acid-fast bacilli / *M. leprae* in a skin or nerve biopsy |
| Lp5 | *M. leprae* DNA detected (PCR) |
| Lp6 | J: Histopathology compatible with leprosy without bacilli seen (e.g. granulomas around nerves) |

**Rule:**
- Any of Lp3–Lp5 → **Confirmed**.
- Otherwise Lp1 or Lp2 or Lp6 → **Probable**. Note: WHO itself accepts one cardinal sign as a full diagnosis. Mapping clinical diagnosis to "Probable" is **our** common-scale choice and must be stated.
- Otherwise → Insufficient.

---

## 14. Cholera 🟡

**Source:** GTFCC, *Public health surveillance for cholera: guidance document* (2024). Structure from GTFCC training material; verify against the PDF.

| ID | Criterion |
|---|---|
| Ch1 | *V. cholerae* O1 or O139 isolated by culture (including seroagglutination) |
| Ch2 | *V. cholerae* O1/O139 detected by PCR |
| Ch3 | Toxigenicity shown (e.g. *ctx* PCR) |
| Ch4 | Cholera rapid diagnostic test positive |
| Ch5 | Acute watery diarrhoea (with severe dehydration or death, outside an outbreak; any AWD during an outbreak) |

**Rule:**
- Ch1 or Ch2 → **Confirmed**. GTFCC also requires Ch3 when there is no known outbreak. Our class definition already requires toxigenic O1/O139.
- Otherwise Ch5 and Ch4 → **Probable** (RDT-positive suspected case).
- Otherwise Ch5 → **Suspected** (Possible).
- Otherwise → Insufficient.

---

## 15. Trypanosomiasis 🟡

**Source:** WHO/PAHO diagnostic standards for Chagas disease and WHO standards for human African trypanosomiasis. **Not yet verified against a primary document.**

| ID | Criterion |
|---|---|
| Tr1 | Trypanosomes seen by microscopy (blood, lymph-node aspirate, CSF, tissue) |
| Tr2 | *Trypanosoma* DNA detected (PCR) |
| Tr3 | (Chagas, chronic) Positive results on **two** serological tests based on different antigens or techniques |
| Tr4 | Single positive serological test (Chagas serology; CATT or other HAT serology) |
| Tr5 | Compatible clinical picture (e.g. Chagas cardiomyopathy or megaviscera; HAT neurological stage) with exposure |

**Rule:**
- Tr1 or Tr2 → **Confirmed**.
- Chronic Chagas: Tr3 → **Confirmed** (the standard diagnosis).
- Otherwise Tr4 and Tr5 → **Probable**.
- Otherwise Tr5 → **Possible**.
- Otherwise → Insufficient.

---

## 16. Viral Hemorrhagic Fevers 🟡

**Source:** CDC/CSTE viral hemorrhagic fever case definition and WHO Ebola/Marburg case definitions. **Verify.**

| ID | Criterion |
|---|---|
| V1 | Virus RNA detected (RT-PCR) |
| V2 | Viral antigen detected |
| V3 | Virus isolated in culture |
| V4 | Specific IgM, or IgG seroconversion |
| V5 | Clinically compatible illness with an epidemiological link (contact, outbreak, endemic exposure) |

**Rule:**
- Any of V1–V4 → **Confirmed**.
- Otherwise V5 → **Probable**.
- Otherwise → Insufficient.

---

## 17. Scrub Typhus 🟡

**Source:** Rahi M et al., *DHR-ICMR guidelines for diagnosis & management of rickettsial diseases in India*, Indian J Med Res 2015;141:417–422. From memory; **verify.**

| ID | Criterion |
|---|---|
| S1 | *O. tsutsugamushi* DNA detected (PCR) or isolated |
| S2 | ≥4-fold rise in IFA/IIP titre on paired sera |
| S3 | Single positive IgM ELISA / IFA above the stated cut-off |
| S4 | Eschar |
| S5 | Acute febrile illness compatible with scrub typhus, with exposure |
| S6 | Weil-Felix OX-K positive (low specificity) |

**Rule:**
- S1 or S2 → **Confirmed**.
- Otherwise S5 and (S3 or S4) → **Probable**.
- Otherwise S5 and S6 → **Possible**.
- Otherwise → Insufficient.

---

## 18. Soil-Transmitted Helminths 🔶

**Derived**, using CDC's generic structure and standard parasitological diagnosis.

| ID | Criterion |
|---|---|
| H1 | Eggs or larvae of *Ascaris*, *Trichuris*, hookworm or *Strongyloides* seen in stool or another specimen |
| H2 | Adult worms seen (passed, endoscopy, surgery, imaging showing worms) |
| H3 | Species-specific PCR positive |
| H4 | *Strongyloides* serology positive |
| H5 | Compatible clinical picture or eosinophilia with exposure |

**Rule:**
- Any of H1–H3 → **Confirmed**.
- Otherwise H4 and H5 → **Probable**.
- Otherwise H5 → **Possible**.
- Otherwise → Insufficient.

---

## 19. Schistosomiasis 🔶

**Derived.**

| ID | Criterion |
|---|---|
| Sc1 | *Schistosoma* eggs in stool, urine or a tissue biopsy |
| Sc2 | Circulating schistosome antigen (CCA/CAA) or *Schistosoma* PCR positive |
| Sc3 | *Schistosoma* serology positive |
| Sc4 | Compatible clinical or imaging findings with freshwater exposure in an endemic area |

**Rule:**
- Sc1 or Sc2 → **Confirmed**.
- Otherwise Sc3 and Sc4 → **Probable**.
- Otherwise Sc4 → **Possible**.
- Otherwise → Insufficient.

---

## 20. Amebiasis 🔶

**Derived.**

| ID | Criterion |
|---|---|
| Am1 | *E. histolytica* trophozoites seen in tissue or abscess material, or haematophagous trophozoites in stool |
| Am2 | *E. histolytica*-specific antigen or PCR positive |
| Am3 | J: *Entamoeba* cysts/trophozoites seen without species distinction (microscopy cannot separate *E. histolytica* from *E. dispar*) |
| Am4 | Anti-amoebic serology positive |
| Am5 | Compatible illness (dysentery/colitis, liver abscess) |

**Rule:**
- Am1 or Am2 → **Confirmed**.
- Otherwise Am5 and (Am4 or Am3) → **Probable**.
- Otherwise Am5 → **Possible**.
- Otherwise → Insufficient.

---

## 21. Foodborne Trematodes 🔶

**Derived.**

| ID | Criterion |
|---|---|
| Ft1 | Eggs of *Fasciola*, *Clonorchis*, *Opisthorchis* or *Paragonimus* in stool, sputum, bile or duodenal fluid |
| Ft2 | Adult flukes recovered (ERCP, surgery, biopsy) |
| Ft3 | Species-specific PCR positive |
| Ft4 | Specific serology positive |
| Ft5 | Compatible clinical or imaging findings with exposure (raw freshwater fish, crabs, watercress) |

**Rule:**
- Any of Ft1–Ft3 → **Confirmed**.
- Otherwise Ft4 and Ft5 → **Probable**.
- Otherwise Ft5 → **Possible**.
- Otherwise → Insufficient.

---

## 22. Mycetoma 🔶

**Derived**, after Zijlstra EE et al., *Mycetoma: a unique neglected tropical disease*, Lancet Infect Dis 2016 (from memory; verify).

| ID | Criterion |
|---|---|
| My1 | Grains identified to organism level by culture or molecular methods |
| My2 | Histopathology showing grains with fungal hyphae or actinomycete filaments |
| My3 | Grains seen (unidentified) |
| My4 | Clinical triad: painless subcutaneous swelling, multiple sinuses, discharge |

**Rule:**
- My1 or My2 → **Confirmed**.
- Otherwise My4 and My3 → **Probable**.
- Otherwise My4 → **Possible**.
- Otherwise → Insufficient.

---

## Still to verify before Stage 7 is built

| Item | Needs |
|---|---|
| Del Brutto 2017, Table 1 (NCC clinical/exposure items) | Full text (paywalled: J Neurol Sci) |
| Brunetti 2010, §3.3.4 (CE confirmed case; histopathology?) | Full text (paywalled: Acta Trop) |
| WHO TRS 949 (leishmaniasis case definitions) | WHO PDF |
| WHO 2018 leprosy guidelines (cardinal signs wording) | WHO PDF |
| WHO malaria terminology 2021 | WHO PDF |
| GTFCC 2024 cholera guidance | PDF (public) |
| Chagas / HAT, VHF, scrub typhus sources | Primary documents |
| Brazilian PCM consensus 2017 (serology) | Full text |

## Decisions needed from the owner

1. **TB:** does AFB seen on a tissue stain count as smear microscopy (T1)?
2. **Dengue:** is a single IgM Confirmed (CSTE) or Probable (WHO 2009)?
3. **Leprosy:** map WHO clinical diagnosis to Probable?
4. **Echinococcosis:** does cyst-wall histopathology count as confirmation?
5. **Scabies:** tag crusted/bullous cases as outside IACS scope?
6. **Five derived checklists** (STH, schistosomiasis, amebiasis, foodborne trematodes, mycetoma): acceptable if labelled "derived"?
