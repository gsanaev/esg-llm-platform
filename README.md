# ESG KPI Extraction & Reconciliation Pipeline

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2E8B57)

> **Kurzbeschreibung (DE)**
>
> Reproduzierbare Python-Pipeline zur Extraktion, Normalisierung und zum evidenzbasierten Abgleich von Nachhaltigkeitskennzahlen aus PDF-Berichten. Ein kontrollierter synthetischer Benchmark mit separater Ground Truth ermöglicht die Bewertung deterministischer, NLP-basierter und optional LLM-gestützter Verfahren sowie den expliziten Umgang mit fehlenden oder widersprüchlichen Angaben.

**Project summary (EN)**

A reproducible Python pipeline for extracting sustainability KPIs from PDF disclosures, preserving their source evidence, normalizing heterogeneous values and units, reconciling multiple observations, and evaluating extraction quality against hidden ground truth in a controlled benchmark.

The central data-quality problem is that a plausible extracted number is not automatically a reliable observation. Values may disagree, refer to different years or locations, originate from different extraction methods, or be absent altogether. The pipeline therefore separates **extraction**, **normalization**, **evidence preservation**, and **reconciliation** before assigning a final result status.

The implementation is a compact methodological prototype based on controlled synthetic disclosures. It is designed for transparent and reproducible evaluation rather than production-scale ESG reporting.

## Why this project

Sustainability disclosures are difficult to process consistently because the same KPI can appear:

- in narrative text or tables;
- with different number formats and units;
- with reporting-year or facility-specific context;
- more than once in the same document;
- with conflicting values;
- or not at all.

The project follows five principles:

1. **Preserve evidence before selecting final values.**
2. **Use deterministic extraction methods before optional LLM assistance.**
3. **Normalize values and units through an explicit KPI schema.**
4. **Reconcile observations before marking a result as accepted.**
5. **Evaluate predictions against controlled ground truth rather than treating heuristic confidence as correctness.**

## How it works

```text
PDF
 │
 ├─ table-grid extraction
 ├─ table-plain extraction
 ├─ regex extraction
 ├─ NLP extraction
 └─ optional LLM backfill
          │
          ▼
     normalization
          │
          ├──────────────► compact extraction/fusion API
          │                    run_on_pdf()
          │
          ▼
   EvidenceCandidate[]
          │
          ▼
      reconciliation
          │
          ▼
  ReconciledKPIResult
          │
   ┌──────┼───────────────┐
   ▼      ▼               ▼
accepted  review_required  not_reported
```

The public CLI uses the reconciled workflow. The compact extraction/fusion API remains available in Python for simpler extraction use cases.

## Supported KPIs

The universal schema is stored in:

`src/esg/schemas/universal_kpis.json`

| KPI code | Type | Canonical unit |
| --- | --- | --- |
| `total_ghg_emissions` | quantitative | `tCO2e` |
| `energy_consumption` | quantitative | `MWh` |
| `water_withdrawal` | quantitative | `m3` |
| `water_consumption` | quantitative | `m3` |
| `water_stress_share` | quantitative | `fraction` |
| `water_dependency` | qualitative | none |

Facility or geographic location is contextual evidence metadata rather than a separate KPI.

## Evidence and reconciliation

Each extracted observation can be represented as an `EvidenceCandidate` containing fields such as:

```text
metric
value_raw
value_normalized
unit_raw
unit_normalized
year
location
source_document
page
source_context
extraction_method
extraction_score
```

This allows multiple observations to remain traceable instead of discarding provenance after the first match.

The reconciliation layer then evaluates the evidence for each KPI.

Current rules include:

- agreeing deterministic evidence can be accepted;
- different known years or locations can require review without automatically being treated as conflicts;
- incompatible normalized units can trigger review/conflict handling;
- disagreement between values in the same known context can trigger a conflict;
- LLM-only evidence requires review rather than automatic acceptance;
- absence of usable evidence produces `not_reported`.

Final `ReconciledKPIResult` objects expose:

```text
metric
value
unit
year
location
status
conflict_flag
review_required
supporting_evidence
```

