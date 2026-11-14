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


## Coordinator workflow

| Term | Plain meaning |
| --- | --- |
| Workflow status | The saved administrative stage: received, missing information, review required, or ready for downstream processing. It is separate from extraction checklist completeness and does not grant approval. |
| Missing-information request | A coordinator's saved description of information needed and why. It changes workflow status and stays in history after review resumes; the application does not send it externally. |
| Review event | An append-only application record of a workflow action, including supplied demo reviewer, server time, reason, previous/new status and version. It does not record field correction history. |
| Workflow version | A counter advanced by each saved workflow action. A stale expected version prevents a browser from applying a decision against an older workflow state. |

## Saved correction history

| Term | Plain meaning |
| --- | --- |
| Correction event | An append-only record of one changed correction save: actual previous/new field values, supplied demo reviewer, reason, and server time. Separate from workflow events, source text, and extraction snapshots. Earlier corrections are not reconstructed. |
| Saved-values version | A counter advanced by each correction save that changes values. A stale expected version rejects a save; workflow actions do not advance this counter. |

## Administrative readiness

| Term | Plain meaning |
| --- | --- |
| Ready for downstream processing | A saved administrative status explicitly recorded by a demo reviewer after the current packet passes its retained checklist. It does not grant clinical approval or send data downstream. |
| Ready decision | A workflow event identifying the extraction run and saved-values version reviewed, together with reviewer, reason and time. It never includes unsaved correction drafts. |
| Reopen review | An explicit action moving a ready referral back to review required before documents or saved values can change. Previous decisions stay in history. |
| Reviewed saved-values version | The version number of the saved referral values assessed when a ready decision was recorded. It is separate from the immutable source-text assessment and the browser's unsaved draft. |
