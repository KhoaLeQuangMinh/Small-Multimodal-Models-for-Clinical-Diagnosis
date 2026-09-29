# Small-Multimodal-Models-for-Clinical-Diagnosis

Project repository for **Tropical Infectious Diseases Clinical Diagnosis** using Small Multimodal Models (SMMs) and Knowledge Graph RAG (LightRAG).

Supervised by: **Dr. Tran Duc Khanh** (Faculty of Engineering, Vietnamese-German University).

---

## 🧭 Suggested Reading & Workflow Order

If you are joining or reviewing this project, follow this recommended sequence:

| Step | Section / Directory | What It Covers | Key Files to Read / Run |
| :---: | :--- | :--- | :--- |
| **1** | [📖 **`4_Literature_and_Materials/`**](#4-4_literature_and_materials-foundational-literature) | Theoretical foundation: MultiCaRe paper, LLM clinical scoping review, LightRAG paper | `Materials/*.pdf` |
| **2** | [🏛️ **`Official_MultiCaRe/`**](#2-official_multicare-upstream-framework--reference) | Upstream reference: How 98k PMC cases and 140+ medical ontology classes were created | `README.md`, `MultiCaRe_Taxonomy/` |
| **3** | [🔬 **`1_Data_Exploration/`**](#1-1_data_exploration-cohort-derivation--eda) | Cohort extraction: How 22 tropical disease classes were filtered using MeSH terms | `explore_dataset.ipynb` |
| **4** | [📥 **`2_Clinical_Verification/`**](#2-2_clinical_verification-verified-benchmark--download) | **Action Required:** Download the audited, clean dataset (1,797 cases + 3,013 images) | `todo.md`, `kaggle_partA/README.md` |
| **5** | [🧠 **`3_LightRAG_Knowledge_Graph/`**](#3-3_lightrag_knowledge_graph-knowledge-graph-construction) | Active implementation: Build and query the clinical Knowledge Graph with Ollama/Colab | `tropical_lightrag_colab.ipynb` |

---

## 📂 Full Directory Tree & Component Explanations

```text
Datasets/                                                  # Root of this repository
├── README.md                                              # [You are here] Master guide, reading order, and index
├── requirements.txt                                       # Core Python dependencies (LightRAG, torch, transformers)
├── .gitignore                                             # Prevents large images, parquet, and .zip archives from leaking into Git
│
├── 🛠️ Custom_Tropical_Project/                             # PRIMARY WORK: Custom tropical disease pipeline & benchmark
│   │
│   ├── 1_Data_Exploration/                                # [READING STEP 3] Exploratory data analysis & filtering logic
│   │   ├── explore_dataset.ipynb                          # MeSH C01/C02/C03 tree filtering pipeline (extracts tropical candidate cohort)
│   │   └── explore_tropical_dataset.ipynb                 # Visualizes class frequencies, distributions, and initial imbalance
│   │
│   ├── 2_Clinical_Verification/                           # [READING STEP 4 - ACTION REQUIRED] Clinically audited benchmark
│   │   ├── todo.md                                        # Step-by-step Kaggle download & unzip instructions (Tracked in Git)
│   │   ├── archive.zip                                    # [Git-ignored] Raw downloaded archive from Kaggle (~63 MB)
│   │   └── kaggle_partA/                                  # [Git-ignored] Extracted clean, active dataset
│   │       ├── README.md                                  # Schema specification, field definitions, and license breakdown
│   │       ├── partA_final.jsonl                          # 1,797 clinically verified cases (ground-truth diagnoses & evidence quotes)
│   │       └── images/                                    # 3,013 verified multimodal image panels (.webp format)
│   │
│   ├── 3_LightRAG_Knowledge_Graph/                        # [READING STEP 5] Knowledge Graph construction & clinical retrieval
│   │   ├── tropical_lightrag_mock_llm.ipynb               # Fast Decoupled KG builder (Pre-extracted triplets + bge-m3, ~10 min total)
│   │   ├── tropical_lightrag_colab.ipynb                  # End-to-end KG builder with local Ollama Qwen 3B
│   │   ├── setup_tropical_rag.py                          # CLI runner for local LightRAG ingestion & testing
│   │   ├── kg_extraction/                                 # Decoupled subagent extraction pipeline
│   │   │   ├── HOW_TO_RUN_IN_ANTIGRAVITY.md               # Step-by-step operational guide for teammates
│   │   │   ├── runner.md                                  # Antigravity driving prompt for parallel triplet extraction
│   │   │   ├── prompt.md                                  # Reference LightRAG triplet extraction prompt
│   │   │   ├── prepare_case_prompts.py                    # Generates 1,797 prompt files in case_prompts/
│   │   │   ├── validate_triplets.py                       # Validates and summarizes extracted triplet JSON files
│   │   │   ├── case_prompts/                              # [Git-ignored] 1,797 self-contained prompt files
│   │   │   └── extracted_triplets/                        # [Git-ignored] Extracted entities and relationships per case
│   │   ├── tropical_kg_storage/                           # [Git-ignored] Local Ollama graph database & vector index (GraphML + JSON)
│   │   ├── tropical_kg_gemini_storage/                    # [Git-ignored] Cloud graph storage cache
│   │   └── test_storage/                                  # [Git-ignored] Scratch folder for quick unit tests
│   │
│   └── 4_Literature_and_Materials/                        # [READING STEP 1] Foundational literature & project references
│       └── Materials/
│           ├── An Open-Source Clinical Case Dataset...pdf # MultiCaRe data descriptor paper (MDPI Data 2025)
│           ├── LLM Diagnosis Review.pdf                   # Scoping review on LLMs in disease diagnosis (Zhou et al., 2024)
│           └── LightRAG.pdf                               # LightRAG: Simple and Fast Knowledge Graph RAG (arXiv 2024)
│
└── 🏛️ Official_MultiCaRe/                                 # [READING STEP 2 - REFERENCE] Upstream MultiCaRe framework
    ├── README.md                                          # Upstream MultiCaRe documentation and API quickstart
    ├── LICENSE                                            # CC0 1.0 Universal open-source dataset license
    │
    ├── whole_multicare_dataset/                           # [Git-ignored, 3.0 GB] Raw upstream database (98,641 PMC articles)
    │   ├── cases.parquet                                  # Unfiltered patient narratives across all medical specialties
    │   ├── case_images.parquet                            # Image-to-case relational table
    │   ├── captions_and_labels.csv                        # Image captions with extracted MeSH labels
    │   ├── abstracts.parquet                              # PubMed article abstracts
    │   ├── metadata.parquet                               # Publication journals, authors, DOIs, and dates
    │   ├── data_dictionary.csv                            # Schema definitions for raw parquet tables
    │   └── PMC1/ ... PMC9/                                # Full raw image directory hierarchy (139,000+ images)
    │
    ├── Dataset_Creation_Process/                          # Upstream notebooks showing how MultiCaRe was scraped from PMC
    │   ├── 1_How_to_Query_Case_Reports_from_PubMed_using_BioPython.ipynb
    │   ├── 2_Data_Extraction_from_PMC's_Case_Reports.ipynb
    │   ├── 3_Image_Preprocessing.ipynb
    │   ├── 4_Turning_Captions_into_Image_Labels.ipynb
    │   └── README.md
    │
    ├── MultiCaRe_Taxonomy/                                # 140+ medical image ontology classes and formal axioms
    │   ├── GT_MCR_TX.owx                                  # Ground-truth OWL ontology file
    │   ├── ML_MCR_TX.owx                                  # Machine-learning aligned ontology
    │   ├── MultiCaRe Taxonomy Documentation.pdf           # Visual documentation of hierarchical medical concepts
    │   ├── image_data_per_class.csv                       # Image distribution per taxonomy category
    │   └── input_format/                                  # Input syntax and schemas for OWL ontology files
    │
    ├── MultiCaReClassifier/                               # Upstream baseline CNN/ViT image classifiers
    │   ├── pipeline.py                                    # Baseline PyTorch inference & evaluation script
    │   ├── metrics_per_model.csv                          # Accuracy, macro F1, and AUC for baseline vision models
    │   ├── model_training/                                # Upstream training code & splits
    │   │   ├── training.ipynb
    │   │   └── training_data_fourth_version.csv
    │   └── cofunsion_matrices/                            # Per-modality confusion matrix evaluation plots
    │
    └── Demos/                                             # Upstream demo notebooks from the original authors
        ├── customized_subset_creation.ipynb               # Demonstrates the multiversity library filter syntax
        └── create_image_classification_datasets.ipynb     # Prepares classification splits for torchvision
```

---

## 📥 Required Dataset Downloads (TODO)

Because medical datasets and high-resolution image panels exceed GitHub file size limits, data folders are **Git-ignored** and must be downloaded separately:

### 1. Active Verified Benchmark (`kaggle_partA`) — **REQUIRED**
This is the cleaned, audited dataset required to run LightRAG and train small multimodal backbones.
* **Download URL:** [Kaggle: Small Multimodal Project Dataset](https://www.kaggle.com/datasets/kisokoghan/small-multimodal-project-dataset)
* **Setup Guide:** Follow the step-by-step instructions in [`Custom_Tropical_Project/2_Clinical_Verification/todo.md`](Custom_Tropical_Project/2_Clinical_Verification/todo.md).
* **Terminal Setup:**
  ```bash
  cd Custom_Tropical_Project/2_Clinical_Verification/
  # Move your downloaded archive.zip here, then:
  unzip archive.zip
  # Verifies kaggle_partA/ containing partA_final.jsonl and images/
  ```

### 2. Full Upstream MultiCaRe Dataset (`whole_multicare_dataset`) — *OPTIONAL*
Only needed if you plan to re-filter or scrape outside the 22 tropical disease classes across the general 98,000 cases.
* **Source:** [Zenodo (DOI: 10.5281/zenodo.10079369)](https://doi.org/10.5281/zenodo.10079369) or Hugging Face (`mauro-nievoff/multicare`).
* **Target Location:** Unzip directly into `Official_MultiCaRe/whole_multicare_dataset/`.

---

## 🚀 Quickstart

1. **Set Up Python Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download Verified Clinical Dataset**:
   Follow instructions in [`Custom_Tropical_Project/2_Clinical_Verification/todo.md`](Custom_Tropical_Project/2_Clinical_Verification/todo.md) to place `kaggle_partA/` in place.

3. **Run LightRAG Knowledge Graph**:
   Open [`Custom_Tropical_Project/3_LightRAG_Knowledge_Graph/tropical_lightrag_colab.ipynb`](Custom_Tropical_Project/3_LightRAG_Knowledge_Graph/tropical_lightrag_colab.ipynb) on Google Colab or run locally using Apple Silicon Mac / Ollama.