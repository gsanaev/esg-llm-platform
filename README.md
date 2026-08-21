# 🌿 ESG Extraction Pipeline – Structured, Transparent & Reproducible  
> **Version 1.0 — November 2025**

## 📋 Overview
This project develops a **reproducible ESG (Environmental, Social & Governance) data extraction pipeline** capable of extracting structured KPIs from *unstructured and semi-structured ESG reports*.  
Modern PDF extraction, NLP, and deterministic methods are combined in a layered architecture to reduce ambiguity in ESG disclosures.

While ESG reporting is crucial for achieving global sustainability objectives, the **lack of formatting standards, inconsistent units, and diverse narrative styles** makes automated extraction challenging.  
This project demonstrates a compact, fully transparent extraction framework using **synthetic sample reports**.

---

## 🎯 Objectives
- Provide a **deterministic, testable extraction pipeline** for ESG KPIs.  
- Demonstrate hybrid extraction combining:  
  - Regex-based extraction  
  - Table recognizers (grid & plain)  
  - NLP window-based extraction  
  - Optional LLM fallback  
- Ensure all steps are **auditable, interpretable, and validated** via tests and notebooks.  
- Use **only synthetic PDF samples** for full reproducibility (no real PDFs required).

---

## 🏗️ ESG KPI Framework

### Universal KPI Schema
Located in: `src/esg/schemas/universal_kpis.json`

This version tracks three core metrics:
- **Total GHG Emissions** (`tCO2e`)
- **Energy Consumption** (`MWh`)
- **Water Withdrawal** (`m³`)

The schema includes aliases, keyword triggers, and unit variations.

---

## 🔍 Extraction Architecture

| Layer | Component | Purpose |
|-------|-----------|----------|
| **1. Text Layer** | PDF reading (pdfplumber, PyMuPDF) | Robust text extraction |
| **2. Deterministic Extractors** | Regex, table-grid (Camelot), table-plain | High precision on structured data |
| **3. NLP Extractor** | Keyword windows, numeric parsing | Handles messy paragraphs |
| **4. Normalization** | Value parsing, unit resolution, scoring | Produces standardized KPI results |
| **5. Pipeline** | Orchestration & scoring | Generates final per-KPI outputs |
| **6. LLM Fallback (optional)** | gpt-4o-mini | For missing KPIs (disabled by default) |

---

## 🧪 Test Suite

All extractors are validated using synthetic PDFs.  
Run:

```bash
pytest -q
```

Current status: **✔ All tests passing**.

---

## 🧩 Project Structure

```
esg-llm-platform/
├── data/
│   ├── samples/              # synthetic PDF sample reports
│   └── out/                  # extracted CSV results (sample PDFs only)
│
├── docs/
│   ├── 01-notebook-test-pipeline.html
│   └── 02-notebook-analysis.html
│
├── notebooks/
│   ├── 01-notebook-test-pipeline.ipynb
│   └── 02-notebook-analysis.ipynb
│
├── src/esg/
│   ├── extractors/           # regex, nlp, tables, llm
│   ├── normalization/        # unit/value normalization
│   ├── utils/                # numeric parsing, pdf reader
│   ├── pipeline/             # main pipeline logic
│   ├── schemas/              # KPI definitions
│   └── cli/                  # command-line prototype
│
├── tests/                    # deterministic test suite
├── README.md
└── pyproject.toml
```

---

## 📊 Sample Report Evaluation

Using synthetic PDFs in `data/samples/`:

- 11 reports tested  
- Each contains controlled variations (messy units, OCR noise, corrupted tables, long narrative)  
- All KPIs successfully extracted in most reports  
- Confidence and source attribution provide transparency per extractor

A compact analysis appears in:

- `docs/02-notebook-analysis.html`

---

## 📈 Key Results (Synthetic Reports)

| KPI | Avg. Confidence | Best Extractor |
|------|----------------|----------------|
| Total GHG Emissions | ~0.75 | Regex / Table |
| Energy Consumption | ~0.70 | Regex |
| Water Withdrawal | ~0.70 | Table / Regex |

Missing values: **0%** on deterministic synthetic set.

---

## ⚙️ Tools & Libraries

- **PDF:** pdfplumber, PyMuPDF, Camelot, Ghostscript  
- **NLP:** keyword windows, regex, custom numeric parser  
- **Data:** pandas, numpy  
- **Visualization:** matplotlib (notebooks)  
- **LLM Fallback:** OpenAI API (disabled by default for reproducibility)  
- **Environment:** Python 3.12, `uv sync`, Jupyter notebooks  

---

## 🚀 Usage

### Setup
```bash
uv sync
```

### Run pipeline
```bash
uv run esg-extract data/samples/esg_simple_text.pdf
```

### Run test suite
```bash
uv run pytest -q
```

### Recreate synthetic PDFs (optional)
```bash
uv run python data/samples/make_samples.py
```
> LLM generation is disabled by default for reproducibility.

---

## 📚 Notebooks

| Notebook | Purpose |
|-----------|----------|
| `01-notebook-test-pipeline.ipynb` | Runs pipeline on all synthetic PDFs |
| `02-notebook-analysis.ipynb` | Aggregates CSV outputs → confidence, completeness, source contribution |

HTML exports included in `docs/`.

---

## 📜 License
MIT License — free for use and modification with attribution.

---

## 👤 Author  
Developed by **Golib Sanaev**  
*Data Scientist | Applied AI & ESG Analytics*  

📧 gsanaev80@gmail.com  
🔗 LinkedIn: https://linkedin.com/in/golib-sanaev  
💻 GitHub: https://github.com/gsanaev

---

## 🙏 Acknowledgements

- [StackFuel](https://stackfuel.com/) — applied data science education  
- OpenAI GPT-5 Assistant — documentation, debugging, test design  


⭐ *If you find this project useful, please give it a star!*
