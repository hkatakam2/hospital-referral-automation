# Extraction baseline

Dataset: `synthetic-referrals/1` (30 packets)

SHA-256: `e9c52a8214d43b92ab11674a1b06251ac5806bb01b9a4194910486470f2e2f66`

Extractor: `rules/1`; checklist: `five-required-fields/2`; Python: `3.13.12`.

This curated source-text challenge set does not estimate clinical performance. See the evaluation README for scoring rules and limits.

## Overall

| Metric | Result (numerator/denominator) |
| --- | --- |
| exact_match_accuracy | 92.0% (138/150) |
| finding_accuracy | 92.7% (139/150) |
| value_precision | 99.2% (125/126) |
| value_recall | 91.2% (125/137) |
| evidence_precision | 100.0% (144/144) |
| evidence_recall | 93.5% (144/154) |
| missing_precision | 37.5% (6/16) |
| missing_recall | 100.0% (6/6) |
| conflicting_precision | 100.0% (3/3) |
| conflicting_recall | 100.0% (3/3) |
| invalid_precision | 80.0% (4/5) |
| invalid_recall | 100.0% (4/4) |
| false_completeness_rate | 0.0% (0/15) |
| packet_completeness_accuracy | 80.0% (24/30) |

## By field

| Group | Value precision | Value recall | Exact match | Finding accuracy |
| --- | --- | --- | --- | --- |
| patient_name | 96.2% (25/26) | 89.3% (25/28) | 90.0% (27/30) | 93.3% (28/30) |
| date_of_birth | 100.0% (22/22) | 88.0% (22/25) | 90.0% (27/30) | 90.0% (27/30) |
| referring_organization | 100.0% (26/26) | 92.9% (26/28) | 93.3% (28/30) | 93.3% (28/30) |
| requested_specialty | 100.0% (26/26) | 92.9% (26/28) | 93.3% (28/30) | 93.3% (28/30) |
| referral_reason | 100.0% (26/26) | 92.9% (26/28) | 93.3% (28/30) | 93.3% (28/30) |

## By document type

| Group | Value precision | Value recall | Exact match | Finding accuracy |
| --- | --- | --- | --- | --- |
| alternate_format | 95.0% (19/20) | 76.0% (19/25) | 76.0% (19/25) | 80.0% (20/25) |
| conflicting | 100.0% (16/16) | 100.0% (16/16) | 100.0% (20/20) | 100.0% (20/20) |
| invalid | 100.0% (12/12) | 100.0% (12/12) | 100.0% (15/15) | 100.0% (15/15) |
| labeled | 100.0% (25/25) | 100.0% (25/25) | 100.0% (25/25) | 100.0% (25/25) |
| missing | 100.0% (20/20) | 100.0% (20/20) | 100.0% (25/25) | 100.0% (25/25) |
| multipage | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) |
| multiple_documents | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) |
| narrative | 100.0% (3/3) | 33.3% (3/9) | 40.0% (4/10) | 40.0% (4/10) |
| partial | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) |

## Processing latency

One in-process extraction plus assessment per packet; no warmup, IO or scoring.

30 samples; mean 0.174 ms; p50 0.130 ms; p95 0.432 ms. Timing varies by machine and run.

## Failure examples

### abbreviated-patient (alternate_format)

Complete: expected `True`, actual `False`.

```json
{"field": "patient_name", "expected_value": "Avery Morgan", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000960", 1, "Pt: Avery Morgan"]], "unexpected_evidence": []}
```

### abbreviated-organization (alternate_format)

Complete: expected `True`, actual `False`.

```json
{"field": "referring_organization", "expected_value": "Lakeside Primary Care", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-0000000009c4", 1, "Referrer: Lakeside Primary Care"]], "unexpected_evidence": []}
```

### us-format-dob (alternate_format)

Complete: expected `True`, actual `False`.

```json
{"field": "date_of_birth", "expected_value": "1974-03-12", "actual_value": null, "expected_status": "found", "actual_status": "invalid", "missing_evidence": [], "unexpected_evidence": []}
```

### unfamiliar-service-label (alternate_format)

Complete: expected `True`, actual `False`.

```json
{"field": "requested_specialty", "expected_value": "cardiology", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000a8c", 1, "Consult service: Cardiology"]], "unexpected_evidence": []}
```

### narrative-letter (narrative)

Complete: expected `True`, actual `False`.

```json
{"field": "patient_name", "expected_value": "Avery Morgan", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000af0", 1, "Avery Morgan was born on March 12, 1974."]], "unexpected_evidence": []}
```

```json
{"field": "date_of_birth", "expected_value": "1974-03-12", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000af0", 1, "Avery Morgan was born on March 12, 1974."]], "unexpected_evidence": []}
```

```json
{"field": "referring_organization", "expected_value": "Lakeside Primary Care", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000af0", 1, "Lakeside Primary Care requests a cardiology consultation for recurrent palpitations."]], "unexpected_evidence": []}
```

```json
{"field": "requested_specialty", "expected_value": "cardiology", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000af0", 1, "Lakeside Primary Care requests a cardiology consultation for recurrent palpitations."]], "unexpected_evidence": []}
```

```json
{"field": "referral_reason", "expected_value": "Recurrent palpitations", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000af0", 1, "Lakeside Primary Care requests a cardiology consultation for recurrent palpitations."]], "unexpected_evidence": []}
```

### inline-fields (alternate_format)

Complete: expected `True`, actual `False`.

```json
{"field": "patient_name", "expected_value": "Avery Morgan", "actual_value": "Avery Morgan; DOB: 1974-03-12", "expected_status": "found", "actual_status": "found", "missing_evidence": [], "unexpected_evidence": []}
```

```json
{"field": "date_of_birth", "expected_value": "1974-03-12", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000b54", 1, "Patient: Avery Morgan; DOB: 1974-03-12"]], "unexpected_evidence": []}
```

### narrative-missing-organization (narrative)

Complete: expected `False`, actual `False`.

```json
{"field": "referral_reason", "expected_value": "Recurrent palpitations", "actual_value": null, "expected_status": "found", "actual_status": "missing", "missing_evidence": [["00000000-0000-0000-0000-000000000bb8", 1, "The reason for referral is recurrent palpitations."]], "unexpected_evidence": []}
```

