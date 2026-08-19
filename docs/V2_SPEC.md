# ESG Extraction Pipeline — v2 Technical Specification

## 1. Purpose

Version 2 extends the existing ESG extraction pipeline from a primarily
extraction-oriented prototype into a controlled benchmark for sustainability
data extraction, validation, provenance, reconciliation, and methodological
evaluation.

The project remains synthetic-first and reproducible.

The main methodological questions are:

1. How accurately can deterministic, NLP-based, and LLM-assisted methods
   recover sustainability indicators from heterogeneous corporate disclosures?
2. How should ambiguous or conflicting evidence be handled?
3. When can an extracted observation be accepted automatically?
4. When should an observation be flagged for human review?
5. Under which conditions does an LLM add value to a statistical extraction
   workflow?

The project does not aim to provide production-ready ESG reporting,
company ratings, or financial-risk estimates.

---

## 2. Scope

Version 2 focuses on environmental and nature-related sustainability data.

The existing core indicators are retained:

- Total GHG emissions
- Energy consumption
- Water withdrawal

The nature-related extension introduces a small set of additional variables:

- Water consumption
- Share of activity or water use in water-stressed areas
- Facility or geographic location
- Qualitative water dependency

Water is used as the main nature-related case because it provides a realistic
setting for testing:

- closely related indicators,
- geographic context,
- missing information,
- different reporting definitions,
- conflicting values,
- unit conversion,
- actual values versus targets,
- and qualitative versus quantitative evidence.

The project remains broader than a water-risk application and continues to
cover climate, energy, and resource-use indicators.

The project does not attempt to represent the complete Environmental, Social
and Governance taxonomy.

---

## 3. Design Principles

Version 2 follows the following principles:

### 3.1 Synthetic-first and reality-informed

Synthetic disclosures are used to retain full reproducibility and controlled
ground truth.

Synthetic reports should imitate realistic disclosure problems without
claiming to reproduce every feature of real corporate sustainability reports.

### 3.2 Hidden ground truth

True company-level values are generated before the synthetic reports.

The extraction pipeline must not access the ground-truth data during
extraction.

Ground truth is used only for:

- generating controlled disclosures,
- evaluating extraction performance.

### 3.3 Evidence before final values

Extractors should return candidate evidence rather than immediately reducing
each KPI to one final number.

This allows the pipeline to preserve:

- source document,
- page,
- source context,
- extraction method,
- raw value,
- normalized value,
- units,
- year,
- location,
- and other relevant contextual information.

### 3.4 Reconciliation before acceptance

Multiple candidate observations must be reconciled before a final KPI result
is accepted.

Agreement, disagreement, missingness, ambiguity, and source conflicts should
be represented explicitly.

### 3.5 LLMs are evaluated, not automatically trusted

The LLM component remains optional.

LLM outputs must be structured and should be evaluated against known ground
truth and deterministic alternatives.

LLM output alone is not sufficient evidence for automatic acceptance.

### 3.6 Auditability and reproducibility

The project should favor transparent and reproducible analytical workflows over
unnecessary technical complexity.

---

## 4. Ground-Truth Schema

The benchmark ground truth should contain a compact company-level structure
similar to:

- company_id
- company_name
- reporting_year
- ghg_emissions_tco2e
- energy_consumption_mwh
- water_withdrawal_m3
- water_consumption_m3
- water_stress_share
- facility_location
- water_dependency

Example conceptually:

| company_id | company_name | reporting_year | water_withdrawal_m3 | water_consumption_m3 | water_stress_share |
|------------|--------------|----------------|----------------------|----------------------|--------------------|
| COMP_001 | Alpha Foods GmbH | 2025 | 2400000 | 1600000 | 0.38 |

Ground-truth data must remain logically separate from the extraction pipeline.

---

## 5. Synthetic Benchmark Cases

The benchmark should include a manageable number of deliberately heterogeneous
disclosures.

Planned cases include:

1. Clean narrative
2. Structured table
3. Locale-specific number formats
4. Mixed units
5. Multiple reporting years
6. Actual value versus target
7. Similar metrics such as water withdrawal versus water consumption
8. Conflicting narrative and table values
9. Missing KPI
10. Geographic or facility-level information
11. Long narrative context
12. OCR-like text noise

