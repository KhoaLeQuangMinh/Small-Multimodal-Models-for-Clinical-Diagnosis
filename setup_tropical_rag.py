import os
import csv
import asyncio
from functools import partial
from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

# 1. Configuration
WORKING_DIR = "./tropical_kg_storage"
os.makedirs(WORKING_DIR, exist_ok=True)

# Select local Ollama LLM (tagged as 'gemma4:e4b' or 'llama3.2:latest')
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e4b")
EMBEDDING_MODEL = "nomic-embed-text"
MAX_CASES_TO_INDEX = int(os.getenv("MAX_CASES", "1"))

async def main():
    print(f"--- Initializing LightRAG with LLM: {LLM_MODEL} & Embedding: {EMBEDDING_MODEL} ---")
    
    # 2. Initialize LightRAG with local Ollama
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        llm_model_name=LLM_MODEL,
        llm_model_max_async=1,  # Keep 1 for local Ollama to avoid memory contention
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=partial(ollama_embed.func, embed_model=EMBEDDING_MODEL)
        )
    )

    # 3. Initialize LightRAG storages (required in current LightRAG versions)
    print("Initializing LightRAG storages...")
    await rag.initialize_storages()

    # 4. Path to filtered tropical clinical cases
    cases_file = "MultiCaRe_Dataset/Demos/medical_datasets/tropical_infectious_diseases_cohort/cases.csv"
    if not os.path.exists(cases_file):
        print(f"Error: {cases_file} not found! Please run explore_dataset.ipynb first.")
        return

    print(f"\nIngesting first {MAX_CASES_TO_INDEX} tropical clinical cases into Knowledge Graph...")
    with open(cases_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= MAX_CASES_TO_INDEX:
                break
            patient_id = row.get("patient_id", i)
            age = row.get("age", "N/A")
            gender = row.get("gender", "N/A")
            case_text = f"Patient ID {patient_id} (Age: {age}, Gender: {gender}): {row['case_text']}"
            
            print(f"Indexing Case {i+1}/{MAX_CASES_TO_INDEX} (Patient {patient_id})...")
            await rag.ainsert(case_text)

    print(f"\nKnowledge Graph successfully built in {WORKING_DIR}!")

    # 5. Run a test clinical query in Hybrid mode
    test_query = "What are the common symptoms, lab abnormalities, and risk factors for Dengue fever and Tuberculosis in tropical patients?"
    print(f"\nQuerying: {test_query}\n")
    response = await rag.aquery(test_query, param=QueryParam(mode="hybrid"))
    print("--- LightRAG Diagnostic Response ---")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())