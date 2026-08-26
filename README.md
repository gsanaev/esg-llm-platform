# ESG Extraction Pipeline V2

A reproducible Python pipeline for extracting, normalizing, reconciling, and evaluating sustainability KPIs from synthetic ESG disclosures.

Version 2 extends the original extraction prototype with hidden ground truth, controlled benchmark generation, evidence preservation, reconciliation, nature-related water indicators, and method-level evaluation.

## Design principles

1. **Evidence before final values** — extracted observations are preserved for review.
2. **Deterministic methods first** — table, regex, and NLP methods run before optional LLM backfill.
3. **Reconciliation before acceptance** — agreement, contextual differences, and conflicts are represented explicitly.
4. **LLM output is evaluated, not trusted automatically** — LLM-only evidence requires review.
5. **Benchmark claims come from ground truth** — heuristic confidence scores are not treated as correctness measures.

## KPI schema

The universal schema is stored in `src/esg/schemas/universal_kpis.json`.

| KPI code | Type | Canonical unit |
| --- | --- | --- |
| `total_ghg_emissions` | quantitative | `tCO2e` |
| `energy_consumption` | quantitative | `MWh` |
| `water_withdrawal` | quantitative | `m3` |
| `water_consumption` | quantitative | `m3` |
| `water_stress_share` | quantitative | `fraction` |
| `water_dependency` | qualitative | none |

Facility/geographic location is contextual evidence metadata rather than a separate KPI.

## Extraction architecture

```text
PDF
 ├─ table-grid
 ├─ table-plain
 ├─ regex
 └─ NLP
      ↓
 normalization
      ↓
 deterministic fusion
      ↓
 optional LLM backfill for unresolved KPIs
      ↓
 evidence candidates
      ↓
 reconciliation
      ↓
 accepted / review_required / not_reported
```

Independent benchmark methods are `table_grid`, `table_plain`, `regex`, `nlp`, and optionally `llm`.

## Evidence and provenance

V2 preserves fields such as:

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

This keeps observations traceable to their source and extraction method wherever technically possible.

## Reconciliation

The reconciliation layer distinguishes genuine disagreement from valid contextual differences.

- agreeing deterministic evidence can be accepted;
- different known years or locations can require review without being treated as conflicts;
- incompatible units or same-context value disagreement can trigger a conflict;
- LLM-only evidence requires review;
- absence of evidence produces `not_reported`.

Final results expose `status`, `conflict_flag`, `review_required`, and supporting evidence.

## Controlled benchmark

Hidden truth is stored in:

- `data/benchmark/truth/benchmark_truth.yaml`

Controlled disclosure cases are stored in:

- `data/benchmark/cases/benchmark_cases.yaml`

The six current cases are:

- `alpha_structured_table`
- `alpha_clean_narrative`
- `beta_locale_table`
- `beta_mixed_units`
- `alpha_missing_water_consumption`
- `alpha_conflicting_water_withdrawal`

Generated PDFs are written to `data/benchmark/generated/`. That directory is intentionally ignored by Git because the PDFs are reproducible derived artifacts.

Hidden truth is used to generate controlled disclosures and to evaluate predictions. It is not passed to the extraction runner.

## Evaluation

The benchmark calculates:

- KPI detection precision and recall
- numeric value accuracy
- unit normalization accuracy
- reporting-year accuracy
- location extraction accuracy
- missing-value accuracy
- extraction coverage
- conflict-detection accuracy
- review-flag accuracy

All reported benchmark metrics are calculated from actual outputs.

The current evaluator returns `0.0` when a metric has no applicable comparisons, so a zero does not always imply observed failure.

## V2 benchmark notebook

The primary V2 demonstration is:

`notebooks/03-v2-benchmark.ipynb`

It loads benchmark configuration, regenerates the six PDFs, runs independent extraction methods, evaluates their predictions, demonstrates missing-value behavior, and evaluates the reconciled conflict/review cases.

Run it headlessly with:

```bash
uv run jupyter nbconvert \
  --to notebook \
  --execute notebooks/03-v2-benchmark.ipynb \
  --output 03-v2-benchmark-executed.ipynb \
  --output-dir /tmp \
  --ExecutePreprocessor.timeout=120
```

