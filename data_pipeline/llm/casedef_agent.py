#!/usr/bin/env python3
"""
Stage 7: case-definition checklist.

For every label of a case, an agent ticks each criterion of that disease's published case
definition as met / not_met / not_mentioned, with the line it read it in (S = case-text
sentence, C = figure caption) and an exact quote.  The agent never decides the level.  This
script checks the quotes and applies the published rule, giving the disease's own level
(e.g. "Bacteriologically confirmed") and a common level: confirmed / probable / possible /
insufficient.  This follows the Brighton Collaboration approach (Bonhoeffer et al., Vaccine
2002), where reviewers tick criteria and an algorithm assigns the level of certainty.

Where a source is unclear, the rule takes the cautious reading (CAUTIOUS below); the liberal
reading is computed too and reported as a sensitivity analysis.  Sources and verification
status are in llm/case_definitions_draft.md.

Labels checked: `present` in partA_final.jsonl plus llm/label_additions.jsonl.

    python3 llm/casedef_agent.py build --ids llm/css_pilot50_ids.txt --out handoff_casedef/pilot50
    python3 llm/casedef_agent.py check handoff_casedef/pilot50/responses
    python3 llm/casedef_agent.py apply handoff_casedef/pilot50/responses --out llm/casedef_pilot50.jsonl
"""
import argparse, collections, csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mask_regex import sentences  # noqa: E402
from mask_agent import RUNNER_MD as _MASK_RUNNER  # noqa: E402
from rewrite_agent import load_rows, quote_ok, quote_in, norm  # noqa: E402

ADDITIONS = os.path.join(HERE, "label_additions.jsonl")
PROMPT_VERSION = "casedef-v2-2026-10-16"

# --- checklists -----------------------------------------------------------------------------------
# items: (id, criterion).  "J:" marks criteria that need clinical judgment.
# forms: the agent must pick one when the disease has sub-forms with different rules.

