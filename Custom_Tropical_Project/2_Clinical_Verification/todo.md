# 📋 Dataset Download & Setup Guide

This folder holds the **clinically verified multimodal tropical diseases dataset** used for SMM fine-tuning and Knowledge Graph construction (LightRAG).

Because this dataset contains large JSONL records and 3,013 medical image panels, the data files and archives are **ignored by Git** to keep the repository lightweight.

Follow the steps below to download and set up the dataset locally.

---

## 🔗 Download Link

Download the dataset directly from Kaggle:
👉 **[Kaggle: Small Multimodal Project Dataset](https://www.kaggle.com/datasets/kisokoghan/small-multimodal-project-dataset)**

> Direct URL:
> `https://www.kaggle.com/datasets/kisokoghan/small-multimodal-project-dataset`

---

## 🛠️ Step-by-Step Setup Instructions

### 1. Download the Dataset
Click the **Download (63 MB)** button on the Kaggle dataset page to obtain `archive.zip` (or use the Kaggle CLI):
```bash
kaggle datasets download -d kisokoghan/small-multimodal-project-dataset
```

### 2. Place Archive in this Directory
Move the downloaded zip file into this directory:
```text
Project_Dr. Tran Duc Khanh/Datasets/Custom_Tropical_Project/2_Clinical_Verification/
```

### 3. Unzip the Archive
Unzip the downloaded file in this directory:
```bash
# From inside 2_Clinical_Verification/:
unzip archive.zip
```

### 4. Verify the Extracted Structure
After extracting, ensure the directory structure looks like this:
```text
2_Clinical_Verification/
├── todo.md                     # This instruction file (tracked in git)
├── archive.zip                 # Downloaded archive (optional to delete)
└── kaggle_partA/               # [Git-ignored active dataset]
    ├── README.md               # Dataset schema and metadata description
    ├── partA_final.jsonl       # 1,797 clinically audited cases
    └── images/                 # 3,013 clinical image panels (.webp)
```

### 5. (Optional) Reclaim Disk Space
Once `kaggle_partA` is verified and unzipped, you can safely delete `archive.zip`:
```bash
rm archive.zip
```
