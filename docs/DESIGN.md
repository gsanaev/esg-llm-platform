# ESG KPI Extraction & Reconciliation Pipeline — Technical Design

## 1. Purpose

This project implements a reproducible pipeline for extracting, normalizing,
preserving, reconciling, and evaluating sustainability indicators from
semi-structured and unstructured PDF disclosures.

The project is designed around a central methodological problem: extracting a
number from a document is not sufficient if the observation cannot be traced,
compared with alternative evidence, or assessed for ambiguity and conflict.

The main questions addressed are:

1. How accurately can deterministic, NLP-based, and optional LLM-assisted
   methods recover sustainability indicators from heterogeneous disclosures?
2. How should multiple observations for the same indicator be preserved and
   reconciled?
3. When can an extracted observation be accepted automatically?
4. When should an observation require human review?
5. How should missing information and conflicting evidence be represented?
6. Under which conditions can an LLM add value to a statistical extraction
   workflow?

The project is synthetic-first. Controlled PDF disclosures and hidden ground
truth make the benchmark reproducible while keeping extraction and evaluation
logically separate.

It is not intended to provide company ESG ratings, financial-risk estimates,
or a production ESG reporting platform.

---

## 2. Scope

The project focuses on a compact set of environmental and nature-related
sustainability indicators.

The authoritative KPI schema is stored in:

`src/esg/schemas/universal_kpis.json`

The six implemented KPIs are:

| Metric | Type | Canonical unit |
|---|---|---|
| Total GHG Emissions | quantitative | `tCO2e` |
| Energy Consumption | quantitative | `MWh` |
| Water Withdrawal | quantitative | `m3` |
| Water Consumption | quantitative | `m3` |
| Water Stress Share | quantitative | `fraction` |
| Water Dependency | qualitative | none |

Facility or geographic location is treated as contextual information rather
than as a separate KPI.

Water-related indicators are used as the main nature-related extension because
they create realistic extraction and data-quality problems involving:

- closely related concepts;
- geographic context;
- missing disclosures;
- different units;
- percentage and fraction representations;
- conflicting values;
- and qualitative as well as quantitative evidence.

The project remains broader than a water-only application because it also
includes climate and energy indicators.

It does not attempt to represent the complete Environmental, Social and
Governance taxonomy.

---

## 3. Design Principles

### 3.1 Synthetic-first and reality-informed

Synthetic disclosures provide controlled ground truth and reproducible
evaluation.

The generated reports imitate selected problems found in real sustainability
disclosures without claiming to reproduce every feature of long production
reports.

### 3.2 Hidden ground truth

Company-level truth is defined before benchmark documents are generated.

The extraction pipeline does not access benchmark truth while producing
predictions.

Ground truth is used only for:

- generating controlled disclosures; and
- evaluating predictions after extraction.

This separation prevents the benchmark runner from using the answers it is
supposed to predict.

### 3.3 Evidence before final values

Extraction methods preserve candidate observations rather than immediately
collapsing every KPI to one final value.

Evidence records retain information needed for validation and audit, including:

- metric;
- company identifier;
- raw value;
- normalized value;
- raw unit;
- normalized unit;
- reporting year;
- location;
- source document;
- page;
- source context;
- extraction method;
- extraction score.

The `extraction_score` field is a heuristic extraction signal. It is not
presented as a statistically calibrated probability of correctness.

### 3.4 Reconciliation before acceptance

Multiple candidate observations are compared before the evidence-based
workflow produces a final KPI result.

Agreement, disagreement, contextual differences, ambiguity, missingness, and
source conflicts are represented explicitly rather than hidden behind a
single selected value.

### 3.5 LLMs are optional and evaluated

The LLM component is optional.

LLM output follows the same structured evidence model as other extraction
methods and can be evaluated against hidden truth.

LLM-only evidence is not sufficient for automatic acceptance in the
reconciliation workflow.

### 3.6 Auditability and reproducibility

The project favors transparent extraction logic, explicit evidence,
deterministic benchmark generation, and automated testing over unnecessary
technical complexity.

---

## 4. Ground-Truth Model

Benchmark truth is stored separately from extraction configuration in:

`data/benchmark/truth/benchmark_truth.yaml`

The current benchmark contains two synthetic companies. Each record includes:

- `company_id`;
- `reporting_year`;
- `facility_location`;
- the six benchmark KPIs and their units.

The truth dataset is deliberately small. Its purpose is controlled evaluation,
not statistical representativeness.

The benchmark runner does not use this file during extraction.

---

## 5. Controlled Benchmark Cases

Benchmark case configuration is stored in:

