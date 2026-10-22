# Stage 1: Clinical Knowledge Graph Extraction Prompt

This prompt is designed to extract high-density, discriminative clinical Knowledge Graph profiles from comprehensive disease monographs and authoritative clinical literature (WHO, CDC, Europe PMC Landmark Reviews).

It is strictly grounded in **Cognitive Illness Script Theory** (*Schmidt & Boshuizen, 1990; Bowen, NEJM 2006*) and **Bayesian Likelihood Thresholds** (*Pauker & Kassirer, NEJM 1980*), and is 100% plug-and-play compatible with the LightRAG ingestion engine in [`benchmarks/build_clinical_kg.py`](../benchmarks/build_clinical_kg.py).

---

## 🏛️ Master System Prompt for LLM Extraction

```markdown
You are an expert tropical medicine physician and clinical knowledge graph engineer.

Your task is to analyze the authoritative clinical monograph for "{DISEASE_NAME}" and extract an Illness Script Knowledge Graph profile grounded in Bayesian diagnostic thresholds, formatted for LightRAG.

### 1. THE 6 CLINICAL COGNITION AXES (Choose strictly from these):

#### Axis 1: Predisposing Conditions (Who gets it?)
- Entity Type: "Vector_Exposure" (Vectors, animal reservoirs, soil/freshwater habitats, rural/urban settings, occupational hazards, host comorbidities like diabetes).
- Relationship Name: "TRANSMITTED_BY" or "EXPOSURE_TO"

#### Axis 2: Pathophysiological Fault (What is it?)
- Entity Type: "Pathogen" (Causative organism, genus, species, taxonomy, toxins, life cycle stage).
- Relationship Name: "HAS_PATHOGEN"

#### Axis 3: High Likelihood Ratio+ (What confirms / Rules in?)
- Entity Type: "Cardinal_Sign" (Pathognomonic physical hallmarks, smoking-gun lesions, rash timelines, characteristic physical findings).
- Entity Type: "Admission_Lab_Imaging" (Admission triage CBC cutoffs, LFT patterns, urinalysis, POCUS ultrasound, chest X-ray findings).
- Relationship Name: "HAS_PATHOGNOMONIC_HALLMARK" (for signs with LR+ >> 10 that cross the treatment threshold)
- Relationship Name: "EXHIBITS_LAB_PATTERN" (for characteristic admission lab and imaging patterns)

#### Axis 4: Low Likelihood Ratio- (What excludes / Rules out?)
- Entity Type: "Exclusion_Criterion" (Specific negative findings, normal lab cutoffs, or fever durations that strongly EXCLUDE this disease).
- Relationship Name: "RULED_OUT_BY"

#### Axis 5: Direct Contrasts (What looks like it?)
- Entity Type: "Disease" (The top 2-3 look-alike tropical diseases).
- Relationship Name: "DIFFERENTIATED_FROM" (Explains the exact bedside finding or laboratory cutoff that separates this disease from the look-alike).

#### Axis 6: Therapeutic Verification (How to test / verify?)
- Entity Type: "Drug_Response" (Empirical treatment response, rapid defervescence timeline, or intrinsic resistance).
- Relationship Name: "RESPONDS_TO" or "INTRINSICALLY_RESISTANT_TO"

---

### 2. CRITICAL CLINICAL EXTRACTION CONSTRAINTS:

1. NO NAKED GENERIC HUBS:
   - DO NOT extract generic, non-discriminative terms like "Fever", "Headache", "Pain", or "Vomiting" as standalone isolated nodes.
   - Always qualify them with clinical descriptors (e.g., "Saddleback Biphasic Fever", "Retro-Orbital Headache", "Severe Gastrocnemius Calf Myalgia").

2. MANDATORY NEGATIVE BOUNDARIES (RULED_OUT_BY):
   - You MUST extract at least 2 to 4 explicit negative boundary rules stating what clinical findings, lab thresholds, or timelines RULE OUT this disease.
   - Set relationship `keywords` to start with: "RULED_OUT_BY, exclusion criterion, negative boundary".

3. MANDATORY DIRECT DIFFERENTIAL CONTRASTS (DIFFERENTIATED_FROM):
   - You MUST extract direct contrast edges against the top 2 to 3 most common look-alike tropical diseases.
   - In the relationship `description`, explicitly state how a triage physician tells them apart at admission.
   - Set relationship `keywords` to start with: "DIFFERENTIATED_FROM, look-alike, differential diagnosis".

4. PATHOGNOMONIC HALLMARKS (HAS_PATHOGNOMONIC_HALLMARK):
   - For findings that strongly confirm the disease (e.g., eschar, anchovy-sauce pus, terminal hematuria, water-lily sign), set relationship `keywords` to start with: "HAS_PATHOGNOMONIC_HALLMARK, smoking gun, rules in".

5. ADMISSION TEMPORAL CONSTRAINT:
   - All clinical signs and lab patterns MUST be findings available at initial hospital admission/triage (history, physical exam, CBC with differential, LFTs, basic urinalysis, POCUS ultrasound, plain chest X-ray).
   - Do NOT rely on delayed confirmatory culture species, PCR serotypes, or post-biopsy findings as primary diagnostic anchors, as these are masked or pending at admission.

---

### 3. OUTPUT JSON FORMAT (Return ONLY raw valid JSON):

{
  "entities": [
    {
      "name": "<Canonical Entity Name>",
      "type": "<Vector_Exposure | Pathogen | Cardinal_Sign | Admission_Lab_Imaging | Exclusion_Criterion | Disease | Drug_Response>",
      "description": "<Concise clinical definition and diagnostic significance>"
    }
  ],
  "relationships": [
    {
      "source": "<Source Entity Name>",
      "target": "<Target Entity Name>",
      "keywords": "<EXACT_RELATION_NAME, e.g. HAS_PATHOGNOMONIC_HALLMARK, RULED_OUT_BY, DIFFERENTIATED_FROM, plus descriptive tags>",
      "description": "<Detailed clinical explanation of this diagnostic relationship>"
    }
  ]
}
```

