# Stage 3: Graph Evaluation & Generic Term Weight Discounting

## 🎯 Objective
Evaluate the newly constructed Knowledge Graph, analyze its entity degree distribution, catalog non-discriminative generic medical terms, and apply **Soft Weight Discounting** to suppress noise without deleting nodes.

---

## 🧭 Role in the Big Picture

### Why Soft Weighting Instead of Hard Pruning?
* **The Risk of Hard Pruning (Deleting Nodes):**
  If we delete nodes like `Fever` or `Abdominal Pain` from the graph entirely, we risk **graph fragmentation**—breaking paths that connect a patient's secondary findings to the primary disease node.
* **The Power of Soft Weight Discounting:**
  We keep every node intact in the graph, but we modify how the retrieval pipeline **ranks and selects** evidence to present to Qwen2.5-3B.
  * When a high-specificity pathognomonic term (*Eschar*, *Tourniquet test*, *Hydatid daughter cyst*, *Doxycycline cure*) appears, it gets **full weight (1.0)**.
  * When a generic constitutional symptom (*Fever*, *Fatigue*, *Headache*, *Vomiting*) appears, its weight is **discounted by a degree penalty factor**.

This guarantees that the limited context window of Qwen2.5-3B is filled with **high-discrimination diagnostic facts**, rather than 30 variations of *"fever is common in infection"*.

---

## 🔬 Mathematical Formulation

### 1. Degree Distribution & Hub Detection
Let $\text{Degree}(v)$ be the total number of relational edges incident to entity $v$ in the graph. Entities with $\text{Degree}(v) > 20$ that represent non-specific constitutional symptoms are flagged as **Generic Symptom Hubs**.

### 2. The Specificity Discount Factor
For every entity $v$, we calculate a clinical specificity discount $W(v)$:

$$W(v) = \begin{cases} 
  \alpha \times \frac{1}{\log_2(1 + \text{Degree}(v))} & \text{if } v \in \text{Generic Hub Catalog} \\
  1.0 & \text{if } v \text{ is a Pathognomonic / High-Specificity Clinical Finding}
\end{cases}$$

Where $\alpha \approx 0.15 \text{ to } 0.25$ is a dampening constant.

### 3. Modulated Triple Ranking for Prompt Injection
When LightRAG retrieves a candidate pool of relational triples $(u \xrightarrow{r} v)$, we rank them according to their composite clinical utility score:

$$\text{Priority}(u \xrightarrow{r} v) = \text{Similarity}(u, v \mid \text{Query}) \times W(u) \times W(v) \times \mathbb{I}_{\text{DiseaseAnchor}}(u, v)$$

* $\mathbb{I}_{\text{DiseaseAnchor}}(u, v) = 2.0$ if either $u$ or $v$ is one of the 22 canonical disease nodes.
* Triples containing pathognomonic clinical features rise to the top.
* Generic triples (`Patient has fever`) sink to the bottom.

---

## 📋 The Generic Terms Catalog

The terms evaluated and subjected to weight discounting include:

1. **Constitutional Symptoms:**
   - `Fever`, `High-grade fever`, `Chills`, `Rigors`, `Sweating`, `Fatigue`, `Malaise`, `Weakness`, `Loss of appetite`, `Weight loss`, `Body aches`, `Myalgia`.
2. **Generic Gastrointestinal & Respiratory Complaints:**
   - `Nausea`, `Vomiting`, `Abdominal pain`, `Diarrhea`, `Cough`, `Dyspnea`, `Chest pain`, `Headache`.
3. **Administrative & General Medical Terms:**
   - `Patient`, `Male`, `Female`, `Hospital`, `Admission`, `Discharge`, `History`, `Examination`, `Treatment`, `Therapy`, `Normal`, `Medication`, `Antibiotics`.

---

## 🛠️ Step-by-Step Execution Plan for Stage 3

1. **Analyze Graph Statistics:** Run `analyze_and_weight_graph.py` on `graph_chunk_entity_relation.graphml` to calculate node degrees, edge counts, and identify the top 50 highest-degree nodes.
2. **Build the Generic Terms Config:** Generate `generic_terms_config.json` containing the identified generic hubs and their assigned discount weights.
3. **Integrate Weighting Function:** Connect the weighting multiplier directly into the triple-formatting function used in the benchmark pipeline.
4. **Compare Context Quality:** Inspect the top 30 formatted triples before and after weighting to confirm that pathognomonic evidence successfully displaces generic symptom noise.