`data/benchmark/cases/benchmark_cases.yaml`

The current benchmark implements six cases:

| Case | Purpose |
|---|---|
| `alpha_structured_table` | structured tabular disclosure |
| `alpha_clean_narrative` | clean narrative disclosure |
| `beta_locale_table` | locale-specific number formatting |
| `beta_mixed_units` | unit conversion, including `GWh` to canonical `MWh` |
| `alpha_missing_water_consumption` | deliberate missing KPI |
| `alpha_conflicting_water_withdrawal` | deliberate conflicting evidence |

The missing-water-consumption case expects:

- `conflict_flag = false`;
- `review_required = false`;
- `status = not_reported`.

The conflicting-water-withdrawal case expects:

- `conflict_flag = true`;
- `review_required = true`;
- `status = review_required`.

Benchmark PDFs are generated from the truth and case definitions. Generated
benchmark documents are reproducible and are not themselves the source of
ground truth during evaluation.

---

## 6. Evidence Model

The evidence-based workflow represents extractor output as
`EvidenceCandidate` objects.

Conceptually, each candidate contains:

- `company_id`;
- `metric`;
- `value_raw`;
- `value_normalized`;
- `unit_raw`;
- `unit_normalized`;
- `year`;
- `location`;
- `source_document`;
- `page`;
- `source_context`;
- `extraction_method`;
- `extraction_score`.

This structure keeps provenance and contextual information attached to the
observation throughout the workflow.

Evidence is preserved even when the final result requires review.

---

## 7. Final Result Model

Evidence-based final results are represented separately from raw candidate
evidence.

A reconciled result contains:

- metric;
- selected or reconciled value;
- normalized unit;
- reporting year;
- location;
- supporting evidence;
- conflict flag;
- review requirement;
- result status.

The implemented statuses are:

- `accepted`;
- `review_required`;
- `not_reported`.

`accepted` indicates that the available evidence is sufficiently consistent
for automatic acceptance under the implemented reconciliation rules.

`review_required` indicates that the pipeline found usable evidence but cannot
accept a final observation automatically.

`not_reported` indicates that no usable observation was found for the KPI.

A KPI with a successfully selected value does not retain a `not_reported`
status.

---

## 8. Extraction Architecture

The project uses a layered extraction architecture.

### 8.1 KPI schema

The KPI schema defines:

- display names;
- value types;
- canonical units;
- accepted units;
- synonyms;
- keyword triggers;
- selected context requirements.

The schema is the authoritative definition of the supported KPIs.

### 8.2 PDF input

PDF text and table content are read through the project utilities and supplied
to the relevant extraction methods.

### 8.3 Extraction methods

The current extraction methods include:

- grid-table extraction;
- plain-table extraction;
- regex/context extraction;
- NLP/context-window extraction;
- optional schema-guided LLM extraction.

Different methods are retained because sustainability disclosures can present
the same information in materially different structures.

### 8.4 Normalization

Extractor-specific outputs are normalized into comparable values and units.

Normalization includes, where applicable:

- numeric parsing;
- locale-aware number handling;
- unit normalization;
- unit conversion;
- percentage-to-fraction conversion;
- qualitative-value handling.

### 8.5 Evidence conversion

Normalized extractor outputs are converted to evidence candidates with
provenance and contextual information preserved.

### 8.6 Reconciliation

Candidate evidence is reconciled into final evidence-based KPI results.

The project therefore separates:

`extraction -> normalization -> evidence -> reconciliation`

rather than treating extraction itself as the final analytical decision.

---

## 9. Two Result Paths

The project exposes two related result paths.

### 9.1 Compact extraction/fusion path

The compact API runs the extraction and normalization layers and returns
`KPIResult` objects.

It is useful when a simpler per-KPI extraction result is sufficient.

### 9.2 Evidence-based reconciled path

The reconciled workflow preserves multiple candidates as evidence and applies
the reconciliation layer before returning `ReconciledKPIResult` objects.

This is the primary workflow exposed through the command-line interface because
it preserves the project's data-quality and review logic.

---

## 10. Reconciliation and Conflict Detection

Reconciliation compares usable evidence before assigning a final status.

### 10.1 Agreement

If multiple deterministic observations refer to the same context and agree
after normalization, the KPI can be accepted.

Conceptually:

Narrative: `2.4 million m3`

Table: `2.4 million m3`

Possible result:

- `status = accepted`;
- `conflict_flag = false`;
- `review_required = false`.

### 10.2 Same-context disagreement

If usable observations refer to the same known context but disagree materially,
the result is treated as a conflict.

Conceptually:

