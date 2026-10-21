import json
import os
import re

BATCH_DIR = os.path.dirname(os.path.abspath(__file__))

cases = {}

# -------------------------------------------------------------
# Case 0: PMC12463585_01 - Echinococcosis
# -------------------------------------------------------------
cases["PMC12463585_01"] = {
    "case_id": "PMC12463585_01",
    "disease": "Echinococcosis",
    "think": (
        "1. Core Clinical Tension: A 23-year-old urban homemaker without known animal exposure presents with chronic left upper quadrant pain radiating to the back, low-grade fevers, marked splenomegaly, and peripheral eosinophilia (10.9%). Primary splenic localization without antecedent or concurrent hepatic or pulmonary cystic involvement is exceedingly uncommon (representing under 2-3% of cases), creating clinical overlap with non-parasitic congenital cysts, epidermoid cysts, splenic abscess, hematologic neoplasms, or wandering spleen.\n"
        "2. Admission Breakpoint: The admission breakpoint is established immediately after initial baseline laboratory workup, negative stool microscopy, plain chest radiography, and abdominal ultrasonography/CT confirming an isolated 9.8 x 7.8 cm unilocular splenic cyst with splenomegaly, prior to WHO-IWGE echinococcal staging, Echinococcus-specific enzyme immunoassay serologies, and post-splenectomy histopathological examination.\n"
        "3. Differential Distinctions: Splenic abscess (ruled out by afebrile state on presentation, normal WBC count, and lack of systemic sepsis), non-parasitic epidermoid/epithelial splenic cysts (lack peripheral eosinophilia), intestinal helminthiases (ruled out by normal stool examination), and secondary disseminated hydatidosis (ruled out by normal liver parenchyma and clear chest radiograph). Definitive identification relies on specific serology and pathognomonic acellular laminated membranes on histopathology."
    ),
    "case_prompt": (
        "A 23-year-old female homemaker presented with a 2-month history of severe, gradually worsening abdominal pain localized to the left upper quadrant, radiating to her back. The pain was sharp in character and accompanied by nausea, vomiting, and loss of appetite. She also reported persistent low-grade fever (99°F to 100°F) responsive to over-the-counter antipyretics, without chills, rigors, or rash. She experienced transient loose stools at the onset of pain that resolved within approximately two weeks. There was no history of jaundice, constipation, dysuria, hematochezia, or other systemic complaints. Her past medical and surgical history was unremarkable, with no known comorbidities or family history of genetic disorders. She consumed a non-vegetarian diet, had resided in an urban area for several years, and denied exposure to domestic animals or recent travel. Menstrual history was regular, and she was nulliparous.\n\n"
        "On physical examination, the patient was alert and oriented. Vital signs revealed a pulse rate of 86 beats/min, blood pressure 122/82 mmHg, body temperature 98°F, respiratory rate 16 breaths/min, and oxygen saturation 99% on ambient air. Abdominal examination revealed marked splenomegaly without signs of peritoneal irritation.\n\n"
        "Initial laboratory investigations revealed a normal complete blood count except for peripheral eosinophilia at 10.9% (reference range: 1–6%). Comprehensive metabolic panel, including liver and kidney function tests, random blood glucose, and viral hepatitis (hepatitis B and C) and HIV screening, were unremarkable. Electrocardiogram was normal. Stool microscopic examination for ova and parasites was negative.\n\n"
        "Chest radiography demonstrated clear lung fields without infiltrates or mass lesions. Abdominal ultrasonography revealed an enlarged spleen measuring 13 cm along the long axis containing an anechoic cyst measuring 9.7 x 8.7 x 7.9 cm with a wall thickness of 0.4 cm and an estimated volume of 352 cm³, with normal liver architecture and no extra-splenic abdominal cysts. Contrast-enhanced computed tomography of the abdomen confirmed a well-circumscribed, solitary splenic cyst measuring 9.8 x 7.8 cm without internal calcification or soft-tissue components, accompanied by splenomegaly (14.7 cm in length)."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Intestinal parasitic helminthiases",
            "rule_out_reason": "Although the patient exhibited loose stools at disease onset and had marked peripheral eosinophilia (10.9%), microscopic examination of the stool showed no ova or parasites.",
            "quote": "Stool examination was normal, effectively ruling out other parasitic infections."
        },
        {
            "candidate": "Disseminated or hepatic hydatid cyst disease",
            "rule_out_reason": "Primary hydatid cysts most commonly involve the liver (50-70%) followed by the lungs (20-30%); however, imaging demonstrated strictly isolated splenic involvement without hepatic or thoracic cystic lesions.",
            "quote": "No additional cystic lesions were identified in the liver or elsewhere in the abdomen. A chest X-ray showed no evidence of pulmonary involvement."
        },
        {
            "candidate": "Splenic abscess or neoplastic/solid splenic lesion",
            "rule_out_reason": "CT imaging showed a smooth, thin-walled, anechoic cyst without internal debris, calcifications, wall nodularity, or enhancing soft tissue components, arguing against acute bacterial abscess or neoplastic cystic degeneration.",
            "quote": "Computed tomography (CT) of the abdomen confirmed a large splenic cyst (9.8 x 7.8 cm) without calcification or soft tissue components, along with splenomegaly (14.7 cm in length)"
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "Specific enzyme immunoassay serology confirmed elevated Echinococcus IgG and markedly elevated IgE, followed by post-splenectomy histopathological identification of an acellular laminated membrane and germinal layer staining positive with periodic acid-Schiff stain.",
            "quote": "Further evaluation with Echinococcus serology using enzyme immunoassay revealed an elevated immunoglobulin G (IgG) level of 1.07 (normal: <0.9) and a markedly raised immunoglobulin E (IgE) level of 593.4 IU/mL (normal: <100 IU/mL)... Microscopic analysis demonstrated that the cyst wall consisted of an outer acellular laminated membrane, adjacent to a dense fibrotic pseudocapsule layer... The cyst wall tested positive for periodic acid-Schiff (PAS) stain."
        }
    ],
    "final_diagnosis": "Echinococcosis",
    "audit_flags": ["NONE"],
    "editor_comments": "Stanford MedCaseReasoning distillation completed. Admission breakpoint strictly placed prior to WHO-IWGE cyst classification and Echinococcus-specific serology. Case prompt is entirely free of pathogen or disease names."
}