The committed source notebook contains no execution outputs.

## LLM behavior

LLM extraction is schema-guided and currently uses `gpt-4o-mini`.

Operationally, the pipeline first runs deterministic/table/NLP methods. If KPIs remain unresolved, it attempts LLM backfill only for those metrics.

The LLM extractor checks `OPENAI_API_KEY`:

- without the variable, it returns no LLM predictions and the pipeline continues without a network call;
- with the variable, LLM backfill may make a live OpenAI API request.

The V2 benchmark notebook defaults to:

```python
RUN_LLM = False
```

Independent LLM benchmarking must therefore be enabled deliberately. The reconciled workflow demonstration also suppresses LLM backfill so the missing-value and conflict cases remain reproducible.

## Observed benchmark behavior

The controlled benchmark intentionally exposes limitations rather than forcing perfect scores.

Current runs show that:

- table-grid extraction performs strongly on generated structured tables and can preserve reporting year and location;
- regex performs strongly on several quantitative values and units but does not currently capture year/location in the same way;
- NLP contributes mainly on the controlled narrative case;
- table-plain contributes little on the current generated PDFs;
- qualitative KPI coverage is more limited for deterministic text methods;
- some alternative-unit normalization paths remain incomplete;
- deterministic methods correctly leave the controlled omitted water-consumption metric missing;
- the hybrid reconciled workflow correctly flags the controlled same-context water-withdrawal disagreement for review.

These are observed benchmark results, not predetermined claims.

## Installation

Python 3.12+ is required.

```bash
uv sync
```

The development dependency group includes `ipykernel` so the benchmark notebook can execute in the project environment.

## Command-line usage

Run the operational extraction façade:

```bash
uv run esg-extract data/samples/esg_simple_text.pdf
```

Specify an output file:

```bash
uv run esg-extract \
  data/samples/esg_simple_text.pdf \
  --output output.json
```

The CLI currently writes fused KPI extraction results to JSON.

The reconciled workflow is available through Python:

```python
from esg.pipeline.pipeline import ESGPipelineV2

pipeline = ESGPipelineV2()
results = pipeline.run_on_pdf_reconciled("report.pdf")
```

## Tests

Run:

```bash
uv run pytest -q
```

The test suite covers schema validation, extractors, normalization, evidence preservation, reconciliation, nature-related KPIs, benchmark generation, method-level evaluation, missing-value handling, conflict detection, review flags, and workflow orchestration.

Benchmark tests mock LLM execution where needed so automated tests do not depend on live API responses.

## Project structure

```text
esg-llm-platform/
├── data/
│   ├── benchmark/
│   │   ├── cases/
│   │   ├── generated/        # ignored derived PDFs
│   │   └── truth/
│   └── samples/
├── docs/
│   └── V2_SPEC.md
├── notebooks/
│   ├── 01-notebook-test-pipeline.ipynb
│   ├── 02-notebook-analysis.ipynb
│   └── 03-v2-benchmark.ipynb
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
├── README.md
├── pyproject.toml
└── uv.lock
```

The first two notebooks are retained as earlier exploratory material. `03-v2-benchmark.ipynb` is the primary V2 benchmark notebook.

## Current limitations

- controlled synthetic disclosures rather than production company reports;
- method-dependent extraction coverage;
- non-uniform year/location extraction;
- limited qualitative KPI coverage;
- incomplete alternative-unit conversion paths;
- variable behavior when live LLM execution is enabled;
- OCR/image-based extraction is not part of the core V2 benchmark.

The project is intentionally a compact methodological prototype, not a production ESG reporting platform.

## Design specification

See `docs/V2_SPEC.md` for the V2 scope, evidence model, reconciliation rules, benchmark design, LLM modes, and acceptance criteria.

## License

MIT License.

## Author

**Golib Sanaev**

Data Science · Applied Econometrics · Sustainability Data

- GitHub: https://github.com/gsanaev
- LinkedIn: https://linkedin.com/in/golib-sanaev
