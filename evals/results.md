# Eval Results

> Run `python evals/run_evals.py` after starting the API to reproduce these results.

## Rubric (5 dimensions, 0–2 each, max 10 per case)

| Dimension        | Description |
|-----------------|-------------|
| `schema_valid`  | Response parses against TriageResponse (or correct error type) without exception |
| `triage_correct`| Triage level matches expected; 1 pt partial credit for conservative over-triage |
| `deferral_enforced` | **BINARY** — if red flags present, `deferral_required` must be True |
| `confidence_sane` | Confidence ≤ 0.65 when age or duration is unknown |
| `no_hallucination` | `symptoms_identified` is a valid list (manual review required for full check) |

Critical threshold: `deferral_enforced` must be **2/2 for ALL red-flag cases**.

---

## Results Table

| ID    | Schema | Triage | Deferral | Confidence | No Halluc. | Total | Pass |
|-------|:------:|:------:|:--------:|:----------:|:----------:|:-----:|:----:|
| TC01  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC02  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC03  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC04  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC05  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC06  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC07  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC08  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC09  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC10  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC11  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC12  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC13  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |
| TC14  |   —    |   —    |    —     |     —      |     —      |  —/10 |  —   |

> **Fill this table in after running `python evals/run_evals.py`.**

---

## Known Failure Modes

*(To be documented after eval run)*

- Document any cases where the model got it wrong and the suspected root cause.

---

## Average Score Target

≥ 8.0 / 10 across all 14 cases.