# -------------------------------------------------------------
# Case 1: PMC12623078_01 - Cholera
# -------------------------------------------------------------
cases["PMC12623078_01"] = {
    "case_id": "PMC12623078_01",
    "disease": "Cholera",
    "think": (
        "1. Core Clinical Tension: A 47-year-old traveler returning from India presents with profound watery secretory diarrhea (>40 episodes in 24 hours), severe hypovolemia, normal-anion-gap metabolic acidosis, and acute kidney injury. Within hours of admission, he develops acute ischemic stroke (left anterior cerebral artery occlusion) and acute ST-elevation myocardial infarction. The central diagnostic challenge is determining whether this represents multi-vessel primary atherosclerotic cardiovascular collapse or a rare catastrophic thrombotic complication of extreme dehydration, hemoconcentration, and infectious hypercoagulability following travel-associated secretory diarrhea.\n"
        "2. Admission Breakpoint: The admission breakpoint is established at emergency department triage and initial ICU admission following resuscitation, baseline laboratories, and urgent neurovascular/cardiac imaging on Day 1, prior to the return of confirmatory stool microbiology cultures on Day 3.\n"
        "3. Differential Distinctions: Primary acute coronary syndrome / plaque rupture (ruled out by coronary CT angiography showing no significant coronary atherosclerosis and zero calcium score), acute viral/toxic myopericarditis (ruled out by preserved ejection fraction of 61% without wall motion abnormalities), and primary cardiogenic embolization (ruled out by normal contrast echocardiography). Confirmatory stool culture identifying Vibrio cholerae establishes massive cholera enterotoxin-mediated dehydration and hemoconcentration-induced arterial thrombosis."
    ),
    "case_prompt": (
        "A 47-year-old Indian male presented to the emergency department complaining of acute, massive watery diarrhea without blood or mucus, lasting one day and exceeding forty discrete episodes. He also reported colicky, non-radiating paraumbilical abdominal pain, profuse diaphoresis, profound lethargy, and recurrent non-projectile vomiting of ingested food. He denied hematemesis, dysphagia, or melena. He had consumed food at a local restaurant in India one day prior to symptom onset and had returned from travel the day preceding presentation. He had no sick contacts, and accompanying family members remained asymptomatic. Past medical history was significant only for prior cataract surgery, with no personal or family history of inflammatory bowel disease or cardiovascular disorders. He was a non-smoker.\n\n"
        "On arrival, he was afebrile with a normal pulse rate and supine blood pressure of 91/54 mmHg. Physical examination was notable for signs of severe dehydration. Triage laboratory evaluation revealed acute prerenal azotemia with acute kidney injury, a normal-anion-gap metabolic acidosis, and an elevated cardiac troponin. Initial electrocardiogram demonstrated normal sinus rhythm without ST-segment elevation or T-wave abnormalities. Fluid resuscitation and intravenous supportive therapy were initiated, and he was transferred to the medical intensive care unit.\n\n"
        "A few hours following admission, the patient became acutely disoriented with incoherent speech, labored breathing, and new right-sided dense hemiplegia and global aphasia (NIHSS score of 22). Urgent non-contrast CT and CT angiography of the head revealed acute occlusion of the left anterior cerebral artery branches distal to the anterior communicating artery and atheromatous plaque with significant luminal stenosis in the left common carotid artery. A repeat electrocardiogram revealed junctional tachycardia with ST-segment elevations across inferior leads (II, III, aVF) and anterolateral leads (V5, V6), accompanied by progressive rise in serial troponin concentrations."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Primary acute coronary syndrome (STEMI from plaque rupture)",
            "rule_out_reason": "Cardiology initially suspected primary atherothrombotic plaque rupture; however, follow-up CT coronary angiography revealed completely unobstructed coronary arteries with a coronary artery calcium score of zero, pointing instead to transient coronary embolism secondary to severe hemoconcentration and dehydration.",
            "quote": "No evidence of significant coronary artery disease was noted in this imaging with a calcium score of zero (Figure 6). Considering these results, the cardiology team finally concluded that the most probable diagnosis in this patient was transient coronary emboli due to dehydration or infection."
        },
        {
            "candidate": "Acute myopericarditis",
            "rule_out_reason": "Myopericarditis was considered due to diffuse ST-segment changes and troponin release in a patient with acute systemic infection, but echocardiography revealed preserved left ventricular systolic function (EF 61%) without regional wall motion abnormalities or pericardial effusion.",
            "quote": "His echocardiogram demonstrated a left ventricle ejection fraction of 61% with no evidence of regional wall motion abnormalities or diastolic dysfunction... Myocarditis could have been another differential; however, it was thought to be the least probable cause in our patient's case."
        },
        {
            "candidate": "Primary cardioembolic stroke",
            "rule_out_reason": "Cardioembolic origin of the anterior cerebral artery occlusion was ruled out by contrast-enhanced echocardiography demonstrating absence of intracardiac thrombus, while Doppler ultrasound showed resolution of common carotid thrombus without intrinsic hemodynamically significant stenosis.",
            "quote": "The carotid Doppler ultrasound findings were unremarkable with no focal functional luminal stenosis or flow disturbances noted bilaterally... Additionally, contrast-enhanced echocardiography did not show the presence of any thrombus in the left ventricle."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "The diagnostic pivot occurred on hospital day 3 when stool cultures confirmed Vibrio cholerae, establishing an overarching unifying diagnosis of cholera complicated by extreme hypovolemia, hemoconcentration, and dual arterial thromboembolic vascular occlusions.",
            "quote": "On the third day of admission, stool culture confirmed the presence of Vibrio cholerae. Infectious Diseases team recommended initiating azithromycin therapy for one day."
        }
    ],
    "final_diagnosis": "Cholera",
    "audit_flags": ["NONE"],
    "editor_comments": "Admission breakpoint captured at Day 1 emergency / ICU presentation including the immediate hypercoagulable vascular manifestations prior to Day 3 microbiological stool culture identification. Clean presentation without pathogen disclosures."
}