---

## 🧪 Concrete Demonstration: Extraction for Melioidosis

```json
{
  "entities": [
    {
      "name": "Melioidosis",
      "type": "Disease",
      "description": "Severe tropical infection endemic to Southeast Asia and Northern Australia caused by Burkholderia pseudomallei."
    },
    {
      "name": "Burkholderia pseudomallei",
      "type": "Pathogen",
      "description": "Gram-negative, oxidase-positive environmental saprophytic bacillus exhibiting bipolar safety-pin staining."
    },
    {
      "name": "Wet Soil & Monsoon Inoculation",
      "type": "Vector_Exposure",
      "description": "Percutaneous inoculation or aerosol inhalation from wet tropical soils, mud, or surface water during monsoons."
    },
    {
      "name": "Type 2 Diabetes Mellitus",
      "type": "Vector_Exposure",
      "description": "Primary host susceptibility factor present in >40-60% of all melioidosis patients (impaired neutrophil oxidative burst)."
    },
    {
      "name": "Suppurative Parotitis in Children",
      "type": "Cardinal_Sign",
      "description": "Hallmark presentation in Southeast Asian pediatric cohorts presenting with acute unilateral parotid abscess."
    },
    {
      "name": "Prostatic Abscess in Males",
      "type": "Cardinal_Sign",
      "description": "Present in 18-30% of adult males presenting with perineal pain and acute urinary retention."
    },
    {
      "name": "Honeycomb Splenic Microabscesses",
      "type": "Admission_Lab_Imaging",
      "description": "Multiple small, discrete round hypoechoic lesions in spleen and liver creating a Swiss-cheese or honeycomb ultrasound pattern."
    },
    {
      "name": "Marked Neutrophilic Leukocytosis",
      "type": "Admission_Lab_Imaging",
      "description": "WBC 15,000-30,000/µL with toxic left shift (bandemia >15%) and CRP >150 mg/L."
    },
    {
      "name": "Healthy Young Host with Zero Soil Contact",
      "type": "Exclusion_Criterion",
      "description": "Presentation in a non-diabetic host with no outdoor soil/water exposure makes melioidosis highly improbable."
    },
    {
      "name": "Cavitary Pneumonia Resolving on Ceftriaxone",
      "type": "Exclusion_Criterion",
      "description": "Rapid clinical response to standard third-generation cephalosporins rules out Burkholderia pseudomallei."
    },
    {
      "name": "Tuberculosis",
      "type": "Disease",
      "description": "Top look-alike disease presenting with upper-lobe cavitary lesions and wasting."
    },
    {
      "name": "Intrinsic Ceftriaxone & Penicillin Resistance",
      "type": "Drug_Response",
      "description": "Intrinsically resistant to penicillins, 1st/2nd/3rd gen cephalosporins (ceftriaxone), and aminoglycosides; requires Ceftazidime or Meropenem."
    }
  ],
  "relationships": [
    {
      "source": "Melioidosis",
      "target": "Burkholderia pseudomallei",
      "keywords": "HAS_PATHOGEN, causative agent, microbiology",
      "description": "Caused by Burkholderia pseudomallei."
    },
    {
      "source": "Melioidosis",
      "target": "Wet Soil & Monsoon Inoculation",
      "keywords": "EXPOSURE_TO, environmental risk, transmission",
      "description": "Acquired through direct contact with contaminated tropical soil and surface water."
    },
    {
      "source": "Melioidosis",
      "target": "Type 2 Diabetes Mellitus",
      "keywords": "EXPOSURE_TO, host predisposition, diabetes",
      "description": "Type 2 diabetes is the single strongest clinical host risk factor, present in over half of cases."
    },
    {
      "source": "Melioidosis",
      "target": "Suppurative Parotitis in Children",
      "keywords": "HAS_PATHOGNOMONIC_HALLMARK, pediatric sign, rules in",
      "description": "Acute suppurative parotitis in an endemic pediatric patient is a cardinal hallmark."
    },
    {
      "source": "Melioidosis",
      "target": "Honeycomb Splenic Microabscesses",
      "keywords": "EXHIBITS_LAB_PATTERN, imaging hallmark, POCUS",
      "description": "A Swiss-cheese or honeycomb appearance of the spleen on ultrasound strongly indicates melioidosis."
    },
    {
      "source": "Melioidosis",
      "target": "Tuberculosis",
      "keywords": "DIFFERENTIATED_FROM, look-alike, upper lobe cavity",
      "description": "TB has an insidious course (>3 weeks), normal WBC, and AFB on smear; acute pulmonary melioidosis presents acutely (days), with high leukocytosis and procalcitonin."
    },
    {
      "source": "Melioidosis",
      "target": "Healthy Young Host with Zero Soil Contact",
      "keywords": "RULED_OUT_BY, negative boundary, exclusion",
      "description": "Absence of soil/water exposure and absence of diabetes makes melioidosis extraordinarily unlikely."
    },
    {
      "source": "Melioidosis",
      "target": "Cavitary Pneumonia Resolving on Ceftriaxone",
      "keywords": "RULED_OUT_BY, exclusion criterion, antibiotic response",
      "description": "Response to ceftriaxone completely rules out Burkholderia pseudomallei due to intrinsic resistance."
    },
    {
      "source": "Melioidosis",
      "target": "Intrinsic Ceftriaxone & Penicillin Resistance",
      "keywords": "INTRINSICALLY_RESISTANT_TO, antibiotic failure, intrinsic resistance",
      "description": "Standard empirical therapy with ceftriaxone fails; requires intravenous ceftazidime or meropenem."
    }
  ]
}
```