## Benchmark and evaluation

### Controlled benchmark

The project includes a reproducible synthetic benchmark in which predictions are evaluated against hidden ground truth.

- Ground truth: `data/benchmark/truth/benchmark_truth.yaml`
- Case definitions: `data/benchmark/cases/benchmark_cases.yaml`

The six current cases are:

- `alpha_structured_table`
- `alpha_clean_narrative`
- `beta_locale_table`
- `beta_mixed_units`
- `alpha_missing_water_consumption`
- `alpha_conflicting_water_withdrawal`

Generated benchmark PDFs are written to `data/benchmark/generated/`, which is ignored by Git because the documents are reproducible derived artifacts.

Ground truth is used to generate the controlled disclosures and to evaluate predictions afterward. It is **not passed to the extraction runner**.

### Evaluation metrics

Independent benchmark methods are:

- `table_grid`
- `table_plain`
- `regex`
- `nlp`
- optional `llm`

Method-level metrics include:

- KPI detection precision;
- KPI detection recall;
- numeric value accuracy;
- unit normalization accuracy;
- reporting-year accuracy;
- location accuracy;
- missing-value accuracy;
- extraction coverage.

`extraction_coverage` currently uses the same detected-versus-expected ratio as detection recall. It is retained as an operational coverage label rather than as a separate statistical measure.

The reconciled workflow is evaluated separately for:

- conflict-detection accuracy;
- review-flag accuracy.

Where a benchmark dimension has no applicable comparison, the evaluator currently returns `0.0`; such values should therefore be interpreted in context.

### Benchmark snapshot

A deterministic benchmark run with `RUN_LLM = False` produces the following representative results:

| Controlled scenario | Observed behavior |
|---|---|
| Structured table | `table_grid` reaches `1.00` detection recall, numeric accuracy, and unit accuracy |
| Locale-formatted table | `table_grid` reaches `1.00` detection recall, numeric accuracy, and unit accuracy |
| Clean narrative | `regex` and `nlp` each recover 5 of 6 KPIs (`0.833` recall), with `1.00` numeric and unit accuracy for detected values |
| Mixed units | `table_grid` retains `1.00` detection recall, while numeric and unit accuracy fall to `0.80` |
| Deliberately missing water consumption | all deterministic methods leave the KPI absent; reconciliation returns `not_reported` without conflict or review |
| Deliberately conflicting water withdrawal | reconciliation returns `review_required` with `conflict_flag = true` and `review_required = true` |

The benchmark intentionally exposes method- and case-specific limitations rather than forcing a single aggregate accuracy score. `table_plain`, for example, produces no detections on the six generated benchmark PDFs, although it remains exercised separately on the mixed-layout integration fixture.

Detailed method-by-case results are reproducible in `notebooks/esg_benchmark.ipynb`. Live LLM benchmarking is opt-in and is excluded from the deterministic results above.

## Quick start

Python 3.12+ and `uv` are required.

Install the locked environment:

```bash
uv sync --locked
```

Run the reconciled pipeline:

```bash
uv run esg-extract data/samples/esg_simple_text.pdf
```

Specify an output file:

```bash
uv run esg-extract \
  data/samples/esg_simple_text.pdf \
  --output output.json
```

The CLI writes JSON containing the source PDF path and reconciled KPI results, including status, conflict/review flags, and supporting evidence.

## Python API

### Reconciled workflow

```python
from esg.pipeline.pipeline import ESGPipeline

pipeline = ESGPipeline()
results = pipeline.run_on_pdf_reconciled("report.pdf")
```

This returns evidence-based `ReconciledKPIResult` objects.

### Compact extraction/fusion API

```python
from esg.pipeline.pipeline import ESGPipeline

pipeline = ESGPipeline()
results = pipeline.run_on_pdf("report.pdf")
```

This returns compact `KPIResult` objects.

## Benchmark notebook

The complete case-level benchmark and reconciliation demonstration is available in `notebooks/esg_benchmark.ipynb`. It regenerates the controlled disclosures, evaluates extraction methods independently against hidden ground truth, and demonstrates the missing-value and conflict cases.