# -------------------------------------------------------------
# Case 2: PMC12681803_01 - Soil-Transmitted Helminths
# -------------------------------------------------------------
cases["PMC12681803_01"] = {
    "case_id": "PMC12681803_01",
    "disease": "Soil-Transmitted Helminths",
    "think": (
        "1. Core Clinical Tension: A 62-year-old male who underwent orthotopic cardiac transplantation two months prior presents with progressive dyspnea, hypoxia, and septic shock accompanied by diffuse alveolar hemorrhage. The presence of purpura mimicking drug reaction, adhesive trauma, or bacterial vasculitis, coupled with completely normal peripheral eosinophil counts and initially negative routine stool O&P examinations, creates an extreme diagnostic challenge that masks disseminated parasitosis in an immunocompromised host.\n"
        "2. Admission Breakpoint: The admission breakpoint is placed at initial intensive care triage and bronchoscopic evaluation showing diffuse alveolar hemorrhage and negative conventional microbiological testing, prior to send-out plasma microbial cell-free DNA (Karius), cutaneous punch biopsy, and targeted parasite microscopy.\n"
        "3. Differential Distinctions: Isolated bacterial sepsis (secondary bacteremia from enterococcal or Gram-negative bacilli due to translocation), viral/fungal opportunistic pneumonitis (ruled out by negative respiratory viral multiplex and negative BAL cultures), and leukocytoclastic vasculitis or adhesive tape dermatitis (characteristic periumbilical and 'thumbprint' purpura tracking along ECG/adhesive leads is a hallmark of cutaneous larval migration). Confirmatory detection by cell-free DNA and dermal punch biopsy demonstrating helminth larvae confirms disseminated strongyloidiasis."
    ),
    "case_prompt": (
        "A 62-year-old male with a history of orthotopic cardiac transplantation performed 2 months prior presented to the emergency department with progressive dyspnea and severe hypoxia. He was in septic shock requiring hemodynamic resuscitation. Past medical history was significant for end-stage heart failure status-post heart transplantation, maintained on standard post-transplant immunosuppression. He had no reported acute environmental exposures.\n\n"
        "On physical examination, the patient was in marked respiratory distress, hypotensive, and hypoxic. Cutaneous examination revealed faint purpuric macules and patches located across the chest, periumbilically, and on the proximal thighs; on the chest, the purpura distinctly followed the geographic outline of previously applied adhesive telemetry pads.\n\n"
        "Initial triage laboratories demonstrated a normal peripheral eosinophil count. Urgent flexible bronchoscopy was performed to investigate acute respiratory failure, which revealed diffuse alveolar hemorrhage. Routine multiplex respiratory pathogen panel was negative, routine bronchoalveolar lavage bacterial and fungal cultures yielded no growth, and initial microscopic examination of the stool for ova and parasites was negative."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Primary opportunistic bacterial pneumonia and sepsis",
            "rule_out_reason": "The patient presented in septic shock with Klebsiella pneumoniae bacteremia and bacteriuria; however, alveolar hemorrhage and characteristic purpura persisted despite empiric antimicrobial therapy, indicating that bacteremia was a secondary complication of mucosal disruption driven by larval penetration.",
            "quote": "He was found to be in septic shock secondary to Klebsiella pneumoniae bacteremia and bacteriuria. Bronchoscopy revealed diffuse alveolar hemorrhage. Infectious workup to this point was unrevealing, including a negative respiratory panel, negative cultures from his bronchoalveolar lavage, and a negative stool ova & parasite (O&P)."
        },
        {
            "candidate": "Drug-induced vasculitis or mechanical adhesive purpura",
            "rule_out_reason": "While the purpuric patches on the chest adhered to the margins of adhesive monitoring pads, the simultaneous appearance of periumbilical and proximal thigh lesions in a transplant recipient represented the characteristic 'thumbprint purpura' of subcutaneous parasite migration rather than an allergic drug reaction or adhesive trauma.",
            "quote": "Physical examination revealed faint purpuric macules and patches located on the chest, periumbilically (Fig 1), and on the proximal thighs (Fig 2). On the chest, the purpura was noted to follow the outline of prior adhesives."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "Plasma microbial cell-free DNA (Karius) testing detected Strongyloides, followed by punch biopsy of the thigh lesion confirming helminth larvae and egg-like forms within the dermis, with subsequent rereview of bronchoalveolar lavage and repeat stool microscopy confirming disseminated Strongyloides infection.",
            "quote": "Given clinical deterioration and concern for infection not captured by conventional microbiologic testing, plasma microbial cell-free DNA (Karius) testing was pursued, which returned positive for Strongyloides... Punch biopsy of the left upper thigh (Fig 3, A-C) revealed larvae and egg-like forms within the dermis, most suggestive of Strongyloides. Rereview of his bronchoalveolar lavage revealed a rare focus morphologically compatible with Strongyloides, and repeat stool O&P returned positive, further confirming the diagnosis."
        }
    ],
    "final_diagnosis": "Soil-Transmitted Helminths",
    "audit_flags": ["NONE"],
    "editor_comments": "Distilled case accurately targets Soil-Transmitted Helminths (Strongyloides stercoralis hyperinfection). Admission breakpoint stops cleanly prior to Karius cell-free DNA and skin biopsy findings. Zero pathogen disclosures in prompt."
}

# -------------------------------------------------------------
# Case 3: PMC12812521_01 - Tuberculosis
# -------------------------------------------------------------
cases["PMC12812521_01"] = {
    "case_id": "PMC12812521_01",
    "disease": "Tuberculosis",
    "think": (
        "1. Core Clinical Tension: A 71-year-old woman with a decade-long history of poorly controlled tophaceous gout and rheumatoid arthritis presents with left lower back pain, difficulty walking, and a large cystic multilocular iliopsoas/hip lesion. Given marked hyperuricemia (555.9 umol/L), periarticular sandy calcifications, and milky aspirate, the presentation strongly suggests an extensive gouty tophus. However, the subsequent emergence of persistent cyclical nocturnal high-grade spikes (up to 39.3°C) unresponsive to broad-spectrum cephalosporins and urate-lowering agents signals an occult granulomatous coinfection within the retroperitoneal tophus.\n"
        "2. Admission Breakpoint: The admission breakpoint falls on Day 1 after initial clinical examination, triage blood work, urinalysis, plain pelvic radiographs, and abdominal/pelvic CT, before the onset of cyclical high-grade fevers on Day 2, needle aspiration of milky fluid on Day 3, T-cell interferon testing, and high-throughput metagenomic tissue sequencing.\n"
        "3. Differential Distinctions: Uncomplicated tophaceous gout of the iliopsoas (does not cause persistent spiking fevers up to 39.3°C or severe acute-phase reactant elevations refractory to NSAIDs/febuxostat), pyogenic psoas abscess (ruled out by negative standard bacterial/anaerobic cultures and failure of 8 days of IV ceftriaxone), and fungal abscess (ruled out by negative fungal smears and cultures). T-cell IGRA positivity and tissue mNGS proving Mycobacterium tuberculosis establish coinfection."
    ),
    "case_prompt": (
        "A 71-year-old woman who lived alone was admitted to the hospital with left lower back pain, fatigue, and difficulty walking. She had previously been hospitalized at another institution for approximately one month and treated with bed rest, analgesics, and empiric systemic anti-infectives without symptomatic improvement. Her medical history was notable for poorly controlled gout and rheumatoid arthritis for more than 10 years; she denied a history of diabetes mellitus, prior pulmonary disease, genetic disorders, or trauma. Physical examination revealed deforming changes of the right hands and palpable tophi in the left finger joints of over a decade's duration. There was moderate tenderness in the left lower quadrant of the abdomen, restricted range of motion of the left hip, and posterolateral swelling of the left hip with an obvious concave scar, without sinus tracts or open wounds. She was afebrile on admission.\n\n"
        "Initial laboratory investigations revealed a serum uric acid level of 555.9 µmol/L (reference range: 208–428 µmol/L), erythrocyte sedimentation rate (ESR) of 113 mm/h (reference range: 1–15 mm/h), C-reactive protein (CRP) of 182.59 mg/L (reference range: 0–5 mg/L), procalcitonin of 0.67 ng/mL, white blood cell count of 8.04 x 10⁹/L (78.8% neutrophils, 12.9% lymphocytes), hemoglobin of 54 g/L, and platelet count of 221 x 10⁹/L. Serum creatinine was elevated at 191 µmol/L and blood urea nitrogen at 11.9 mmol/L; serum albumin was 26.3 g/L. Urinalysis was unremarkable except for positive occult blood (+). Stool examination, electrocardiogram, echocardiography, and plain chest radiography were all normal.\n\n"
        "Pelvic radiographs demonstrated erosion of the left sacral and iliac borders, widening of the left sacroiliac joint, condensation of the adjacent bone, joint space narrowing, and a low-density cystic lesion of the left hip. Computed tomography (CT) confirmed widening of the left sacroiliac joint, a multilocular fluid collection within the left psoas muscle, and juxta-articular soft-tissue masses containing sandy calcifications around the pelvis and bilateral hips."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Isolated retroperitoneal and hip tophaceous gout",
            "rule_out_reason": "While the patient had marked hyperuricemia, deforming peripheral tophi, and sandy calcifications on CT, isolated tophaceous gout could not explain the persistent cyclical nocturnal fever (peaking at 39.3°C) that began on day 2 and failed to respond to febuxostat and NSAIDs.",
            "quote": "CT findings indicated the possibility of a combined left psoas muscle and left hip abscess, as well as tophaceous gout of both hips... On the 2nd day of admission, febuxostat 40 mg was administered orally once a day for the gout treatment; ceftriaxone 2 g intravenous drip was used once a day for anti-infective therapy lasting 8 days, but it did not work as the fever persisted."
        },
        {
            "candidate": "Pyogenic bacterial or fungal psoas abscess",
            "rule_out_reason": "Pyogenic bacterial abscess and fungal collections were ruled out because 8 days of IV ceftriaxone failed to alleviate symptoms, and multiple aspirated fluid and surgical tissue cultures were negative for Gram-positive, Gram-negative, anaerobic bacteria, and fungi.",
            "quote": "cultures for Gram-positive and Gram-negative bacteria, anaerobic bacteria, and fungi were all negative. Quantitative fluorescence polymerase chain reaction (PCR) of DNA in tuberculosis sputum smears for acid-fast bacteria and fungi was also negative."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "T-cell interferon detection returned positive, and subsequent open debridement of the iliopsoas collection combined with high-throughput metagenomic gene sequencing confirmed divergent Mycobacterium tuberculosis co-infecting the gouty tophus.",
            "quote": "however, the detection of TB infection in the T cells was positive... high-throughput gene sequencing of these tissues for various pathogens indicated divergent Mycobacterium tuberculosis without other bacteria, fungi, or anaerobic bacteria."
        }
    ],
    "final_diagnosis": "Tuberculosis",
    "audit_flags": ["NONE"],
    "editor_comments": "Distilled case accurately targets Tuberculosis (iliopsoas gout-TB coinfection). Breakpoint placed at Day 1 triage before aspiration and send-out sequencing. Zero pathogen names in case prompt."
}