CHECKLISTS = {
    "Tuberculosis": {
        "source": "WHO, Definitions and reporting framework for tuberculosis, 2013 revision (updated 2020)",
        "items": [
            ("T1", "Smear microscopy positive for acid-fast bacilli on a specimen such as sputum, other body fluid, pus or aspirate (a smear, not a tissue section)"),
            ("T1b", "Acid-fast bacilli seen in a tissue section (e.g. Ziehl-Neelsen stain of a biopsy or resected specimen)"),
            ("T2", "Culture grew Mycobacterium tuberculosis (complex)"),
            ("T3", "Rapid molecular test positive for M. tuberculosis (e.g. Xpert MTB/RIF, other NAAT/PCR, LAM, sequencing)"),
            ("T4", "A clinician diagnosed active TB and gave or decided to give a full course of TB treatment"),
            ("T5", "Histology suggestive of TB (caseating or necrotising granulomas)"),
        ]},
    "Malaria": {
        "source": "WHO malaria terminology, 2021 update",
        "items": [
            ("M1", "Plasmodium parasites seen on microscopy (blood film, or tissue such as placenta or brain)"),
            ("M2", "Malaria rapid diagnostic test (antigen) positive"),
            ("M3", "Nucleic acid test (e.g. PCR) positive for Plasmodium"),
            ("M4", "Illness suspected by a health worker to be malaria and treated as malaria"),
        ]},
    "Dengue": {
        "source": "CDC/CSTE, Dengue virus infections, 2015 case definition",
        "items": [
            ("D0", "Fever, reported by the patient or a clinician"),
            ("D1", "Dengue virus nucleic acid detected (RT-PCR) in blood, CSF, other body fluid or tissue"),
            ("D2", "Dengue virus antigen detected in tissue (immunofluorescence or immunohistochemistry)"),
            ("D3", "NS1 antigen positive"),
            ("D4", "Dengue virus isolated in cell culture"),
            ("D5", "IgM seroconversion between acute and convalescent specimens"),
            ("D6", "IgG seroconversion or >=4-fold IgG titre rise between paired specimens, confirmed by neutralisation testing"),
            ("D7", "Dengue IgM positive in a single specimen"),
            ("D9", "Travel to or residence in a dengue-endemic area within 2 weeks before onset, or contact with a dengue case"),
        ]},
    "Zika Virus": {
        "source": "CDC/CSTE, Zika virus disease and infection, 2016 case definition",
        "items": [
            ("Z1", "Zika virus detected by culture, viral antigen or viral RNA (RT-PCR) in any specimen (congenital: fetal tissue, cord blood, amniotic fluid, or neonatal specimen within 2 days of birth)"),
            ("Z2", "Zika IgM positive AND Zika neutralising antibody positive AND dengue neutralising antibody negative"),
            ("Z3", "Zika IgM positive, but Z2 is not fully shown (no neutralisation test, neutralising antibodies to both Zika and dengue/other flaviviruses, or the dengue neutralisation result not reported)"),
            ("Z4", "Clinical criteria of Zika disease (e.g. fever, rash, arthralgia, conjunctivitis, Guillain-Barre) or congenital Zika syndrome (e.g. microcephaly, intracranial calcifications)"),
            ("Z5", "Epidemiological link: residence in or travel to an area with Zika transmission, sexual contact, or (congenital) the mother's exposure"),
        ]},
    "Leptospirosis": {
        "source": "CSTE position statement 12-ID-02 (2013), Leptospirosis",
        "items": [
            ("L0", "Fever within 2 weeks plus >=2 of myalgia, headache, jaundice, conjunctival suffusion, rash; or >=1 of aseptic meningitis, GI symptoms, pulmonary complications, cardiac arrhythmia/ECG abnormality, renal insufficiency, haemorrhage, jaundice with acute renal failure"),
            ("L1", "Leptospira isolated from a clinical specimen"),
            ("L2", ">=4-fold rise in agglutination (MAT) titre between acute and convalescent sera"),
            ("L3", "Leptospira demonstrated in tissue by direct immunofluorescence"),
            ("L4", "MAT titre >= 800 in one or more sera"),
            ("L5", "Pathogenic Leptospira DNA detected (e.g. PCR)"),
            ("L6", "MAT titre >= 200 but < 800 in one or more sera"),
            ("L7", "Anti-Leptospira antibodies by indirect immunofluorescence"),
            ("L8", "Leptospira seen by dark-field microscopy"),
            ("L9", "IgM against Leptospira in acute-phase serum (e.g. ELISA, rapid test)"),
            ("L10", "Epidemiological link to an exposure event with confirmed cases"),
        ]},
    "Melioidosis": {
        "source": "CDC/CSTE, Melioidosis, 2012 case definition",
        "items": [
            ("B1", "Burkholderia pseudomallei isolated (culture) from a clinical specimen"),
            ("B2", ">=4-fold rise in B. pseudomallei antibody titre (IHA) between paired sera"),
            ("B3", "B. pseudomallei DNA detected (e.g. PCR)"),
            ("B4", "Clinically compatible illness (localised, pulmonary, bloodstream or disseminated infection)"),
            ("B5", "Travel to or residence in an endemic region, or other known exposure"),
        ]},
    "Scabies": {
        "source": "Engelman D et al., 2020 IACS Consensus Criteria for the Diagnosis of Scabies, Br J Dermatol 2020;183:808-820",
        "items": [
            ("A1", "Mites, eggs or faecal pellets seen on light microscopy of skin samples"),
            ("A2", "Mites, eggs or faecal pellets seen on the patient with a high-powered imaging device"),
            ("A3", "Mite seen on dermoscopy"),
            ("B1", "Scabies burrows"),
            ("B2", "Typical lesions on the male genitalia"),
            ("B3", "Typical lesions in a typical distribution"),
            ("C2", "J: Atypical lesions or atypical distribution"),
            ("H1", "Itch"),
            ("H2", "Positive contact history (close contact with an itchy person or one with typical lesions)"),
            ("X1", "Crusted or bullous scabies, or an immunocompromised, elderly or bedridden patient (outside the IACS criteria's intended scope)"),
        ]},
    "Talaromycosis": {
        "source": "Donnelly JP et al., EORTC/MSGERC 2020 consensus definitions (endemic mycoses), Clin Infect Dis 2020;71:1367-1376",
        "items": [
            ("F1", "Histopathology or direct microscopy of a specimen from an affected site shows the distinctive yeast form (e.g. septate yeast cells)"),
            ("F2", "Talaromyces marneffei grown in culture from a specimen from an affected site"),
            ("F3", "Blood culture grows T. marneffei"),
            ("F4", "Geographic or occupational exposure (including remote) and a compatible clinical illness"),
            ("F5", "Antigen, antibody, PCR or sequencing (e.g. mNGS) positive for T. marneffei"),
        ]},
    "Paracoccidioidomycosis": {
        "source": "Donnelly JP et al., EORTC/MSGERC 2020 consensus definitions (endemic mycoses), Clin Infect Dis 2020;71:1367-1376",
        "items": [
            ("F1", "Histopathology or direct microscopy of a specimen from an affected site shows the distinctive yeast form (multiple budding, 'pilot's wheel')"),
            ("F2", "Paracoccidioides grown in culture from a specimen from an affected site"),
            ("F3", "Blood culture grows Paracoccidioides"),
            ("F4", "Geographic or occupational exposure (including remote) and a compatible clinical illness"),
            ("F5", "Serology (e.g. double immunodiffusion), antigen, PCR or sequencing positive for Paracoccidioides"),
        ]},
    "Neurocysticercosis": {
        "source": "Del Brutto OH et al., Revised diagnostic criteria for neurocysticercosis, J Neurol Sci 2017;372:202-210",
        "items": [
            ("NA1", "Histological demonstration of the parasite from a biopsy of a brain or spinal cord lesion"),
            ("NA2", "Cystic lesion showing the scolex on CT or MRI"),
            ("NA3", "Direct visualisation of subretinal parasites by fundoscopy"),
            ("NM1", "Cystic lesions without a discernible scolex on CT or MRI (each lesion counts for one of NM1-NM4 only)"),
            ("NM2", "Enhancing lesions on CT or MRI"),
            ("NM3", "Multilobulated cystic lesions in the subarachnoid space"),
            ("NM4", "Typical parenchymal brain calcifications"),
            ("NK1", "Resolution of cystic lesions after cysticidal drug therapy"),
            ("NK2", "Spontaneous resolution of single small enhancing lesions"),
            ("NK3", "Migration of ventricular cysts on sequential imaging"),
            ("Nm1", "Obstructive hydrocephalus (symmetric or asymmetric) or abnormal enhancement of the basal leptomeninges"),
            ("NE1", "Specific anticysticercal antibodies or cysticercal antigens detected by well-standardised tests"),
            ("NE2", "Cysticercosis outside the central nervous system"),
            ("NE3", "Household contact with Taenia solium infection"),
            ("NE4", "Clinical manifestations suggestive of neurocysticercosis (e.g. seizures, focal deficits, raised intracranial pressure)"),
            ("NE5", "Coming from or living in an area where cysticercosis is endemic"),
            ("NX", "J: Other pathologies producing similar neuroimaging findings were excluded"),
        ]},
    "Echinococcosis": {
        "source": "Brunetti E, Kern P, Vuitton DA; WHO-IWGE, Expert consensus for the diagnosis and treatment of cystic and alveolar echinococcosis in humans, Acta Trop 2010;114:1-16",
        "forms": ["cystic", "alveolar", "unspecified"],
        "items": [
            ("E1", "Clinical history compatible with echinococcosis (symptoms or signs referable to the cyst, or an incidental mass)"),
            ("E2", "Epidemiological history (residence in or exposure in an endemic area, contact with dogs or livestock)"),
            ("E3", "Imaging findings of an echinococcal cyst or lesion (ultrasound, CT or MRI)"),
            ("E4", "Serology positive for echinococcosis (one test)"),
            ("E5", "Serology positive on two different tests"),
            ("E6", "Protoscoleces or their components (e.g. hooklets) seen by direct microscopy in cyst contents"),
            ("E7", "Characteristic change of the cyst's ultrasound appearance over time (spontaneous or after albendazole)"),
            ("E8", "Histopathology showing the cyst's laminated and/or germinal layer"),
            ("E9", "Histopathology compatible with alveolar echinococcosis"),
            ("E10", "Echinococcus DNA detected (PCR or sequencing) in a clinical specimen"),
        ]},
    "Leishmaniasis": {
        "source": "WHO Expert Committee, Control of the leishmaniases, WHO Technical Report Series 949 (2010), Annex 3",
        "forms": ["visceral", "cutaneous", "mucocutaneous", "PKDL", "unspecified"],
        "items": [
            ("Le1", "Parasites (amastigotes) seen on a stained smear or histology, or Leishmania grown in culture (bone marrow, spleen, liver, lymph node, blood, skin or mucosal lesion)"),
            ("Le2", "Leishmania DNA detected (PCR or related technique)"),
            ("Le3", "Serology positive (IFAT, ELISA, rK39 rapid test, direct agglutination test)"),
            ("Le4", "Visceral signs: prolonged irregular fever, splenomegaly and/or weight loss"),
            ("Le5", "One or more skin lesions (nodule, ulcer) or mucosal lesions"),
            ("Le6", "Patient from a kala-azar-endemic area with multiple hypopigmented macules, papules, plaques or nodules"),
            ("Le7", "The PKDL lesions have no loss of sensation"),
        ]},
    "Leprosy": {
        "source": "WHO, Guidelines for the diagnosis, treatment and prevention of leprosy, 2018",
        "items": [
            ("Lp1", "Definite loss of sensation in a pale (hypopigmented) or reddish skin patch"),
            ("Lp2", "Thickened or enlarged peripheral nerve with loss of sensation and/or weakness of the muscles supplied by that nerve"),
            ("Lp3", "Acid-fast bacilli in a slit-skin smear"),
            ("Lp4", "Acid-fast bacilli / M. leprae seen in a skin or nerve biopsy (tissue section)"),
            ("Lp5", "M. leprae or M. lepromatosis DNA detected (PCR or sequencing)"),
            ("Lp6", "J: Histopathology compatible with leprosy without bacilli seen (e.g. granulomas around nerves)"),
        ]},
    "Cholera": {
        "source": "GTFCC, Public health surveillance for cholera: guidance document, 2024",
        "items": [
            ("Ch1", "Vibrio cholerae O1 or O139 isolated by culture (including seroagglutination)"),
            ("Ch2", "V. cholerae O1 or O139 detected by PCR"),
            ("Ch3", "The strain was shown to be toxigenic (e.g. ctx gene by PCR, cholera toxin)"),
            ("Ch4", "Cholera rapid diagnostic test positive"),
            ("Ch5", "Acute watery diarrhoea (non-bloody liquid stools, >=3 in 24 hours, lasting < 7 days), or death from it"),
            ("Ch6", "Severe dehydration"),
            ("Ch7", "Occurred during a probable or confirmed cholera outbreak in the area"),
        ]},
    "Trypanosomiasis": {
        "source": "PAHO, Guidelines for the diagnosis and treatment of Chagas disease (2018); WHO/CDC guidance for human African trypanosomiasis",
        "forms": ["chagas_acute", "chagas_chronic", "chagas_congenital", "hat_gambiense", "hat_rhodesiense", "unspecified"],
        "items": [
            ("Tr1", "Trypanosomes seen by microscopy (blood, lymph-node aspirate, CSF, tissue, or other specimen)"),
            ("Tr2", "Trypanosoma DNA detected (PCR)"),
            ("Tr3", "Positive results on two serological tests based on different principles or antigens"),
            ("Tr4", "A single positive serological test (e.g. one Chagas ELISA, CATT or other HAT serology)"),
            ("Tr5", "Compatible clinical picture (e.g. Chagas cardiomyopathy, megaoesophagus or megacolon, romana sign; HAT chancre, fever, lymphadenopathy, sleep disturbance, neurological signs) with exposure"),
        ]},
    "Viral Hemorrhagic Fevers": {
        "source": "CDC/CSTE, Viral hemorrhagic fever, 2025 case definition (position statement 24-ID-12)",
        "items": [
            ("V1", "VHF-specific nucleic acid detected by a molecular test (e.g. RT-PCR, NAAT, genome sequencing) in blood, body fluid or tissue"),
            ("V2", "VHF-specific IgM detected by ELISA"),
            ("V3", "Four-fold rise in VHF-specific IgG titre between acute and convalescent samples"),
            ("V4", "VHF virus isolated in cell culture"),
            ("V5", "Acute onset of >=1 compatible finding (fever, headache, muscle or joint pain, weakness, rash, vomiting, diarrhoea, abdominal pain, unexplained bleeding, hiccups, neurological signs, acute hearing loss)"),
            ("V6", "Epidemiological link within the incubation period (contact with a known or suspected case, exposure in an endemic or outbreak area, animal or tick exposure, specimen handling)"),
            ("V7", "VHF viral antigen detected (e.g. antigen ELISA or rapid test)"),
        ]},
    "Scrub Typhus": {
        "source": "Rahi M et al., DHR-ICMR Guidelines for diagnosis & management of rickettsial diseases in India, Indian J Med Res 2015;141:417-422",
        "items": [
            ("S1", "Orientia tsutsugamushi DNA detected by PCR (eschar or whole blood)"),
            ("S2", "Rising antibody titres on acute and convalescent sera by IFA or IPA (indirect immunoperoxidase)"),
            ("S3", "Scrub typhus IgM ELISA positive (e.g. OD > 0.5) or other positive IgM test"),
            ("S4", "Weil-Felix test positive (OX-K, OX-2 or OX-19 titre >= 1:80)"),
            ("S5", "Fever lasting 5 days or more"),
            ("S6", "Eschar"),
            ("S7", "Orientia tsutsugamushi isolated in culture"),
            ("S8", "Fever (any duration)"),
        ]},
    "Soil-Transmitted Helminths": {
        "source": "Derived: CDC generic laboratory-confirmed / probable / suspected structure with standard parasitological diagnosis",
        "items": [
            ("H1", "Eggs or larvae of Ascaris, Trichuris, hookworm or Strongyloides seen in stool or another specimen (including tissue)"),
            ("H2", "Adult worms seen (passed, at endoscopy or surgery, or on imaging)"),
            ("H3", "Species-specific PCR positive"),
            ("H4", "Strongyloides serology positive"),
            ("H5", "Compatible clinical picture (e.g. abdominal pain, diarrhoea, anaemia, intestinal obstruction, larva currens, hyperinfection) or eosinophilia"),
            ("H6", "Exposure: residence in or travel to an endemic area, or soil contact"),
        ]},
    "Schistosomiasis": {
        "source": "Derived: CDC generic laboratory-confirmed / probable / suspected structure with standard parasitological diagnosis",
        "items": [
            ("Sc1", "Schistosoma eggs in stool, urine or a tissue biopsy"),
            ("Sc2", "Circulating schistosome antigen (CCA/CAA) or Schistosoma PCR positive"),
            ("Sc3", "Schistosoma serology positive"),
            ("Sc4", "Compatible clinical or imaging findings (e.g. haematuria, periportal fibrosis, portal hypertension, granulomas, Katayama fever)"),
            ("Sc5", "Freshwater exposure in an endemic area"),
        ]},
    "Amebiasis": {
        "source": "Derived: CDC generic laboratory-confirmed / probable / suspected structure with standard parasitological diagnosis",
        "items": [
            ("Am1", "E. histolytica trophozoites seen in tissue or abscess material, or haematophagous trophozoites in stool"),
            ("Am2", "E. histolytica-specific antigen or PCR positive"),
            ("Am3", "J: Entamoeba cysts or trophozoites seen without species distinction"),
            ("Am4", "Anti-amoebic (E. histolytica) serology positive"),
            ("Am5", "Compatible illness (dysentery or colitis, liver abscess, ameboma, other invasive disease)"),
        ]},
    "Foodborne Trematodes": {
        "source": "Derived: CDC generic laboratory-confirmed / probable / suspected structure with standard parasitological diagnosis",
        "items": [
            ("Ft1", "Eggs of Fasciola, Clonorchis, Opisthorchis or Paragonimus in stool, sputum, bile, duodenal fluid or tissue"),
            ("Ft2", "Adult flukes recovered (ERCP, surgery, biopsy)"),
            ("Ft3", "Species-specific PCR positive"),
            ("Ft4", "Specific serology positive"),
            ("Ft5", "Compatible clinical or imaging findings (e.g. hepatic or biliary lesions, cholangitis, pleuropulmonary disease, eosinophilia)"),
            ("Ft6", "Exposure: eating raw or undercooked freshwater fish, crabs or crayfish, or watercress or other water plants"),
        ]},
    "Mycetoma": {
        "source": "Derived, after Zijlstra EE et al., Mycetoma: a unique neglected tropical disease, Lancet Infect Dis 2016",
        "items": [
            ("My1", "Grains identified to organism level by culture or molecular methods"),
            ("My2", "Histopathology showing grains with fungal hyphae or actinomycete filaments"),
            ("My3", "Grains seen, organism not identified"),
            ("My4", "Clinical triad: painless subcutaneous swelling, multiple sinuses, discharge"),
        ]},
}