Existing v1 synthetic samples may be retained as regression or integration
fixtures where useful.

New benchmark cases should be generated from explicit hidden truth.

---

## 6. Evidence Model

Each extractor should produce an evidence candidate rather than only a final
KPI value.

The exact Python implementation may evolve during development, but the
conceptual structure should include:

- company_id
- metric
- value_raw
- value_normalized
- unit_raw
- unit_normalized
- year
- location
- source_document
- page
- source_context
- extraction_method
- extraction_score

The term `extraction_score` is preferred over `confidence` unless the score is
statistically calibrated.

---

## 7. Final Result Model

Final KPI results should be conceptually distinct from raw evidence.

A final result should be able to represent:

- selected or reconciled value,
- normalized unit,
- reporting year,
- location,
- supporting evidence,
- conflict status,
- review requirement,
- result status.

Planned statuses:

- accepted
- review_required
- not_reported

A successfully extracted result must never retain a `not_reported` status.

---

## 8. Extraction Architecture

The existing layered architecture should be preserved where practical.

### Deterministic extraction

- regex and contextual rules
- numeric parsing
- unit handling

### Table extraction

- structured table extraction
- plain table extraction

### NLP extraction

- keyword and context-window methods
- context-aware numeric extraction

### LLM extraction

- optional
- schema-guided
- structured output
- no automatic trust without validation

The KPI schema should become the authoritative source for metric definitions,
aliases, units, and relevant triggers.

Hard-coded duplicate KPI definitions should be reduced where practical.

---

## 9. Reconciliation and Conflict Detection

Candidate evidence should be compared before producing a final observation.

Examples:

### Agreement

Narrative: 2.4 million m³  
Table: 2.4 million m³  
LLM: 2.4 million m³

Possible result:

- accepted
- conflict_flag = false
- review_required = false

### Conflict

Narrative: 2.4 million m³  
Table: 2.6 million m³  
LLM: 2.4 million m³

Possible result:

- conflict_flag = true
- review_required = true

Different values for different reporting years must not automatically be
treated as conflicts.

The reconciliation layer should distinguish genuine disagreement from valid
contextual differences.

---

## 10. Provenance

Page-level and source-level provenance should be preserved wherever technically
possible.

An extracted observation should ideally be traceable to:

- source document,
- page,
- source text or table context,
- extraction method.

The purpose is to make extracted sustainability data reviewable and auditable.

---

## 11. LLM Modes

Version 2 should support two conceptual modes.

### 11.1 Operational mode

Deterministic, table, and NLP extraction are attempted first.

The LLM may be used for unresolved or contextually difficult cases.

### 11.2 Benchmark mode

Deterministic, NLP, and LLM methods may be run independently on controlled
benchmark cases.

Their results are then compared with hidden ground truth.

This allows the project to evaluate where LLMs add value and where they create
additional errors or review requirements.

---

## 12. Evaluation

Heuristic extractor scores should not be treated as measures of actual
correctness.

Benchmark evaluation should use ground truth.

Planned evaluation dimensions include:

- KPI detection precision and recall
- numeric value accuracy
- unit normalization accuracy
- reporting-year accuracy
- location extraction accuracy
- correct missing-value handling
- conflict-detection performance
- review-flag performance
- extraction coverage

Method-level comparison should be possible for:

- deterministic methods
- NLP
- LLM
- hybrid workflow

All reported benchmark results must be calculated from actual outputs.

No predetermined performance claims should be used.

---

## 13. Nature-Related Extension

The nature-related extension should remain focused and methodologically useful.

Water-related variables are selected because they create realistic extraction
and data-quality challenges while remaining connected to the broader
sustainability-data framework.

The project does not attempt to estimate:

- company-level financial risk,
- bank credit risk,
- expected financial losses,
- or systemic financial risk.

The structured indicators produced by the project may conceptually serve as
upstream inputs to later financial-exposure analysis, but such analysis is
outside the scope of v2.