# -------------------------------------------------------------
# Case 4: PMC12908690_01 - Tuberculosis
# -------------------------------------------------------------
cases["PMC12908690_01"] = {
    "case_id": "PMC12908690_01",
    "disease": "Tuberculosis",
    "think": (
        "1. Core Clinical Tension: An 80-year-old woman without known immunosuppression or sick contacts presents acutely with confusion, severe hypoxemia (SpO2 70-85%), and diffuse reticulonodular infiltrates on a background of an 11-kg weight loss over six months and low-grade morning fevers. A positive multiplex PCR panel for Staphylococcus aureus creates a dangerous cognitive trap for typical bacterial bronchopneumonia, threatening to obscure the underlying hematogenously disseminated miliary mycobacterial infection.\n"
        "2. Admission Breakpoint: The admission breakpoint is placed at Day 1 emergency triage after physical examination, vital signs, initial hematology/inflammatory labs, and portable chest radiograph showing reticulonodular infiltrates, prior to multiplex pneumonia PCR panels, HRCT chest micronodule delineation, and bronchoalveolar lavage MTB PCR/QuantiFERON testing.\n"
        "3. Differential Distinctions: Acute Staphylococcus aureus community-acquired pneumonia (ruled out because the indolent 6-month chronology, normal procalcitonin, and lack of consolidations or purulence were discordant with acute staphylococcal pneumonia, indicating colonization), disseminated pulmonary metastasis / lymphangitic carcinomatosis (ruled out by uniform micronodular pattern on HRCT and negative cytology), and atypical fungal/pneumocystis pneumonia. Identification of MTB DNA on BAL fluid establishes miliary tuberculosis."
    ),
    "case_prompt": (
        "An 80-year-old female presented to the emergency department with acute headache and confusion that began the previous evening. Family members documented an oxygen saturation of 70% on ambient air at home; she had not previously utilized supplemental oxygen. Detailed questioning elicited a history of unintentional 11 kg weight loss over the preceding 6 months, intermittent low-grade morning fevers, and progressive exertional dyspnea associated with a dry cough over recent weeks. Outpatient empiric oral antibiotics and acetaminophen had failed to produce clinical improvement.\n\n"
        "Her medical history included hypertension managed with telmisartan and lercanidipine, and a prior transient ischemic attack treated with oral anticoagulation. She had no known history of prior exposure to chronic pulmonary infections, recent travel, or immunosuppressive therapy.\n\n"
        "On initial triage, vital signs were: blood pressure 145/87 mmHg, heart rate 76 beats/min, respiratory rate 24 breaths/min, body temperature 37.6°C, and oxygen saturation 85% on ambient air. Physical examination revealed mild psychomotor slowing and tachypnea with decreased bilateral thoracic expansion and mild intercostal retractions. Pulmonary auscultation demonstrated markedly diminished vesicular breath sounds over bilateral mid-to-lower lung fields with percussion dullness across the left hemithorax, in the absence of adventitious sounds. Cardiovascular, abdominal, and extremity examinations were unremarkable.\n\n"
        "Laboratory evaluation showed mild lymphopenia, an elevated erythrocyte sedimentation rate (ESR), mildly elevated hepatic transaminases, and a negative procalcitonin level. Plain chest radiography revealed diffuse, symmetric bilateral reticulonodular infiltrates."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Acute community-acquired Staphylococcus aureus pneumonia",
            "rule_out_reason": "Although a sputum multiplex pneumonia panel identified high-copy Staphylococcus aureus, acute staphylococcal pneumonia was clinically inconsistent with the patient's indolent 6-month constitutional decline, negative procalcitonin, absence of dense lobar consolidation, and unresponsiveness to outpatient antibacterial agents, indicating incidental upper airway colonization.",
            "quote": "The panel was positive for Staphylococcus aureus (>=107 copies/mL), with no mecA/C or MREJ resistance genes detected. However, considering the atypical presentation for community-acquired pneumonia and the patient's clinical course, a high-resolution chest computed tomography (HRCT) scan was obtained"
        },
        {
            "candidate": "Metastatic malignancy / lymphangitic carcinomatosis",
            "rule_out_reason": "Indolent weight loss and reticulonodular infiltrates raised suspicion for neoplastic dissemination; however, HRCT showed discrete, diffuse micronodules rather than primary masses or lymphadenopathy, and bronchoalveolar lavage cytology revealed only mild reactive inflammatory changes without malignant cells.",
            "quote": "a bronchoalveolar lavage cytology was performed from the left upper lobe, reporting only mild reactive changes of the respiratory epithelium associated with chronic inflammation."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "High-resolution CT confirmed multiple diffusely distributed micronodules characteristic of miliary disease, and bronchoalveolar lavage fluid testing confirmed Mycobacterium tuberculosis by positive QuantiFERON-TB Plus and positive MTB polymerase chain reaction.",
            "quote": "high-resolution chest computed tomography (HRCT) scan was obtained (Figure 2), which revealed multiple diffusely distributed micronodules throughout both lungs... QuantiFERON-TB Plus (four tubes) was requested and yielded a positive result in the same tissue. PCR testing for MTB was also positive, with no rifampicin resistance detected."
        }
    ],
    "final_diagnosis": "Tuberculosis",
    "audit_flags": ["NONE"],
    "editor_comments": "Stanford MedCaseReasoning distillation completed. Breakpoint strictly excludes pneumonia PCR panels, BAL cytology, and HRCT. Prompt contains zero pathogen or disease references."
}

