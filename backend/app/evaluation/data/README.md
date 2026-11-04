# Synthetic referral source-text dataset, version 1

`referrals-v1.json` contains 30 fictional packets and independent administrative
annotations for all five required fields. The expected values and findings were
specified during fixture authoring, without calling the production extractor.
Evidence quotes point to exact text on a document and one-based page. IDs are
fixed so report failures can be compared between runs.

The corpus includes labeled forms, multiple pages/documents, duplicates, missing
fields, invalid values, conflicts, partial coverage, alternate labels/date formats,
and narrative letters. Alternate formats and narratives deliberately describe
facts that a human can read even when `rules/1` cannot recognize them. A US date
is annotated as a known ISO-normalized date; the impossible date is invalid.
Cardiology consultation normalizes to `cardiology`. Other text preserves case,
with whitespace collapsed. Narratives explicitly refer to the same synthetic
patient and clinic as the labeled packets.

All five fields are required; there are no optional or not-applicable fields in
this version. Missing means absent, invalid means present but unusable, and
conflicting means different valid values with no selected value. Invalid values
take precedence over conflicts, matching the documented checklist contract.
All non-found fields have null selected values. Repeated equivalent values have
one selection and evidence from each source occurrence. A packet is complete
only if all fields are found and all pages have text. Partial pages deliberately
model unknown coverage; no OCR truth is claimed for their empty text.

This is a small, curated challenge set with repeated identities, not a sampled
clinical population or an unbiased estimate of real-world quality. It measures
extraction and assessment from already parsed text, excluding PDF parsing, OCR,
HTTP, persistence, and human corrections. Do not tune expected answers to match
extractor output. Changes to annotations or packets require a new dataset version
and a new baseline. Report the file SHA-256 as well as the version.