# --- rules ----------------------------------------------------------------------------------------
# Each rule gets the set of met item ids, the form, and the choice flags; it returns
# (the disease's own level name, common level).  Common levels: confirmed / probable / possible /
# insufficient.  Where the source is unclear we take the cautious reading by default.

CAUTIOUS = {"tb_tissue_afb_confirms": False, "dengue_single_igm_confirms": False,
            "leprosy_tissue_afb_confirms": False, "leprosy_cardinal_sign_confirms": False,
            "echino_histology_confirms": False, "leish_vl_serology_confirms": False,
            "leish_cl_pcr_confirms": False}
# echino_histology_confirms stays False in both: Brunetti et al. 2010 (sec. 3.3 C) lists only protoscoleces /
# their components (microscopy or molecular) in cyst contents, or ultrasound change, as confirmation for CE
LIBERAL = {k: True for k in CAUTIOUS} | {"echino_histology_confirms": False}

C, P, PO, I = "confirmed", "probable", "possible", "insufficient"
INS = ("Insufficient information", I)


def r_tb(m, f, o):
    if m & {"T1", "T2", "T3"} or ("T1b" in m and o["tb_tissue_afb_confirms"]):
        return "Bacteriologically confirmed", C
    if "T4" in m:
        return "Clinically diagnosed", P
    if m & {"T1b", "T5"}:
        return "Suggestive findings, no clinician diagnosis documented", PO
    return INS