Narrative: `2.4 million m3`

Table: `2.6 million m3`

Possible result:

- `status = review_required`;
- `conflict_flag = true`;
- `review_required = true`.

### 10.3 Different known contexts

Different values associated with different known reporting years or locations
are not automatically treated as contradictory observations.

They require contextual handling rather than a false conflict assignment.

### 10.4 Mixed known and unknown context

If some observations contain year or location information while comparable
observations do not, automatic acceptance may be inappropriate.

Such ambiguity can trigger review even when the values themselves appear
compatible.

### 10.5 Unit disagreement

Evidence with unresolved or incompatible unit information can require review
rather than automatic acceptance.

### 10.6 LLM-only evidence

If all usable evidence for a KPI comes only from the LLM extractor, the
implemented workflow requires review rather than automatic acceptance.

### 10.7 Missing evidence

If no usable evidence is available, the result remains explicitly
`not_reported`.

Missing information is therefore preserved as missing rather than filled by an
unsupported estimate.

---

## 11. Provenance

Provenance is retained wherever technically available.

An evidence candidate can be traced through:

- source document;
- page;
- source context;
- extraction method;
- raw and normalized representations.

This makes extracted sustainability data inspectable and supports human review
when automatic reconciliation is insufficient.

---

## 12. LLM Modes

The optional LLM component serves two distinct purposes.

### 12.1 Operational assistance

The operational pipeline first runs deterministic, table, and NLP methods.

If metrics remain unresolved, LLM extraction can be attempted for those
unresolved metrics when an OpenAI API key is available.

The API key is supplied through the environment and is not part of the
repository.

Without an API key, the project continues without live LLM extraction.

### 12.2 Independent benchmark evaluation

The benchmark runner can evaluate extraction methods independently.

This allows deterministic, NLP, and optional LLM predictions to be compared
against the same hidden benchmark truth without allowing one method's result to
be fused into another method's score.

The separation makes it possible to investigate where an LLM adds useful
coverage and where it introduces errors or additional review requirements.

---

## 13. Evaluation

Heuristic extraction scores are not treated as measures of actual correctness.

Benchmark predictions are evaluated against hidden ground truth after
extraction.

Implemented method-level evaluation includes:

- KPI detection precision;
- KPI detection recall;
- numeric-value accuracy;
- unit accuracy;
- reporting-year accuracy;
- location accuracy;
- missing-value accuracy;
- extraction coverage.

Workflow-level evaluation additionally includes:

- conflict-detection accuracy;
- review-flag accuracy.

`extraction_coverage` is retained as an operational coverage label. In the
current benchmark implementation it uses the same underlying detected-truth
ratio as detection recall, so it should not be interpreted as an independent
statistical performance measure.

All benchmark results are calculated from actual extraction outputs rather
than predetermined performance claims.

---

## 14. Nature-Related Extension

Nature-related indicators remain deliberately focused.

Water withdrawal and water consumption allow the project to test whether
closely related sustainability concepts can be distinguished.

Water-stress share introduces percentage and fraction normalization as well as
context-sensitive extraction.

Water dependency introduces qualitative evidence that cannot be handled as a
standard numeric KPI.

Facility location provides geographic context for observations and allows the
reconciliation layer to distinguish valid contextual differences from genuine
same-context conflicts.

The project does not estimate:

- ecosystem condition;
- biodiversity loss;
- species impact;
- company-level financial risk;
- bank credit risk;
- expected financial losses;
- or systemic financial risk.

The structured indicators produced here can conceptually serve as upstream
inputs to later exposure or risk analysis, but such modelling is outside the
scope of this project.

---

## 15. Image-Based Extraction

Genuine image-based or OCR extraction is not implemented in the current
benchmark.

The project therefore does not claim support for:

- scanned-document OCR;
- image-to-text extraction;
- satellite imagery;
- computer-vision models;
- multimodal document understanding.

Image-based extraction could be integrated in the future by converting its
output to the same evidence model, but it is not part of the implemented
workflow documented here.

---

## 16. Explicitly Out of Scope

The project does not aim to provide:

- complete ESG taxonomy coverage;
- company ESG ratings or rankings;
- bank-risk modelling;
- financial-loss prediction;
- arbitrary long-document robustness;
- production-scale document processing;
- satellite-image analysis;
- a chatbot;
- a general retrieval-augmented generation architecture;
- a vector database;
- cloud deployment solely for demonstration purposes;
- or production-readiness claims.

The intended contribution is narrower: transparent sustainability-data
extraction, evidence preservation, reconciliation, and reproducible
methodological evaluation.
