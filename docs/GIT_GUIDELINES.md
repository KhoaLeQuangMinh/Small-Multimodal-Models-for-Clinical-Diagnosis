# Git & GitHub Guidelines for Medical AI Research Team

Welcome to the unified `Datasets` repository. To ensure our research is reproducible, collaborative, and collision-free, all contributors (students, researchers, and AI agents) must adhere to these guidelines.

---

## 1. Branch Naming Taxonomy

Every piece of work MUST happen on a dedicated branch created from the latest `main`. Never commit directly to `main`.

| Prefix | Use Case | Example | Merged to `main`? |
|---|---|---|---|
| `feature/` | New clinical features, pipelines, tools, or retrieval engines | `feature/retrieval-reranker` | Yes (via PR/review) |
| `bugfix/` | Fixing errors, script crashes, or missing imports | `bugfix/torch-import-error` | Yes |
| `experiment/` | Novel ML/RAG experiments, ablation tests, prompt trials | `experiment/gemini-flash-kg-eval` | Optional (if successful) |
| `data/` | Dataset extraction, cleaning, schema updates, labeling | `data/mesh-tropical-expansion` | Yes |
| `eval/` | Benchmark evaluation runs, error metrics, diagnostic scoring | `eval/365-masked-subgroup` | Yes |
| `docs/` | Monographs, paper drafts, guides, protocol documentation | `docs/stage4-cot-specification` | Yes |
| `refactor/` | Code cleanup, optimization, restructuring (no behavior change) | `refactor/vector-memory-loader` | Yes |
| `test/` | Local scratchpad experiments, throwaway sandbox tests | `test/ollama-kv-latency` | **NO** (never merged to `main`) |

---

## 2. Essential Git Command Reference

```bash
# Check current working tree state and staged/untracked files
git status

# Inspect exact line-by-line differences before staging
git diff

# Stage specific files cleanly (avoid blind 'git add .')
git add path/to/file.py

# Commit with a clear Conventional Commit message
git commit -m "feat(retrieval): implement reciprocal rank fusion for patient twins"

# Fetch upstream commits and branch references without modifying local files
git fetch origin

# Switch branches safely
git switch branch-name
git switch -c feature/new-idea   # Create and switch in one command

# Pull upstream changes for current branch
git pull origin branch-name

# View formatted git history graph
git log --graph --oneline --decorate -n 15
```

---

## 3. Standard Collaborative Workflows

### Workflow A: Starting a New Task or Experiment
```bash
# 1. Ensure your local main branch is completely up to date
git checkout main
git pull origin main

# 2. Create your dedicated branch using the appropriate prefix
git checkout -b feature/clinical-slot-filling

# 3. Develop, run local smoke tests, and commit in small logical increments
git add clinical_slot_extractor.py
git commit -m "feat(slot): add regex patterns for vital signs and symptoms"
```

### Workflow B: Resuming Work When `main` Has Advanced
When colleagues have merged new commits into `main` while you were working on your branch:
```bash
# 1. Fetch latest references from remote
git fetch origin

# 2. Rebase your feature branch on top of updated main (ensures clean, linear history)
git switch feature/clinical-slot-filling
git rebase origin/main

# 3. If merge conflicts occur:
# Inspect conflicting files, resolve the <<<< ==== >>>> markers, and then:
git add resolved_file.py
git rebase --continue

# 4. Push your branch safely
git push --force-with-lease origin feature/clinical-slot-filling
```

---

## 4. History Management & Safety Rules

### Revert vs. Reset (When to Use Which?)
- **`git revert <commit>`**: Creates a new commit that exactly reverses the changes of an older commit.
  - **Always use `revert` on shared or pushed branches**. It preserves linear history and will not corrupt your teammates' local repos.
- **`git reset --soft HEAD~1`**: Undoes the commit but leaves all file modifications staged in your index.
  - Useful when you committed too early and want to add another file or amend the commit message locally.
- **`git reset --mixed HEAD~1` (default)**: Undoes the commit and unstages changes, keeping modifications on disk.
- **`git reset --hard HEAD~1`**: **DESTRUCTIVE**. Completely erases uncommitted changes and reverts all files to the previous commit.
  - *Warning: Never run `reset --hard` unless you are 100% certain you want to discard your uncommitted work.*

### When to `--amend`
```bash
# If you committed locally and noticed a typo or forgot to stage one file:
git add forgotten_file.py
git commit --amend --no-edit   # Amends previous commit without altering message
```
*Rule: Only amend commits that have NOT yet been pushed to a shared remote.*

### When to Use `git push --force-with-lease`
When you rebase your branch against `origin/main`, Git will reject a standard `git push` because the commit history has changed.
- **Always use `git push --force-with-lease origin branch-name`**.
- *Why `--force-with-lease`?* Unlike `--force`, `--force-with-lease` verifies whether another teammate has pushed new commits to the remote branch in the meantime. If so, it refuses to overwrite them, preventing accidental loss of work.
- **GOLDEN RULE: NEVER run `git push --force` or `--force-with-lease` to `main` under any circumstances.**

---

## 5. Machine Learning & Medical Research Best Practices

Grounding our work in medical AI rigor and Google ML engineering standards:

### 1. Strict Featurization Ordering (Zero Data Leakage)
- **Always** partition patient cases into training, validation, and test cohorts **BEFORE** running embedding generation, feature scaling, vocabulary building, or vector indexing.
- Never fit vectorizers, normalizers, or knowledge graph extractors on the test set.
- Clinical vignette rewrites must be strictly blinded: admission triage text must never contain the final diagnosis, pathognomonic lab confirmations, or post-treatment outcomes.

### 2. Reproducibility & Fixed Random Seeds
- Any script performing subsampling, train/test splitting, clustering, or stochastic LLM inference must set explicit seeds:
  ```python
  import random
  import numpy as np
  import torch

  SEED = 42
  random.seed(SEED)
  np.random.seed(SEED)
  torch.manual_seed(SEED)
  if torch.cuda.is_available():
      torch.cuda.manual_seed_all(SEED)
  ```

### 3. Rigorous Multi-Metric Evaluation
Do not evaluate clinical models on raw accuracy alone:
- **Top-1 and Top-3 Differential Diagnostic Accuracy:** Clinical diagnosis is inherently differential. Report both whether the exact ground truth is ranked #1 and whether it appears in the top-3 candidate differentials.
- **Macro-F1 & Per-Disease Sensitivity/Specificity:** Neglected tropical disease datasets are often imbalanced. Monitor sensitivity and specificity across all 22 target diseases to detect neglected rare classes.
- **Statistical Significance via Bootstrapping:** Report bootstrap 95% confidence intervals on benchmark cohorts to confirm improvements are statistically significant rather than test-split artifacts.
- **Operational Trade-Offs:** Always measure inference latency per case (seconds) and token count alongside diagnostic accuracy.

### 4. Naive Baselines & Model Comparison
- Always benchmark new architectures against:
  1. A naive baseline (majority class or zero-shot unprompted SLM).
  2. Standard RAG (dense vector retrieval).
  3. Graph-only RAG (pure triple matching).
- Document performance deltas in `docs/RESULT.md`.

### 5. Data vs. Code Discipline
- **NEVER** commit raw medical images (`.jpg`, `.png`, `.webp`), bulk PMC parquets (>50MB), or vector database storage caches to Git.
- Large datasets belong in local storage or cloud buckets. Git must only track curated scripts, monographs, schema definitions, and explicitly whitelisted benchmark JSONLs (`data/test_masked_cases.jsonl`, `stage2_medcase_distillation/train_medcase_profiles.jsonl`).

---

## 6. Credential Security & Secret Leak Prevention

Preventing credential leaks is a non-negotiable security requirement. Public GitHub repositories and commit histories are continuously monitored by automated threat actors.

### 1. Mandatory Environment Variable Loading
- **NEVER hardcode API keys, access tokens, passwords, or credentials** in Python scripts, Jupyter notebooks (`.ipynb`), configuration files, or documentation.
- All API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HUGGINGFACE_TOKEN`, etc.) must strictly be loaded from environment variables or untracked local `.env` files:
  ```python
  import os
  from dotenv import load_dotenv

  load_dotenv()  # Loads variables from local untracked .env file
  api_key = os.getenv("GEMINI_API_KEY")
  if not api_key:
      raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it in your environment or .env file.")
  ```

### 2. Standardized `.env.example`
- Keep a clean, tracked `.env.example` file in the repository root demonstrating variable names without secret values:
  ```bash
  # .env.example - Copy to .env and fill in real values
  GEMINI_API_KEY=your_gemini_api_key_here
  OPENAI_API_KEY=your_openai_api_key_here
  ANTHROPIC_API_KEY=your_anthropic_api_key_here
  OLLAMA_URL=http://127.0.0.1:11434/api/generate
  ```

### 3. Automated Secret Scanning Before Commit
Always inspect files staged for commit or run a regex scan for common credential signatures:
```bash
# Scan working tree and staged index for known secret patterns (excluding guidelines):
git grep -I -E "AIza[0-9A-Za-z_-]{35}|sk-[a-zA-Z0-9_-]{20,}|gh[p]_[0-9A-Za-z]{20,}" -- ':!docs/GIT_GUIDELINES.md'
```
To automate this locally, install a pre-commit hook in `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Pre-commit hook to block hardcoded API keys
SECRET_PATTERN="AIza[0-9A-Za-z_-]{35}|sk-[a-zA-Z0-9_-]{20,}|gh[p]_[0-9A-Za-z]{20,}"
if git diff --cached --name-only | grep -v "docs/GIT_GUIDELINES.md" | xargs grep -E "$SECRET_PATTERN" 2>/dev/null; then
    echo "ERROR: Attempting to commit an API key or token! Commit rejected."
    exit 1
fi
```

### 4. Incident Response: What to Do if an API Key is Leaked
If an API key is ever committed (even locally or on a branch):
1. **Immediate Revocation (Priority 1):** Go directly to the cloud provider console (e.g. Google Cloud Console / Google AI Studio / OpenAI Platform) and immediately **delete or revoke the compromised key**. Never assume that deleting the commit or file removes the risk, as commit objects persist in Git packfiles.
2. **Rotate Credentials:** Generate a replacement key and update local `.env` files.
3. **Notify Team:** Inform the repository maintainers immediately so audit logs can be reviewed.