def r_malaria(m, f, o):
    if m & {"M1", "M2", "M3"}:
        return "Confirmed malaria case", C
    if "M4" in m:
        return "Suspected / presumed case", PO
    return INS


def r_dengue(m, f, o):
    lab = m & {"D1", "D2", "D3", "D4", "D5", "D6"}
    if "D0" in m:
        if lab or ("D7" in m and o["dengue_single_igm_confirms"]):
            return "Confirmed", C
        if "D7" in m:
            return "Probable", P
        if "D9" in m:
            return "Suspected", PO
    elif lab or "D7" in m:
        return "Laboratory evidence, clinical criteria not documented", PO
    return INS


def r_zika(m, f, o):
    if m & {"Z1", "Z2"}:
        return "Confirmed", C
    if "Z3" in m and "Z5" in m:
        return "Probable", P
    if "Z4" in m and "Z5" in m:
        return "Clinical and epidemiological criteria only", PO
    return INS


def r_lepto(m, f, o):
    if "L0" in m and m & {"L1", "L2", "L3", "L4", "L5"}:
        return "Confirmed", C
    if "L0" in m and m & {"L6", "L7", "L8", "L9", "L10"}:
        return "Probable", P
    if m & {"L1", "L2", "L3", "L4", "L5"}:
        return "Laboratory evidence, clinical criteria not documented", PO
    return INS


