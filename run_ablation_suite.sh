#!/bin/bash
set -e

PYTHON="/opt/anaconda3/envs/smm/bin/python"
SCRIPT="stage4_constrained_inference/benchmark_stage4_cot.py"

echo "========================================================================"
echo "      STARTING DUAL-BRAIN TARGETED ABLATION BENCHMARK SUITE (N=365)"
echo "========================================================================"

# Experiment 1: New Knowledge Graph ONLY + CoT
echo ""
echo ">>> [1/3] Running Experiment 1: New Knowledge Graph ONLY + CoT"
echo ">>> Parameters: --top-k-twins 0 --top-k-triples 15 --prompt-mode cot"
$PYTHON $SCRIPT \
  --top-k-twins 0 \
  --top-k-triples 15 \
  --prompt-mode cot \
  --output-csv stage4_constrained_inference/ablation_new_kg_only_cot.csv

# Experiment 2: Patient Memory ONLY — Direct Prompt (No CoT)
echo ""
echo ">>> [2/3] Running Experiment 2: Patient Memory ONLY — Direct Prompt (No CoT)"
echo ">>> Parameters: --top-k-twins 2 --top-k-triples 0 --prompt-mode direct"
$PYTHON $SCRIPT \
  --top-k-twins 2 \
  --top-k-triples 0 \
  --prompt-mode direct \
  --output-csv stage4_constrained_inference/ablation_patient_memory_direct.csv

# Experiment 3: Patient Memory ONLY — WITH CoT
echo ""
echo ">>> [3/3] Running Experiment 3: Patient Memory ONLY — WITH CoT"
echo ">>> Parameters: --top-k-twins 2 --top-k-triples 0 --prompt-mode cot"
$PYTHON $SCRIPT \
  --top-k-twins 2 \
  --top-k-triples 0 \
  --prompt-mode cot \
  --output-csv stage4_constrained_inference/ablation_patient_memory_cot.csv

echo ""
echo "========================================================================"
echo "          ALL 3 EXPERIMENTS COMPLETE! COMPUTING FINAL METRICS"
echo "========================================================================"

python3 evaluate_ablation_metrics.py \
  stage4_constrained_inference/stage4_results.csv \
  stage4_constrained_inference/ablation_new_kg_only_cot.csv \
  stage4_constrained_inference/ablation_patient_memory_direct.csv \
  stage4_constrained_inference/ablation_patient_memory_cot.csv

echo "Done!"
