# Stage 1: 22 Canonical Disease Guides

## 🎯 Objective
Create authoritative, standardized reference monographs for each of the **22 Canonical Tropical and Neglected Diseases**. These guides serve as the **foundational anchor nodes** in the Knowledge Graph, establishing ground-truth clinical boundaries for epidemiology, cardinal presentations, laboratory patterns, and differential rule-outs.

---

## 🧭 Role in the Big Picture

In the current setup, LightRAG only contains published PMC case reports. Because real-world case reports often highlight rare complications, unusual atypical presentations, or surgical debulking procedures, the graph lacks a clean definition of what the **typical, textbook presentation** of each disease looks like.

By ingesting these 22 Canonical Guides into LightRAG first:
1. **22 Golden Hub Nodes are established:** Each disease class receives an explicit, high-centrality profile.
2. **Clinical Boundaries are defined:** The model learns what findings *strongly confirm* (rule in) a disease and what findings *strongly exclude* (rule out) it.
3. **Melioidosis Attractor Supression:** Provides clear negative boundary criteria so the model stops treating Melioidosis as a catch-all bucket for any unexplained fever.

---

## 📋 The 22 Canonical Tropical Disease Classes

| # | Disease Class | Primary Pathogen / Vector | Key Diagnostic Hallmark |
|---|---|---|---|
| 1 | **Amebiasis** | *Entamoeba histolytica* | "Anchovy sauce" liver abscess, dysentery without high fever |
| 2 | **Cholera** | *Vibrio cholerae* | Painless profuse "rice-water" diarrhea, severe rapid dehydration |
| 3 | **Dengue** | Dengue virus (Aedes mosquito) | Retro-orbital pain, tourniquet test +, saddleback fever, thrombocytopenia |
| 4 | **Echinococcosis** | *Echinococcus granulosus/multilocularis* | Multiloculated hydatid liver/lung cysts, daughter cysts, "water lily" sign |
| 5 | **Foodborne Trematodes** | *Paragonimus*, *Clonorchis*, *Fasciola* | Biliary colic, hemoptysis + marked eosinophilia after raw seafood/game |
| 6 | **Leishmaniasis** | *Leishmania spp.* (Sandfly) | Visceral: Hepatosplenomegaly, pancytopenia, fever. Cutaneous: Volcanic ulcer |
| 7 | **Leprosy** | *Mycobacterium leprae* | Hypopigmented anesthetic skin patches, peripheral nerve thickening |
| 8 | **Leptospirosis** | *Leptospira interrogans* (Rodent urine/water) | Biphasic fever, conjunctival suffusion, calf pain, jaundice + renal failure (Weil) |
| 9 | **Malaria** | *Plasmodium spp.* (Anopheles mosquito) | Periodic paroxysms (cold-hot-sweating), splenomegaly, hemolytic anemia |
| 10 | **Melioidosis** | *Burkholderia pseudomallei* (Soil/water exposure) | Diabetic patient, severe cavitary pneumonia or multi-organ abscesses |
| 11 | **Mycetoma** | Fungal (Eumycetoma) / Bacterial (Actino) | Painless subcutaneous mass, multiple sinus tracts, discharging grains |
| 12 | **Neurocysticercosis** | *Taenia solium* (Pork tapeworm eggs) | Adult-onset new seizures, cystic/calcified parenchymal brain lesions on CT |
| 13 | **Paracoccidioidomycosis** | *Paracoccidioides brasiliensis* | Rural Latin America, mulberry-like oral mucosal ulcers, "bat-wing" infiltrates |
| 14 | **Scabies** | *Sarcoptes scabiei* mite | Severe nocturnal pruritus, burrows in finger webs, wrist flexures, genitals |
| 15 | **Schistosomiasis** | *Schistosoma spp.* (Freshwater snails) | Terminal hematuria (S. haematobium) or portal hypertension / pipestem fibrosis |
| 16 | **Scrub Typhus** | *Orientia tsutsugamushi* (Chigger mite) | Black cigarette-burn **eschar**, regional lymphadenopathy, prompt doxycycline cure |
| 17 | **Soil-Transmitted Helminths** | *Ascaris*, *Trichuris*, Hookworms | Chronic iron-deficiency anemia, eosinophilia, intestinal obstruction |
| 18 | **Talaromycosis** | *Talaromyces marneffei* | HIV/immunocompromised, umbilicated papules on face/trunk, hepatosplenomegaly |
| 19 | **Trypanosomiasis** | *T. cruzi* (Chagas) / *T. brucei* (Sleeping) | Chagas: Megacolon, dilated cardiomyopathy. African: Winterbottom sign, sleep inversion |
| 20 | **Tuberculosis** | *Mycobacterium tuberculosis* | Chronic cough >2-3 weeks, hemoptysis, night sweats, apical lung cavitation |
| 21 | **Viral Hemorrhagic Fevers** | Filovirus, Arenavirus, Bunyavirus | Sudden toxic fever, petechiae, mucosal bleeding, shock, liver enzyme elevation |
| 22 | **Zika Virus** | Zika virus (Aedes mosquito) | Low-grade fever, pruritic maculopapular rash, non-purulent conjunctivitis, arthralgia |

---

## 📑 Standard Clinical Schema for Each Guide

Each guide file is authored in markdown following this exact 5-axis clinical structure:

```markdown
# [Disease Name] - Canonical Clinical Profile

## 1. EPIDEMIOLOGICAL EXPOSURES & TRANSMISSION
- Geographic endemicity, travel requirements, rural vs. urban settings.
- Animal reservoirs, insect vectors, freshwater contact, soil inoculations.
- Incubation period ranges and seasonal patterns (monsoon, harvest).

## 2. CARDINAL CLINICAL SIGNS & TIMELINE
- Fever patterns (continuous, intermittent, biphasic, saddleback).
- Pathognomonic physical signs (eschars, conjunctival suffusion, anesthetic macules, etc.).
- Multi-organ involvement timeline (pulmonary, CNS, hepatic, renal, hematologic).

## 3. ADMISSION LAB & BEDSIDE IMAGING HALLMARKS
- CBC patterns (leukopenia, leukocytosis, thrombocytopenia, eosinophilia).
- Liver function (AST/ALT ratio, total bilirubin), renal markers, urinalysis.
- Ultrasound / X-ray / CT findings available at initial hospital triage.

## 4. DIFFERENTIAL RULE-OUT CRITERIA (Look-Alikes)
- List of the 2-3 most frequent look-alike tropical diseases.
- Specific clinical negatives or discrepancies that rule OUT each look-alike.
- Specific clinical features that rule OUT this disease if present.

## 5. EMPIRICAL DRUG RESPONSE CLUES
- Rapid therapeutic response markers (e.g. defervescence within 48h of Doxycycline, Praziquantel, Artemisinin).
- Ineffective empirical treatments (e.g. failure to respond to standard beta-lactams).
```

---

## 🛠️ Step-by-Step Execution Plan for Stage 1

1. **Create the `guides/` subfolder:** Store individual markdown files (`dengue.md`, `scrub_typhus.md`, etc.).
2. **Draft the 22 Profiles:** Use clinical guidelines (WHO manuals, CDC Yellow Book, Harrison's Principles of Internal Medicine) to write comprehensive profiles following the 5-axis schema.
3. **Compile Index Bundle:** Combine the 22 guides into a consolidated JSONL/markdown ingestion source ready to be fed into LightRAG in Stage 2.