def r_melioid(m, f, o):
    if "B1" in m:
        return "Confirmed", C
    if "B4" in m and m & {"B2", "B3"} and "B5" in m:
        return "Probable", P
    if m & {"B2", "B3"}:
        return "Supportive laboratory evidence only", PO
    return INS


def r_scabies(m, f, o):
    if m & {"A1", "A2", "A3"}:
        return "Confirmed scabies (level A)", C
    if m & {"B1", "B2"} or {"B3", "H1", "H2"} <= m:
        return "Clinical scabies (level B)", P
    if ("B3" in m and m & {"H1", "H2"}) or {"C2", "H1", "H2"} <= m:
        return "Suspected scabies (level C)", PO
    return INS


def r_fungus(m, f, o):
    if m & {"F1", "F2", "F3"}:
        return "Proven", C
    if "F4" in m and "F5" in m:
        return "Exposure, compatible illness and a non-culture test (not an EORTC level)", PO
    return INS


def r_ncc(m, f, o):
    absolute = m & {"NA1", "NA2", "NA3"}
    major = len(m & {"NM1", "NM2", "NM3", "NM4"})
    confirm = len(m & {"NK1", "NK2", "NK3"})
    minor = len(m & {"Nm1"})
    ce_major = len(m & {"NE1", "NE2", "NE3"})
    ce = ce_major + len(m & {"NE4", "NE5"})
    if absolute or (major >= 2 and ce) or (major and confirm and ce) or \
            (major and ce >= 2 and ce_major and "NX" in m):
        return "Definitive", C
    if (major and ce >= 2) or (minor and ce_major):
        return "Probable", P
    if major or minor:
        return "Neuroimaging criteria only", PO
    return INS


def r_echino(m, f, o):
    history = m & {"E1", "E2"}
    image_or_sero = m & {"E3", "E4"}
    proof = m & {"E6", "E7", "E10"} or ("E8" in m and o["echino_histology_confirms"])
    if f == "alveolar" and history and image_or_sero and m & {"E9", "E10"}:
        return "Confirmed (alveolar)", C
    if history and image_or_sero and proof:
        return "Confirmed", C
    if {"E1", "E2", "E3", "E5"} <= m:
        return "Probable", P
    if history and image_or_sero:
        return "Possible", PO
    if m & {"E6", "E8", "E9", "E10"}:
        return "Parasite or histology evidence, clinical/epidemiological history not documented", PO
    return INS


def r_leish(m, f, o):
    para = "Le1" in m
    pcr = "Le2" in m
    if f == "PKDL":
        if "Le6" in m and (para or pcr):
            return "Confirmed PKDL", C
        if "Le6" in m and "Le7" in m:
            return "Probable PKDL", P
        if "Le6" in m:
            return "Clinical PKDL features only", PO
        return INS
    if f in ("cutaneous", "mucocutaneous"):
        if "Le5" in m and (para or (pcr and o["leish_cl_pcr_confirms"])):
            return "Case (parasitological confirmation)", C
        if "Le5" in m and pcr:
            return "PCR-positive lesion (PCR is not in the WHO CL definition)", P
        if f == "mucocutaneous" and "Le5" in m and "Le3" in m:
            return "Case (serological diagnosis, mucocutaneous only)", P
        if "Le5" in m:
            return "Clinical lesion only", PO
        return INS
    # visceral, or unspecified: WHO VL definition
    if "Le4" in m and (para or pcr):
        return "Case (parasitological confirmation)", C
    if "Le4" in m and "Le3" in m:
        return ("Case (serological confirmation)", C) if o["leish_vl_serology_confirms"] else \
               ("Case (serological confirmation)", P)
    if para or pcr:
        return "Parasitological evidence, clinical signs not documented", P
    if "Le4" in m or "Le3" in m:
        return "Clinical signs or serology only", PO
    return INS