Execute it headlessly with:

```bash
uv run jupyter nbconvert \
  --to notebook \
  --execute notebooks/esg_benchmark.ipynb \
  --output esg_benchmark-executed.ipynb \
  --output-dir /tmp \
  --ExecutePreprocessor.timeout=120
```

The committed source notebook is output-free; benchmark results are generated during execution.

## Optional LLM assistance

The LLM extractor is schema-guided and currently uses `gpt-4o-mini`.

The operational workflow first runs deterministic extraction methods. If KPIs remain unresolved, LLM backfill is attempted only for those unresolved metrics.

Behavior depends on `OPENAI_API_KEY`:

- without the variable, LLM extraction returns no predictions and processing continues without a network call;
- with the variable, LLM backfill may make a live OpenAI API request.

Credentials are read from the environment and are not stored in the repository. A safe template is provided in `.env.example`; the local `.env` file is ignored by Git.

For optional live LLM extraction, create a local environment file and add the key there:

```bash
cp .env.example .env
```

The benchmark notebook defaults to:

```python
RUN_LLM = False
```

Independent LLM benchmarking therefore has to be enabled deliberately. Automated tests mock LLM execution where needed and do not depend on live API responses.

## Project structure

```text
esg-llm-platform/
├── data/
│   ├── benchmark/
│   │   ├── cases/
│   │   ├── generated/        # ignored, reproducible PDFs
│   │   └── truth/
│   └── samples/
│       ├── esg_nlp_test.pdf
│       ├── esg_simple_mixed.pdf
│       ├── esg_simple_table.pdf
│       ├── esg_simple_text.pdf
│       └── make_samples.py
├── docs/
│   └── DESIGN.md
├── notebooks/
│   └── esg_benchmark.ipynb
├── src/esg/
│   ├── benchmark/
│   ├── cli/
│   ├── core/
│   ├── extractors/
│   ├── normalization/
│   ├── pipeline/
│   ├── schemas/
│   └── utils/
├── tests/
├── .env.example
├── LICENSE
├── README.md
├── pyproject.toml
├── pytest.ini
└── uv.lock
```

## Tests

Run the complete suite with:

```bash
uv run pytest -q
```

The test suite covers:

- KPI schema contracts;
- result and evidence models;
- regex, NLP, grid-table, and plain-table extraction;
- unit and share normalization;
- optional LLM behavior;
- evidence preservation;
- reconciliation rules;
- integrated pipeline behavior;
- controlled benchmark generation;
- method-level benchmark evaluation;
- missing-value and conflict cases;
- workflow-level evaluation;
- command-line JSON output.

Tests are separated by subsystem so failures can be traced to the corresponding architectural layer.

## Current limitations

- benchmark documents are controlled synthetic disclosures rather than production company reports;
- extraction coverage remains method-dependent;
- reporting-year and location extraction are not uniform across methods;
- deterministic qualitative-KPI extraction remains limited;
- some alternative-unit conversion paths are incomplete;
- live LLM behavior can vary when explicitly enabled;
- OCR/image-based extraction is outside the core benchmark;
- the project is not intended to be a production ESG reporting platform.

These limitations are stated explicitly because the project is intended to demonstrate extraction methodology, provenance, reconciliation, and reproducible evaluation rather than hide unresolved cases.

## Development history

An earlier extraction prototype is preserved under the `v1.0.0` Git tag. The current repository contains the consolidated extraction, evidence, reconciliation, and benchmark architecture.

## Technical design

See `docs/DESIGN.md` for the detailed architecture, evidence model, reconciliation rules, benchmark design, LLM modes, and evaluation methodology.

## License

MIT License.

## Author

**Golib Sanaev**<br>
Data Analyst & Applied Data Scientist<br>
Econometrics · Statistical Modelling · Sustainability Data · Reproducible Workflows

- GitHub: https://github.com/gsanaev
- LinkedIn: https://linkedin.com/in/golib-sanaev
- Email: gsanaev80@gmail.com