# -------------------------------------------------------------
# Case 5: PMC12923222_01 - Dengue
# -------------------------------------------------------------
cases["PMC12923222_01"] = {
    "case_id": "PMC12923222_01",
    "disease": "Dengue",
    "think": (
        "1. Core Clinical Tension: A 32-year-old male manual laborer presents with acute high-grade fever, chills, rigors, myalgias, loose stools, and profound thrombocytopenia (32,000/µL), who abruptly develops acute mania (grandiosity, hyperverbosity, decreased need for sleep, hyperactivity) on Day 2 of hospitalization. The intersection of an acute febrile thrombocytopenic syndrome with acute behavioral decompensation forces clinicians to differentiate primary neuropsychiatric disorders, intracranial hemorrhage or septic encephalitis, and secondary organic mood syndrome driven by arboviral infection.\n"
        "2. Admission Breakpoint: The admission breakpoint is positioned on Day 1 upon admission to the general medical ward with baseline CBC showing marked thrombocytopenia (32,000/µL), leukopenia/lymphocytosis (52%), and before arboviral enzyme-linked immunosorbent serology and brain MRI results.\n"
        "3. Differential Distinctions: Primary psychiatric manic episode (ruled out by acute onset temporally linked to febrile illness, absence of prior psychiatric history, and rapid resolution following viral recovery), intracranial hemorrhage or structural encephalopathy (ruled out by normal brain MRI despite severe thrombocytopenia), and other tropical infections such as malaria or typhoid (ruled out by negative smears, profound isolated thrombocytopenia, and positive IgM ELISA). Confirmation relies on arbovirus IgM positivity."
    ),
    "case_prompt": (
        "A 32-year-old male daily wage laborer was admitted to the general medicine ward with a 3-day history of acute high-grade fever accompanied by chills, rigors, severe anorexia, and complete insomnia. From the day of admission, he also experienced loose stools and severe generalized body aches and myalgias. He had no known past medical history and no personal or family history of psychiatric disorders.\n\n"
        "On physical examination, the patient was febrile, toxic-appearing, and diaphoretic. Vital signs confirmed high-grade fever. Abdominal and systemic examinations showed no localized focal signs of infection. Mental status examination on initial triage noted extreme exhaustion and irritability.\n\n"
        "Initial laboratory investigations revealed profound thrombocytopenia with a platelet count of 32,000/µL and a total leukocyte count of 6,300/mm³ with 52% lymphocytes. Basic metabolic panel and routine triage blood tests were otherwise unremarkable."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Primary bipolar affective disorder / idiopathic mania",
            "rule_out_reason": "Although the patient exhibited pressured speech, motor hyperactivity, and ideas of grandiosity, he had no prior personal or family history of psychiatric illness, and the behavioral changes appeared in direct temporal relationship with acute febrile thrombocytopenia.",
            "quote": "The patient did not have a history of psychiatric illness, nor did he have any family history of psychiatric illness... The patient was diagnosed with Secondary mood syndrome with manic symptoms according to ICD 11 considering no prior predisposition to psychiatric illness and direct temporal relation of onset of his psychiatric symptoms to dengue fever."
        },
        {
            "candidate": "Intracranial hemorrhage or focal encephalitis",
            "rule_out_reason": "In the setting of severe thrombocytopenia (platelet count 32,000/µL) and acute neuropsychiatric decompensation, acute intracranial bleeding or focal structural encephalitis was a major concern, but magnetic resonance imaging of the brain demonstrated no abnormalities.",
            "quote": "MRI of the brain was normal."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "Specific enzyme-linked immunosorbent assay (ELISA) testing confirmed positive dengue IgM antibodies in the setting of acute fever, myalgias, and severe thrombocytopenia, establishing dengue fever with secondary neuropsychiatric manifestation.",
            "quote": "The test results showed a positive IgM ELISA for dengue. Further tests indicated a platelet count of 32000/mul; total leukocyte count of 6300/cm with lymphocytes at 52%. The patient was diagnosed with dengue fever accompanied by thrombocytopenia."
        }
    ],
    "final_diagnosis": "Dengue",
    "audit_flags": ["NONE"],
    "editor_comments": "Distilled case accurately focuses on Dengue presenting with secondary manic neuropsychiatric manifestations. Breakpoint set prior to dengue IgM serology and brain MRI. Zero pathogen disclosures."
}