def r_leprosy(m, f, o):
    if m & {"Lp3", "Lp5"} or ("Lp4" in m and o["leprosy_tissue_afb_confirms"]):
        return "Bacteriological / molecular confirmation", C
    if m & {"Lp1", "Lp2"}:
        return ("Clinical diagnosis (WHO cardinal sign)", C) if o["leprosy_cardinal_sign_confirms"] else \
               ("Clinical diagnosis (WHO cardinal sign)", P)
    if "Lp4" in m:
        return "Acid-fast bacilli in tissue", P
    if "Lp6" in m:
        return "Compatible histopathology only", PO
    return INS


def r_cholera(m, f, o):
    if m & {"Ch1", "Ch2"}:
        return "Confirmed cholera case", C
    if "Ch5" in m and (m & {"Ch6", "Ch7"} or "Ch4" in m):
        return "Suspected cholera case", PO
    return INS


def r_tryp(m, f, o):
    if m & {"Tr1", "Tr2"}:
        return "Confirmed (parasite or DNA)", C
    if f == "chagas_chronic" and "Tr3" in m:
        return "Confirmed (two serological tests, chronic Chagas)", C
    if f.startswith("chagas") and m & {"Tr3", "Tr4"} and "Tr5" in m:
        return "Serology and compatible clinical picture", P
    if m & {"Tr3", "Tr4", "Tr5"}:
        return "Serology or clinical picture only", PO
    return INS


def r_vhf(m, f, o):
    if m & {"V1", "V2", "V3", "V4"}:
        return "Confirmed", C
    if "V5" in m and "V6" in m:
        return "Suspect", PO
    if "V7" in m:
        return "Antigen only (not CSTE confirmatory evidence)", PO
    return INS


def r_scrub(m, f, o):
    suspected = "S5" in m or ("S6" in m and "S8" in m)
    if m & {"S1", "S2", "S7"}:
        return "Confirmed", C
    if suspected and "S3" in m:
        return "Probable", P
    if suspected and "S4" in m:
        return "Suspected, Weil-Felix positive ('possible infection' per ICMR)", PO
    if suspected:
        return "Suspected / clinical case", PO
    return INS


def r_derived(conf, prob_lab, clin):
    def rule(m, f, o):
        if m & conf:
            return "Laboratory confirmed", C
        if m & prob_lab and clin in m:
            return "Probable", P
        if clin in m:
            return "Suspected", PO
        return INS
    return rule


def r_amoeba(m, f, o):
    if m & {"Am1", "Am2"}:
        return "Laboratory confirmed", C
    if "Am5" in m and m & {"Am3", "Am4"}:
        return "Probable", P
    if "Am5" in m:
        return "Suspected", PO
    return INS


def r_mycetoma(m, f, o):
    if m & {"My1", "My2"}:
        return "Laboratory confirmed", C
    if "My4" in m and "My3" in m:
        return "Probable", P
    if "My4" in m:
        return "Suspected", PO
    return INS


RULES = {"Tuberculosis": r_tb, "Malaria": r_malaria, "Dengue": r_dengue, "Zika Virus": r_zika,
         "Leptospirosis": r_lepto, "Melioidosis": r_melioid, "Scabies": r_scabies,
         "Talaromycosis": r_fungus, "Paracoccidioidomycosis": r_fungus, "Neurocysticercosis": r_ncc,
         "Echinococcosis": r_echino, "Leishmaniasis": r_leish, "Leprosy": r_leprosy,
         "Cholera": r_cholera, "Trypanosomiasis": r_tryp, "Viral Hemorrhagic Fevers": r_vhf,
         "Scrub Typhus": r_scrub,
         "Soil-Transmitted Helminths": r_derived({"H1", "H2", "H3"}, {"H4"}, "H5"),
         "Schistosomiasis": r_derived({"Sc1", "Sc2"}, {"Sc3"}, "Sc4"),
         "Amebiasis": r_amoeba,
         "Foodborne Trematodes": r_derived({"Ft1", "Ft2", "Ft3"}, {"Ft4"}, "Ft5"),
         "Mycetoma": r_mycetoma}
assert set(RULES) == set(CHECKLISTS)


# items that are not laboratory evidence (clinical, exposure, imaging, treatment decision)
NON_LAB = {"Tuberculosis": {"T4"}, "Malaria": {"M4"}, "Dengue": {"D0", "D9"}, "Zika Virus": {"Z4", "Z5"},
           "Leptospirosis": {"L0", "L10"}, "Melioidosis": {"B4", "B5"},
           "Scabies": {"B1", "B2", "B3", "C2", "H1", "H2", "X1"}, "Talaromycosis": {"F4"},
           "Paracoccidioidomycosis": {"F4"},
           "Neurocysticercosis": {"NM1", "NM2", "NM3", "NM4", "NK1", "NK2", "NK3", "Nm1", "NE2", "NE3", "NE4", "NE5", "NX"},
           "Echinococcosis": {"E1", "E2", "E3", "E7"}, "Leishmaniasis": {"Le4", "Le5", "Le6", "Le7"},
           "Leprosy": {"Lp1", "Lp2"}, "Cholera": {"Ch5", "Ch6", "Ch7"}, "Trypanosomiasis": {"Tr5"},
           "Viral Hemorrhagic Fevers": {"V5", "V6"}, "Scrub Typhus": {"S5", "S6", "S8"},
           "Soil-Transmitted Helminths": {"H5", "H6"}, "Schistosomiasis": {"Sc4", "Sc5"}, "Amebiasis": {"Am5"},
           "Foodborne Trematodes": {"Ft5", "Ft6"}, "Mycetoma": {"My4"}}


