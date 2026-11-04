# Extraction baseline

Dataset: `synthetic-referrals/1` (30 packets)

SHA-256: `e9c52a8214d43b92ab11674a1b06251ac5806bb01b9a4194910486470f2e2f66`

Extractor: `gemini-claims/1`; checklist: `five-required-fields/2`; Python: `3.13.12`.

This curated source-text challenge set does not estimate clinical performance. See the evaluation README for scoring rules and limits.

## Overall

| Metric | Result (numerator/denominator) |
| --- | --- |
| exact_match_accuracy | 98.0% (147/150) |
| finding_accuracy | 98.7% (148/150) |
| value_precision | 98.5% (134/136) |
| value_recall | 97.8% (134/137) |
| evidence_precision | 100.0% (153/153) |
| evidence_recall | 99.4% (153/154) |
| missing_precision | 85.7% (6/7) |
| missing_recall | 100.0% (6/6) |
| conflicting_precision | 100.0% (3/3) |
| conflicting_recall | 100.0% (3/3) |
| invalid_precision | 75.0% (3/4) |
| invalid_recall | 75.0% (3/4) |
| false_completeness_rate | 0.0% (0/15) |
| packet_completeness_accuracy | 96.7% (29/30) |

## By field

| Group | Value precision | Value recall | Exact match | Finding accuracy |
| --- | --- | --- | --- | --- |
| patient_name | 100.0% (28/28) | 100.0% (28/28) | 100.0% (30/30) | 100.0% (30/30) |
| date_of_birth | 100.0% (24/24) | 96.0% (24/25) | 96.7% (29/30) | 93.3% (28/30) |
| referring_organization | 100.0% (28/28) | 100.0% (28/28) | 100.0% (30/30) | 100.0% (30/30) |
| requested_specialty | 100.0% (28/28) | 100.0% (28/28) | 100.0% (30/30) | 100.0% (30/30) |
| referral_reason | 92.9% (26/28) | 92.9% (26/28) | 93.3% (28/30) | 100.0% (30/30) |

## By document type

| Group | Value precision | Value recall | Exact match | Finding accuracy |
| --- | --- | --- | --- | --- |
| alternate_format | 100.0% (24/24) | 96.0% (24/25) | 96.0% (24/25) | 96.0% (24/25) |
| conflicting | 100.0% (16/16) | 100.0% (16/16) | 100.0% (20/20) | 100.0% (20/20) |
| invalid | 100.0% (12/12) | 100.0% (12/12) | 100.0% (15/15) | 93.3% (14/15) |
| labeled | 100.0% (25/25) | 100.0% (25/25) | 100.0% (25/25) | 100.0% (25/25) |
| missing | 100.0% (20/20) | 100.0% (20/20) | 100.0% (25/25) | 100.0% (25/25) |
| multipage | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) |
| multiple_documents | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) |
| narrative | 77.8% (7/9) | 77.8% (7/9) | 80.0% (8/10) | 100.0% (10/10) |
| partial | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) |

## Execution

Estimated total cost: None

Pricing assumptions (per million tokens): `null`.

Unknown cost is null; estimates include reported thinking tokens. Per-packet model, prompt, usage and request timing are in report.json.

Source checks: `{"checked": 148, "rejected": 0}`. These test source locations and literal support, not semantic entailment.

## Processing latency

One in-process extraction plus assessment per packet; no warmup, dataset IO or scoring; includes provider IO when selected.

30 samples; mean 7831.601 ms; p50 7739.916 ms; p95 11931.523 ms. Timing varies by machine and run.

## Failure examples

### empty-dob (invalid)

Complete: expected `False`, actual `False`.

```json
{"field": "date_of_birth", "expected_value": null, "actual_value": null, "expected_status": "invalid", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-0000000005dc", 1, "DOB: "]], "unexpected_evidence": []}
```

### us-format-dob (alternate_format)

Complete: expected `True`, actual `False`.

```json
{"field": "date_of_birth", "expected_value": "1974-03-12", "actual_value": null, "expected_status": "found", "actual_status": "invalid", "missing_evidence": [], "unexpected_evidence": []}
```

### narrative-letter (narrative)

Complete: expected `True`, actual `True`.

```json
{"field": "referral_reason", "expected_value": "Recurrent palpitations", "actual_value": "recurrent palpitations", "expected_status": "found", "actual_status": "found", "missing_evidence": [], "unexpected_evidence": []}
```

### narrative-missing-organization (narrative)

Complete: expected `False`, actual `False`.

```json
{"field": "referral_reason", "expected_value": "Recurrent palpitations", "actual_value": "recurrent palpitations", "expected_status": "found", "actual_status": "found", "missing_evidence": [], "unexpected_evidence": []}
```