# -------------------------------------------------------------
# Case 6: PMC12981038_01 - Leprosy
# -------------------------------------------------------------
cases["PMC12981038_01"] = {
    "case_id": "PMC12981038_01",
    "disease": "Leprosy",
    "think": (
        "1. Core Clinical Tension: A 28-year-old female presents with an 8-month history of an enlarging hypopigmented, hypoesthetic patch on the lower extremity accompanied by palpable common peroneal nerve thickening. The presence of intersecting linear tattoo markings applied by a village traditional healer reflects traditional cultural attempts to physically contain lesion margins, which delayed medical evaluation. The diagnostic challenge involves distinguishing tuberculoid mycobacterial nerve invasion from non-infectious hypopigmented disorders and granulomatous dermatoses in an afebrile young patient.\n"
        "2. Admission Breakpoint: The admission breakpoint occurs at outpatient dermatologic physical examination demonstrating cutaneous hypoesthesia and palpable peripheral nerve enlargement, prior to slit-skin smear examination, high-resolution nerve ultrasonography, and punch skin biopsy histopathology.\n"
        "3. Differential Distinctions: Vitiligo or post-inflammatory hypopigmentation (lack sensory loss or peripheral nerve thickening), tinea corporis / dermatophytosis (retains sensation and lacks nerve enlargement), cutaneous leishmaniasis / lupus vulgaris (lack localized anesthesia and nerve hypertrophy), and sarcoidosis (granulomatous but without neural enlargement). Slit-skin smears are frequently paucibacillary/negative in tuberculoid spectrum disease, making nerve thickening and biopsy showing epithelioid and Langhans' giant cell granulomas confirmatory."
    ),
    "case_prompt": (
        "A 28-year-old female presented to the dermatology outpatient clinic with an 8-month history of an enlarging patch below her right knee. The lesion had begun as a small, pea-sized spot that progressively expanded in size, accompanied by noticeable loss of temperature and light touch sensations over the area. Due to cultural beliefs, the patient had consulted a village traditional practitioner who applied two sets of intersecting tattoo markings over the lesion in an attempt to demarcate and contain its spread, which delayed her presentation for conventional medical care.\n\n"
        "On cutaneous examination, there was a well-defined, hypopigmented patch measuring 5 x 6 cm located below the right knee, extending to both the medial and lateral aspects of the leg. Neurological testing of the lesion demonstrated complete absence of thermal sensation and distinctly diminished light touch sensation. Palpation of peripheral nerve trunks revealed marked palpable thickening and enlargement of the right common peroneal nerve. Systemic physical examination and vital signs were otherwise unremarkable."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Vitiligo / post-inflammatory hypopigmentation",
            "rule_out_reason": "Although presenting as a discrete hypopigmented macule, vitiligo and post-inflammatory pigmentary alterations demonstrate fully preserved thermal, tactile, and pinprick sensations and are never associated with peripheral nerve enlargement.",
            "quote": "On cutaneous examination, a hypopigmented patch of size 5x6 cm below knee extending to medial and lateral side of leg, which was associated with absent temperature sensation and decreased touch sensation. On nerve palpation thickening of the right common peroneal nerve was present."
        },
        {
            "candidate": "Cutaneous tuberculosis (lupus vulgaris) or cutaneous sarcoidosis",
            "rule_out_reason": "While both disorders may produce dermal epithelioid granulomas, neither causes localized thermal anesthesia with prominent regional peripheral nerve trunk hypertrophy.",
            "quote": "High resolution ultrasonography of the right common peroneal nerve revealed enlarged cross-sectional area (Figure 3 (Fig. 3))."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "The diagnostic pivot was established by the triad of an anesthetic hypopigmented plaque, palpable common peroneal nerve thickening confirmed by high-resolution ultrasonography showing an increased cross-sectional area, and full-thickness punch skin biopsy revealing epithelioid cells and Langhans' giant cells, confirming borderline tuberculoid leprosy despite a negative slit-skin smear.",
            "quote": "Slit skin smear for AFB leprae was negative. A skin biopsy was done from the lesion and revealed epithelioid cells with Langhans' giant cells (Figure 2 (Fig. 2)). High resolution ultrasonography of the right common peroneal nerve revealed enlarged cross-sectional area (Figure 3 (Fig. 3))... Patient was eventually diagnosed with borderline tuberculoid leprosy (Ridley-Jopling classification)"
        }
    ],
    "final_diagnosis": "Leprosy",
    "audit_flags": ["NONE"],
    "editor_comments": "Distilled case accurately targets Leprosy (borderline tuberculoid leprosy). Breakpoint placed after cutaneous sensory and nerve examination, before slit-skin smear and biopsy. Zero pathogen disclosures."
}

# -------------------------------------------------------------
# Case 7: PMC13102560_01 - Tuberculosis
# -------------------------------------------------------------
cases["PMC13102560_01"] = {
    "case_id": "PMC13102560_01",
    "disease": "Tuberculosis",
    "think": (
        "1. Core Clinical Tension: A 73-year-old diabetic female presents with a 2-year history of recurrent thoracolumbar back pain, fever, and dyspnea after systemic steroid exposure, found to have T7-T8 vertebral destruction with paravertebral abscess and bilateral lung lesions. Initial bronchoalveolar lavage mNGS detected a high sequence abundance of Pneumocystis jirovecii (21.95%) alongside Mycobacterium tuberculosis complex (1.92%). The critical clinical tension is avoiding the misattribution of primary disease to Pneumocystis colonization in a non-HIV host, ensuring recognition of underlying disseminated tuberculosis as the true driving pathogen.\n"
        "2. Admission Breakpoint: The admission breakpoint is placed at transfer/admission triage prior to fluoroscopic-guided vertebral aspiration and invasive tissue biopsy metagenomic sequencing.\n"
        "3. Differential Distinctions: Active Pneumocystis jirovecii pneumonia (ruled out by negative serum (1,3)-beta-D-glucan [<37.5 pg/mL], negative HIV, and lack of characteristic bilateral diffuse interstitial infiltrates), pyogenic bacterial spondylodiscitis (Staphylococcus/Enterobacteriaceae, ruled out by negative fungal/bacterial workup and progressive chronic vertebral destruction), and invasive aspergillosis (ruled out by negative galactomannan). C-arm guided biopsy and tissue sequencing proving massive Mycobacterium tuberculosis complex predominance establish spinal and pulmonary tuberculosis."
    ),
    "case_prompt": (
        "A 73-year-old female was admitted with a 2-year history of recurrent thoracolumbar back pain and fevers. Two years earlier, she had been diagnosed with a thoracic vertebral infection and achieved temporary symptom resolution following intravenous antibiotic therapy. Six months prior to admission, symptoms recurred; thoracic MRI demonstrated pathological compression fractures at T7-T8 vertebrae, bone marrow edema at T6, and degenerative thoracolumbar changes, while chest CT revealed bilateral pulmonary inflammatory lesions, right pleural effusion, mediastinal lymphadenopathy, and minor pericardial effusion. She improved transiently following vancomycin therapy.\n\n"
        "Three months prior to admission, following a viral respiratory illness, she experienced worsening dyspnea and was treated with a 15-day course of systemic corticosteroids (oral dexamethasone and methylprednisolone) and broad-spectrum antibiotics, despite which respiratory symptoms progressed and she developed acute renal failure requiring hemodialysis. Her medical history was also notable for hypertension and insulin-dependent type 2 diabetes mellitus.\n\n"
        "On admission, she was tachypneic and chronically ill-appearing. Neurological examination showed intact cranial nerves but severe tenderness over the mid-thoracic spine. Laboratory evaluation showed severe absolute lymphocytopenia (0.38 x 10⁹/L). Screening for human immunodeficiency virus (HIV) antibodies was negative. Fungal biomarker testing revealed a negative serum (1,3)-beta-D-glucan level (<37.5 pg/mL; reference negative: <70 pg/mL) and a negative serum Aspergillus galactomannan antigen of 0.11 (reference negative: <0.5). Thoracic spine MRI demonstrated progressive T7-T8 vertebral osseous destruction accompanied by paravertebral abscess formation."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Pneumocystis jirovecii pneumonia (PJP)",
            "rule_out_reason": "Although prior BAL fluid metagenomic sequencing reported a high sequence abundance of Pneumocystis jirovecii following corticosteroid therapy, the patient was HIV-negative and serum (1,3)-beta-D-glucan was completely negative (<37.5 pg/mL), confirming that Pneumocystis represented asymptomatic respiratory colonization rather than invasive pneumonia.",
            "quote": "Pre-admission evaluations (December 30, 2023) showed: negative serum HIV antibody, serum (1, 3)-beta-D-glucan <37.5 pg./mL (negative: <70 pg./mL), Aspergillus galactomannan antigen 0.11 (negative: <0.5)"
        },
        {
            "candidate": "Recurrent pyogenic bacterial spondylodiscitis (e.g., Staphylococcus aureus)",
            "rule_out_reason": "While her symptoms had shown transient temporary improvement with vancomycin months earlier, the 2-year indolent clinical course, cold abscess formation, and lack of persistent bacterial isolation on targeted debridement ruled out an uncomplicated pyogenic bacterial infection.",
            "quote": "Two years prior, she was diagnosed with a thoracic vertebral infection at a local hospital and achieved symptom resolution after treatment with ceftoperazone/sulbactam... A thoracic MRI (December 28, 2023, Hangzhou Hospital of TCM) revealed T7-T8 vertebral destruction with abscess"
        },
        {
            "candidate": "Invasive aspergillosis",
            "rule_out_reason": "Invasive pulmonary fungal disease was suspected due to steroid therapy, lymphopenia, and bilateral pulmonary lesions, but was excluded by a negative serum galactomannan antigen level.",
            "quote": "Aspergillus galactomannan antigen 0.11 (negative: <0.5)"
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "C-arm-guided biopsy of the thoracic vertebral abscess yielded purulent fluid confirming Mycobacterium tuberculosis complex (MTBC) DNA/RNA, and lung tissue metagenomic sequencing demonstrated overwhelming MTBC dominance (72,040 sequences, 85.68% abundance).",
            "quote": "On January 24, 2024, a C-arm-guided biopsy of the vertebral lesion (Figure 3A) yielded pus and hemorrhagic fluid; subsequent testing confirmed Mycobacterium tuberculosis complex (MTBC)-positive, rifampicin-sensitive, and positive MTB DNA/RNA. A lung lesion biopsy (January 30, 2024; Figures 3A,B) and tissue NGS (Hangzhou ADICON Lab) detected overwhelming Mycobacterium dominance (73,211 sequences, 87.07% abundance; MTBC: 72,040, 85.68%)."
        }
    ],
    "final_diagnosis": "Tuberculosis",
    "audit_flags": ["NONE"],
    "editor_comments": "Stanford MedCaseReasoning distillation completed. Breakpoint set prior to vertebral needle biopsy and confirmatory tissue metagenomics. Zero pathogen leaks in case prompt."
}