def classify(disease, met, form, opts=CAUTIOUS):
    official, common = RULES[disease](set(met), form or "unspecified", opts)
    if common == I and set(met) - NON_LAB[disease]:
        # same rule for every disease: a positive test with the other criteria undocumented
        official, common = "Laboratory evidence only, other criteria not documented", PO
    tags = ["outside_definition_scope"] if disease == "Scabies" and "X1" in met else []
    return {"level": official, "common_level": common, "tags": tags}


# --- prompt ---------------------------------------------------------------------------------------

SYSTEM = """You are a clinical epidemiologist applying published case definitions to a case report.

You will get:
  DISEASES    one or more diseases this patient was labelled with, each with its checklist
  SENTENCES   the case text, one numbered sentence per line (S1, S2, ...)
  CAPTIONS    the figure captions of this case, numbered C1, C2, ... (may be empty)

For EVERY item of EVERY disease's checklist, decide one status:
  met            the text states the finding was present or the test was positive, in this
                 patient, in this illness episode
  not_met        the text states the test was done and was negative or normal, or states the
                 finding was absent
  not_mentioned  the text does not say

RULES (no exceptions)
  - Judge only what the SENTENCES and CAPTIONS say about this patient. Do not use outside
    knowledge to fill in a finding the text does not report. Do not infer a test result from the
    diagnosis or from the treatment given.
  - A past or healed infection, an earlier treated episode, a planned or pending test, a test
    on another person, a suspicion, a differential diagnosis or a "rule out" is never "met".
  - Tick each item on its own. If one sentence supports several items, cite it for each.
  - An item with several parts ("with", "and", a named serogroup, species or threshold) is
    "met" only when the text states every part. "Thickened nerve" alone does not meet "thickened
    nerve with loss of sensation"; "V. cholerae" without a serogroup does not meet "V. cholerae
    O1 or O139".
  - When the text reports a finding without naming the test, tick the item that matches what
    was actually done (a smear of pus is not a tissue section; a culture is not a PCR).
  - Items marked "J:" need clinical judgment: tick "met" only when the text supports it
    explicitly.
  - Every "met" and every "not_met" needs "ref" (the line, e.g. "S12" or "C2") and "quote",
    copied from that line character for character. You may shorten a quote with "..." but
    every part between the dots must be exact. Use "ref": "" and "quote": "" for
    not_mentioned.
  - Never decide or state the level of certainty. Only tick the items.
  - If a disease has FORMS, choose the one form the text supports, or "unspecified".
  - "note": anything that made an item hard to tick, in one or two sentences, else "".

Return ONLY this JSON object, no prose, no markdown fences:
{
  "case_id": "<as given>",
  "diseases": [
    {"disease": "<name as given>",
     "form": "<one of the FORMS, or \\"\\" when the disease has no FORMS>",
     "items": [{"id": "<item id>", "status": "met|not_met|not_mentioned",
                "ref": "<S# or C#, or empty>", "quote": "<exact text, or empty>"}],
     "note": "<or empty>"}
  ]
}
Every item id of every checklist must appear exactly once."""


def additions():
    out = collections.defaultdict(list)
    if os.path.exists(ADDITIONS):
        for l in open(ADDITIONS):
            a = json.loads(l)
            out[a["case_id"]].append(a["class"])
    return out


def labels_of(rec, add):
    return list(rec["present"]) + [c for c in add.get(rec["case_id"], []) if c not in rec["present"]]


def captions(rec):
    seen = []
    for im in rec.get("images") or []:
        c = norm(im.get("caption") or "")
        if c and c not in seen:
            seen.append(c)
    return seen


def build_user(rec, labels):
    parts = [f"case_id: {rec['case_id']}", "", "DISEASES:"]
    for d in labels:
        cl = CHECKLISTS[d]
        parts.append(f"\n### {d}")
        if cl.get("forms"):
            parts.append("FORMS: " + " | ".join(cl["forms"]))
        parts += [f"  {i}: {t}" for i, t in cl["items"]]
    parts += ["", "SENTENCES:"] + [f"S{i}: {s}" for i, s in enumerate(sentences(rec["case_text"]), 1)]
    parts += ["", "CAPTIONS:"] + ([f"C{i}: {c}" for i, c in enumerate(captions(rec), 1)] or ["(none)"])
    return "\n".join(parts)


# --- validation -----------------------------------------------------------------------------------

STATUS = {"met", "not_met", "not_mentioned"}
REF_RX = re.compile(r"^([SC])(\d+)$")