---

## 14. Image-Based Extraction

Image-based extraction is not a core requirement for v2.0.0.

The current OCR-like synthetic sample represents text noise rather than genuine
image-to-text extraction and should be described accurately.

After the core v2 pipeline is complete, one optional experiment may be added:

synthetic table
→ rendered image
→ OCR or image-based extraction
→ common evidence schema
→ normal validation and reconciliation

No satellite imagery, computer-vision model, or large multimodal subsystem is
planned for the core release.

---

## 15. Explicitly Out of Scope

Version 2 does not aim to provide:

- complete ESG coverage,
- company ESG ratings,
- sustainability rankings,
- bank-risk modelling,
- financial-loss prediction,
- arbitrary 200-page PDF robustness,
- production-scale document processing,
- satellite-image analysis,
- a chatbot,
- a large RAG architecture,
- a vector database,
- cloud deployment solely for portfolio presentation,
- or production-readiness claims.

The project should remain focused on sustainability-data extraction,
validation, provenance, and methodological evaluation.

---

## 16. Development Stages

Development should proceed sequentially.

### P0 — Repository and CLI cleanup

- fix or replace the root CLI entry point
- remove or retire broken legacy modules
- align README claims with actual implementation
- clean unused dependencies and repository artifacts where appropriate
- preserve working v1 functionality where relevant

### P1 — Schema, evidence model, and provenance

- establish authoritative KPI schema
- introduce candidate evidence structure
- preserve document/page/context provenance
- correct result-status logic
- clarify extraction-score terminology

### P2 — Hidden truth and benchmark generator

- create ground-truth dataset
- generate controlled synthetic benchmark reports
- separate benchmark truth from extraction inputs
- retain useful v1 fixtures

### P3 — Reconciliation and review logic

- preserve multiple candidate observations
- detect agreement and conflicts
- introduce review-required logic
- distinguish true conflicts from valid contextual differences

### P4 — Nature/water extension

- retain GHG, energy, and water withdrawal
- add selected water-related indicators
- distinguish closely related water metrics
- add location and dependency context where appropriate

### P5 — LLM benchmark and evaluation

- strengthen schema-guided LLM extraction
- preserve optional operational fallback
- add independent benchmark mode
- compare methods against hidden truth

### P6 — Testing, notebooks, documentation, and final audit

- update automated tests
- regenerate notebooks and outputs
- update README
- verify documented commands
- verify reproducibility
- audit dependencies and repository hygiene
- confirm that claims match actual functionality

### P7 — Optional image/OCR experiment

Only after P0–P6 are stable.

This stage is not required for the v2.0.0 release.

---

## 17. Development Protocol

All v2 work is performed on the `dev/v2` branch.

The frozen v1 release remains preserved by the `v1.0.0` Git tag.

For each development stage:

1. define the exact change,
2. modify only the relevant files,
3. run appropriate tests,
4. inspect the Git diff,
5. confirm the working state,
6. create a meaningful signed commit,
7. push to `origin/dev/v2`.

Large mixed-purpose commits should be avoided.

The `main` branch should not receive v2 changes until the final v2 audit is
complete.

---

## 18. Acceptance Criteria for v2.0.0

Version 2 may be merged into `main` only when:

- the project installs cleanly from the declared environment,
- documented commands work,
- no known broken legacy entry points remain,
- automated tests pass,
- synthetic benchmark reports can be reproduced,
- hidden truth is separated from extraction,
- evidence provenance is preserved,
- related water metrics can be distinguished,
- conflicting evidence can trigger review,
- missing information can remain missing,
- deterministic and LLM-assisted methods can be evaluated separately,
- benchmark metrics are calculated against ground truth,
- README statements match actual implementation,
- synthetic-data limitations are stated clearly,
- no production-readiness claim is made,
- and image/OCR functionality is mentioned only if actually implemented.

After the final audit:

1. merge `dev/v2` into `main`,
2. verify the merged repository,
3. create a signed annotated `v2.0.0` tag,
4. push the tag,
5. optionally create a GitHub Release,
6. remove the temporary `dev/v2` branch after successful completion.