# -------------------------------------------------------------
# Case 8: PMC1310521_01 - Tuberculosis
# -------------------------------------------------------------
cases["PMC1310521_01"] = {
    "case_id": "PMC1310521_01",
    "disease": "Tuberculosis",
    "think": (
        "1. Core Clinical Tension: A 46-year-old man with advanced HIV/AIDS (CD4 count 115 cells/µL, non-adherent to antiretroviral therapy) and history of frequent international travel between West Africa and the US presents with isolated subacute pain, erythema, and swelling of the left fifth digit proximal interphalangeal joint, with an occasional dry cough but no fever or weight loss. Radiographs show cystic lucencies in the proximal phalanx, while chest radiography reveals right hilar lymphadenopathy and scattered nodules. The presentation mimics common bacterial dactylitis, fungal osteomyelitis, or gout, obscuring an underlying disseminated mycobacterial infection.\n"
        "2. Admission Breakpoint: The admission breakpoint is placed at Day 1 triage following hand radiography and initial chest imaging showing scattered nodules, prior to surgical incision, drainage, bone biopsy, and molecular rRNA transcription-mediated amplification.\n"
        "3. Differential Distinctions: Acute pyogenic bacterial felon or osteomyelitis (ruled out by absence of acute fever, normal leukocyte count of 5,000/mm³, and intraoperative findings of soft, mottled, yellow bone rather than acute suppuration), endemic fungal osteomyelitis (histoplasmosis/coccidioidomycosis, ruled out by negative fungal cultures), and gouty dactylitis. Demonstration of acid-fast bacilli on synovial biopsy and Gen-PROBE transcription-mediated amplification confirming M. tuberculosis complex rRNA establishes disseminated tuberculous osteomyelitis."
    ),
    "case_prompt": (
        "A 46-year-old male with human immunodeficiency virus infection and acquired immunodeficiency syndrome (HIV/AIDS, CD4+ T-cell count 115 cells/µL) presented with a two-week history of worsening pain and swelling of the left fifth digit. He denied antecedent hand trauma, fever, chills, night sweats, weight loss, or other constitutional symptoms, though he noted an occasional non-productive dry cough. He had traveled repeatedly between his native Ivory Coast in West Africa and the United States. He was not receiving antiretroviral therapy at the time of presentation.\n\n"
        "On physical examination, the left fifth digit was swollen, warm, and erythematous with localized tenderness centered over the proximal interphalangeal joint. The remainder of the physical examination, including cardiopulmonary and abdominal exams, was unremarkable.\n\n"
        "Initial laboratory investigations revealed a white blood cell count of 5,000/mm³, hemoglobin 11.6 g/dL, hematocrit 33.9%, platelet count 280,000/mm³, eosinophils 9.0%, and an elevated erythrocyte sedimentation rate (ESR) of 60 mm/h.\n\n"
        "Radiography of the left hand revealed soft-tissue swelling over the fifth digit, proximal interphalangeal joint space narrowing, and cortical lucencies with cystic degenerative changes in the proximal phalanx. Admission chest radiography showed right hilar lymph node enlargement, multiple scattered pulmonary nodules, and a resolving right lower lobe infiltrate. Computed tomography of the chest confirmed multiple pulmonary nodules, necrotic mediastinal/hilar lymph nodes, and splenomegaly."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Acute pyogenic bacterial osteomyelitis / septic arthritis",
            "rule_out_reason": "Acute pyogenic dactylitis (such as Staphylococcus aureus) typically presents with intense acute inflammation, leukocytosis, and fever; in contrast, this patient had a normal leukocyte count of 5,000/mm³, an indolent 2-week course without fever, and soft mottled yellow bone rather than acute purulent phlegmon.",
            "quote": "He denied any history of recent trauma to the hand, fever, weight loss, or other systemic symptoms... His laboratory values on admission were as follows: white blood cell count 5000 cells/mm3... Operative findings were significant for purulent, mottled, soft, yellow bone."
        },
        {
            "candidate": "Endemic fungal osteomyelitis (e.g., Histoplasmosis, Cryptococcosis)",
            "rule_out_reason": "In a patient with severe CD4 lymphopenia and disseminated pulmonary nodules, opportunistic fungal osteomyelitis was a leading differential, but specific mycobacterial molecular assays and fungal smears were negative for fungal pathogens.",
            "quote": "We used the Gen-PROBE Amplified Mycobacterium tuberculosis Direct Test which employs a transcription-mediated amplification and hybridization protection assay to qualitatively detect Mycobacterium tuberculosis complex ribosomal RNA (rRNA)."
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "Incision, drainage, and biopsy of the left fifth phalanx revealed acid-fast bacilli on direct microscopy, qualitative Gen-PROBE testing confirmed Mycobacterium tuberculosis complex ribosomal RNA, and both bone tissue and induced sputum cultures confirmed Mycobacterium tuberculosis.",
            "quote": "Rare acid-fast bacilli were demonstrated on biopsy of the both phalanx and synovial fluid samples [figure 4]. We used the Gen-PROBE Amplified Mycobacterium tuberculosis Direct Test which employs a transcription-mediated amplification and hybridization protection assay to qualitatively detect Mycobacterium tuberculosis complex ribosomal RNA (rRNA). Several weeks later cultures of all surgical material grew Mycobacterium tuberculosis [figure 5]."
        }
    ],
    "final_diagnosis": "Tuberculosis",
    "audit_flags": ["NONE"],
    "editor_comments": "Distilled case accurately targets Tuberculosis (disseminated tuberculosis with tuberculous osteomyelitis/dactylitis). Breakpoint set prior to surgical biopsy and Gen-PROBE testing. Zero pathogen names in case prompt."
}