def validate(text, rec, labels):
    try:
        j = json.loads(text) if isinstance(text, str) else text
    except Exception as e:
        return False, f"not JSON: {e}"
    if not isinstance(j, dict) or j.get("case_id") != rec["case_id"]:
        return False, "case_id mismatch"
    ds = j.get("diseases")
    if not isinstance(ds, list) or sorted(d.get("disease", "") for d in ds if isinstance(d, dict)) != sorted(labels):
        return False, "diseases do not match the labels given"
    sents, caps = sentences(rec["case_text"]), captions(rec)
    for d in ds:
        cl = CHECKLISTS[d["disease"]]
        forms = cl.get("forms")
        if forms and d.get("form") not in forms:
            return False, f"{d['disease']}: form invalid: {d.get('form')}"
        items = d.get("items")
        if not isinstance(items, list) or sorted(x.get("id", "") for x in items if isinstance(x, dict)) != \
                sorted(i for i, _ in cl["items"]):
            return False, f"{d['disease']}: item ids do not match the checklist"
        for x in items:
            if x.get("status") not in STATUS:
                return False, f"{d['disease']} {x.get('id')}: status invalid"
            if x["status"] == "not_mentioned":
                continue
            mm = REF_RX.match(str(x.get("ref") or ""))
            if not mm:
                return False, f"{d['disease']} {x['id']}: ref missing or invalid"
            kind, n = mm.group(1), int(mm.group(2))
            q = x.get("quote") or ""
            if kind == "S":
                if not 1 <= n <= len(sents) or not quote_in(q, sents, n):
                    return False, f"{d['disease']} {x['id']}: quote not found verbatim in S{n}"
            elif not 1 <= n <= len(caps) or not quote_ok(q, caps[n - 1]):
                return False, f"{d['disease']} {x['id']}: quote not found verbatim in C{n}"
    return True, j


def result(j):
    out = []
    for d in j["diseases"]:
        met = sorted(x["id"] for x in d["items"] if x["status"] == "met")
        cau = classify(d["disease"], met, d.get("form"), CAUTIOUS)
        lib = classify(d["disease"], met, d.get("form"), LIBERAL)
        out.append({"disease": d["disease"], "form": d.get("form", ""), "met": met,
                    "not_met": sorted(x["id"] for x in d["items"] if x["status"] == "not_met"),
                    **cau, "common_level_liberal": lib["common_level"], "note": d.get("note", "")})
    return out


# --- commands -------------------------------------------------------------------------------------

def cmd_build(a):
    rows, add = load_rows(), additions()
    ids = [l.strip() for l in open(a.ids) if l.strip()]
    bad = [i for i in ids if i not in rows or not labels_of(rows[i], add)]
    if bad:
        sys.exit(f"{len(bad)} ids not in the dataset or without labels, e.g. {bad[:3]}")
    os.makedirs(os.path.join(a.out, "cases"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "responses"), exist_ok=True)
    if os.listdir(os.path.join(a.out, "responses")):
        sys.exit("responses/ is not empty - refusing to rebuild over finished work")
    with open(os.path.join(a.out, "manifest.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "case_id", "diseases"])
        for k, cid in enumerate(ids, 1):
            labels = labels_of(rows[cid], add)
            fn = f"{k:04d}_{cid}.txt"
            open(os.path.join(a.out, "cases", fn), "w").write(
                f"=== SYSTEM PROMPT ({PROMPT_VERSION}) ===\n{SYSTEM}\n\n=== CASE ===\n{build_user(rows[cid], labels)}\n")
            w.writerow([fn, cid, "; ".join(labels)])
    nch = -(-len(ids) // 10)
    open(os.path.join(a.out, "RUNNER.md"), "w").write(RUNNER_MD.format(
        k=os.path.basename(a.out).replace("package-", ""), ncases=len(ids), chunk=10, conc=30, wait=45,
        nchunks=nch, nwaves=-(-nch // 30), ver=PROMPT_VERSION))
    print(f"wrote {len(ids)} case files to {a.out}")


def _iter(a):
    rows, add = load_rows(), additions()
    for fn in sorted(os.listdir(a.dir)):
        cid = fn.rsplit(".", 1)[0]
        if not fn.endswith(".json") or cid not in rows:
            yield cid, None, "non-json or unknown file"
            continue
        ok, j = validate(open(os.path.join(a.dir, fn)).read(), rows[cid], labels_of(rows[cid], add))
        yield cid, (j if ok else None), (None if ok else j)


def cmd_check(a):
    c, why = collections.Counter(), collections.Counter()
    lev = collections.defaultdict(collections.Counter)
    lib = collections.Counter()
    for cid, j, err in _iter(a):
        if err:
            c["invalid"] += 1
            why[err.split(":")[0]] += 1
            print(f"  invalid {cid}: {err}")
            continue
        c["valid"] += 1
        for r in result(j):
            lev[r["disease"]][r["common_level"]] += 1
            lev["ALL"][r["common_level"]] += 1
            lib[r["common_level_liberal"]] += 1
            if r["tags"]:
                lev["ALL"]["(scabies outside IACS scope)"] += 1
    print("files:", dict(c))
    if why:
        print("invalid reasons:", dict(why))
    order = [C, P, PO, I]
    for d in sorted(lev, key=lambda d: (d != "ALL", d)):
        n = sum(lev[d][k] for k in order)
        print(f"  {d:28s} n={n:4d}  " + "  ".join(f"{k} {lev[d][k]}" for k in order))
    print("  ALL, liberal choices        " + "  ".join(f"{k} {lib[k]}" for k in order))


def cmd_apply(a):
    n = 0
    with open(a.out, "w") as fh:
        for cid, j, err in _iter(a):
            if err:
                continue
            fh.write(json.dumps({"case_id": cid, "casedef": result(j), "prompt_version": PROMPT_VERSION},
                                ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} cases to {a.out}")


RUNNER_MD = _MASK_RUNNER.replace("clinical text masking job", "case-definition checklist job")


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
