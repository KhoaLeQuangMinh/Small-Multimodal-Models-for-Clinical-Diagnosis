# Clinical Diagnostic Benchmark Suite (`benchmarks/`)

## 1. Overview
This directory contains the standalone evaluation and knowledge graph indexing runners used to assess diagnostic performance of Small Language Models (SLMs) on masked tropical disease cases.

All benchmarks evaluate against the 365-case admission cohort (`data/test_masked_cases.jsonl`) across 22 canonical tropical diseases.

---

## 2. Directory Layout

```text
benchmarks/
├── README.md                                       # CLI usage guide for all evaluation tiers
├── benchmark_baseline.py                           # Tier 0: Zero-shot baseline SLM diagnostic runner
├── benchmark_rag.py                                # Tiers 1 & 2: LightRAG (Graph & Hybrid) runner
├── benchmark_rag_slot.py                           # Phase 1: Clinical slot keyword LightRAG runner
├── benchmark_retrieval.py                          # Knowledge Graph retrieval hit-rate evaluator
├── build_clinical_kg.py                            # LightRAG biomedical KG index builder
├── prepare_test_masked.py                          # Cohort splitter & masked test cohort builder
└── results/                                        # Master benchmark result CSV tables
    ├── baseline_results.csv                        # Tier 0 evaluation results
    ├── rag_tier1_graph_only_results.csv            # Tier 1 Graph-Only evaluation results
    ├── rag_tier1_slot_prompt_results.csv           # Tier 1 Slot-Prompt evaluation results
    ├── rag_tier2_hybrid_results.csv                # Tier 2 Hybrid (2 chunks) results
    ├── rag_tier2_hybrid_10chunks_results.csv       # Tier 2 Hybrid (10 chunks) results
    ├── retrieval_benchmark_results.csv             # Retrieval hit-rate results (clues mode)
    └── retrieval_benchmark_ollama_results.csv      # Retrieval hit-rate results (ollama mode)
```

---

## 3. CLI Execution Reference

Ensure your local virtual environment is activated and Ollama is running (`ollama serve`).

### Tier 0: Zero-Shot Baseline (No RAG)
Runs unaugmented SLM diagnostic inference:
```bash
# Run on all 365 test cases:
python3 benchmarks/benchmark_baseline.py

# Run on a 5-case trial:
MAX_TEST_CASES=5 python3 benchmarks/benchmark_baseline.py
```

### Tier 1: Graph-Only LightRAG
Augments the prompt with retrieved relational knowledge triples:
```bash
# Run on all 365 test cases:
python3 benchmarks/benchmark_rag.py --tier 1

# Run on a quick 5-case trial:
python3 benchmarks/benchmark_rag.py --tier 1 --max-cases 5
```

### Tier 2: Hybrid LightRAG (Graph + Document Chunks)
Augments the prompt with both graph triples and top document chunks:
```bash
# Run standard Tier 2 (2 text chunks):
python3 benchmarks/benchmark_rag.py --tier 2 --top-chunks 2 --max-cases 5

# Run 10-chunk Tier 2:
python3 benchmarks/benchmark_rag.py --tier 2 --top-chunks 10 --max-cases 5
```

### Slot-Filling LightRAG Evaluation
Uses structured clinical slot extraction (syndromes, signs, exposures) to query the knowledge graph:
```bash
python3 benchmarks/benchmark_rag_slot.py --tier 1 --max-cases 5
```

### Knowledge Graph Retrieval Hit-Rate Evaluation
Evaluates recall and hit-rate of graph entity retrieval:
```bash
# Fast offline evaluation using syndromic clues:
KEYWORD_MODE=clues python3 benchmarks/benchmark_retrieval.py

# End-to-end evaluation with local Ollama keyword extraction:
KEYWORD_MODE=ollama python3 benchmarks/benchmark_retrieval.py
```

### Cohort Preparation & Extraction Utility
Prepares or refreshes `data/test_masked_cases.jsonl`:
```bash
python3 benchmarks/prepare_test_masked.py
```

---

## 4. Evaluation Metrics
- **Top-1 Accuracy:** The single most likely primary diagnosis matches the ground truth.
- **Top-3 Differential Coverage:** The ground truth appears anywhere in the Top-3 differential list.
- **Tolerant Differential Paradigm:** See [`docs/RESULT.md`](../docs/RESULT.md) for full methodology and detailed benchmark comparisons.