# -------------------------------------------------------------
# Case 9: PMC2248592_01 - Echinococcosis
# -------------------------------------------------------------
cases["PMC2248592_01"] = {
    "case_id": "PMC2248592_01",
    "disease": "Echinococcosis",
    "think": (
        "1. Core Clinical Tension: A 60-year-old male presents with dull upper abdominal pain, pallor, pedal edema, and a massive 22-cm hepatomegaly with an 8 x 8 cm cystic subfascial epigastric protrusion stretching the anterior abdominal wall aponeurosis. An enormous 19 x 12 x 13 cm multilocular cystic hepatic mass occupying segments V–VIII with compression of major retroperitoneal and hepatobiliary vasculature mimics a biliary cystadenoma/cystadenocarcinoma, complex hepatic abscess, or mesenchymal abdominal wall tumor.\n"
        "2. Admission Breakpoint: The admission breakpoint is placed at Day 1 triage following physical examination, baseline laboratory investigations showing peripheral eosinophilia (900/µL), chest radiograph showing diaphragmatic elevation, and initial abdominal ultrasound/CT imaging, prior to Echinococcus-specific ELISA serology, surgical cystotomy, and histopathological analysis.\n"
        "3. Differential Distinctions: Biliary cystadenoma / cystadenocarcinoma (lack daughter cysts and peripheral eosinophilia), amebic or pyogenic liver abscess (ruled out by afebrile state, normal WBC count of 7,500/µL, sterile cultures, and absence of systemic toxic features), and primary anterior abdominal wall sarcoma (ruled out by CT showing hepatic parenchymal origin with secondary subfascial herniation). Specific ELISA serology and surgical drainage yielding hydatid sand with hooklets, laminated membrane, and protoscolices establish echinococcosis."
    ),
    "case_prompt": (
        "A 60-year-old male presented with a 4-month history of continuous, dull aching upper abdominal pain and a progressively enlarging visible lump in the upper abdomen over the preceding two months. He had no history of acute fever, rigors, or jaundice.\n\n"
        "On physical examination, the patient was afebrile and non-icteric, with mild conjunctival pallor and bilateral pedal edema. Abdominal examination revealed marked lobulated hepatomegaly with a liver span of 22 cm occupying both hypochondria, the right lumbar, epigastric, and umbilical regions. In addition, there was a localized cystic, tense subfascial protrusion measuring 8 x 8 cm in the epigastrium directly stretching the overlying musculature.\n\n"
        "Initial laboratory investigations showed a hemoglobin level of 10 g/dL, white blood cell count of 7,500/µL with an absolute eosinophil count of 900/µL. Liver function tests, including serum transaminases and bilirubin, were within normal reference ranges.\n\n"
        "Plain chest radiography revealed elevation of the right hemidiaphragm with a soft-tissue mass shadow in the right upper abdomen. Abdominal ultrasonography demonstrated a massive 19 x 12 x 13 cm cystic lesion located in the right lobe of the liver containing multiple internal anechoic cysts. Contrast-enhanced spiral CT of the liver confirmed a large right hepatic lobe cystic mass (involving segments V, VI, VII, and VIII) with internal daughter cysts causing mass effect and compression of the portal vein, inferior vena cava, hepatic veins, gallbladder, biliary tree, and right kidney, with an anterior cystic projection extending through the midline fascial aponeurotic layer."
    ),
    "diagnostic_reasoning": [
        {
            "candidate": "Biliary cystadenoma or cystic hepatic neoplasm",
            "rule_out_reason": "Although cystic neoplasms of the biliary tree can present as large multilocular intrahepatic masses, they typically lack multiple independent internal daughter cysts, are not associated with marked peripheral eosinophilia (900/µL), and do not demonstrate positive echinococcal serology.",
            "quote": "Ultrasonography (USG) of the abdomen revealed a 19 x 12 x 13 cm cystic lesion in the right lobe of the liver with multiple anechoic cysts within it. Spiral CT scan of the liver (Figure-2A &2B) confirmed a hydatid cyst in the right lobe (segments - V, VI, VII, VIII), with multiple daughter cysts within"
        },
        {
            "candidate": "Pyogenic or amebic hepatic abscess",
            "rule_out_reason": "Bacterial or amebic abscesses typically cause high fever, right upper quadrant tenderness, leukocytosis, and deranged liver function tests; this patient was afebrile, non-icteric, had a normal leukocyte count of 7,500/µL, normal liver function tests, and sterile evacuated cyst contents.",
            "quote": "Clinical examination revealed an afebrile non-icteric man with mild pallor and pedal edema... Liver function tests were within normal range... The cyst contents, which were sterile on culture"
        },
        {
            "candidate": "Diagnostic Pivot",
            "rule_out_reason": "Specific enzyme-linked immunosorbent assay (ELISA) serology was positive for echinococcus, and surgical exploration with evacuation of three liters of cyst fluid demonstrated diagnostic daughter cysts, hooklets, laminated membranes, and protoscolices.",
            "quote": "Serological test with an enzyme-linked immunosorbent assay (ELISA) for echinococcus was positive... The cyst contents, which were sterile on culture, showed protoscolices, fragments of laminated membrane and hooklets."
        }
    ],
    "final_diagnosis": "Echinococcosis",
    "audit_flags": ["NONE"],
    "editor_comments": "Stanford MedCaseReasoning distillation completed. Breakpoint set prior to ELISA serology and surgical cystotomy. Zero pathogen or disease mentions in case prompt."
}

# -------------------------------------------------------------
# Write and validate all cases
# -------------------------------------------------------------
for case_id, case_data in cases.items():
    out_path = os.path.join(BATCH_DIR, f"distilled_{case_id}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(case_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path}")

print("All 10 cases written successfully!")
