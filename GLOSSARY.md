# Referral terminology

| Term | Meaning |
| --- | --- |
| Referral review workspace | The place where a reviewer inspects a registered referral, attached documents, extraction history and evidence, and prepares corrections. |
| Source-text assessment | An evaluation of document text that produces candidates, selected values, findings and source-coverage warnings for all five supported referral fields. It does not grant approval. |
| Extraction run | A saved snapshot of a source-text assessment for a particular set of attached documents. Later documents and corrections do not rewrite it. |
| Correction draft | Unsaved changes to the registered referral, including values copied from extraction candidates. |
| Source claim | A proposed field value and supporting source quotation, before the application assesses it. |
| Source-location check | A check that cited documents, pages, quotations, and claimed source text exist in the supplied packet. It does not establish that the text supports the meaning of a claim. |
| Extractor / adapter | The component that produces suggestions. Rules use labeled text patterns; Gemini uses a model. Both follow the same input/output contract, with Rules as the browser/API default and Gemini available when explicitly enabled. |
| Completeness checklist | A saved assessment of configured required fields and readable source coverage. The default requires all five fields found. Optional field issues stay visible but do not block the checklist. “Complete” is not administrative or clinical approval. |
| Referral policy | A versioned, fictitious checklist configuration naming which supported extraction fields must be found. The server loads one policy at startup; new extraction snapshots save its exact definition and requirement outcomes. It assesses document findings, not saved referral values or correction drafts. |
