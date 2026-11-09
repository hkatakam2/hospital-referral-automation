# How the referral application works

Read this page first for the overall picture. Look up unfamiliar words in the
[glossary](../GLOSSARY.md); use the [README](../README.md) for commands and API
details. [overall.md](overall.md) is the long-term roadmap, not a list of completed
features. Commits explain why the implementation changed.

## Follow the user workflow

1. **Register a referral.** The coordinator enters five required values and saves
   them. The application currently requires this before documents can be attached.
2. **Attach documents.** Upload a text-based PDF. The application stores the
   original file, reads its pages, and saves numbered page text and warnings.
3. **Run extraction.** Read all currently attached document text and suggest
   values, each with supporting evidence. Rules are the default; the coordinator can explicitly choose Gemini when enabled.
4. **Assess and save the result.** Check the suggestions against source text and
   field format rules. Identify missing, invalid, or conflicting fields, check
   page coverage, and save a new extraction run with its original output.
   The server applies its startup-loaded policy to those findings and retains the
   policy definition and requirement outcomes with each new snapshot.
5. **Review and correct.** Inspect evidence in the page-text viewer. Copy a usable
   candidate or type a correction into the draft, then explicitly save corrections.

## Keep three kinds of information separate

| Information | Example | What changes it? |
| --- | --- | --- |
| Saved referral values | The coordinator's saved date of birth | Registering the referral or saving corrections |
| Document text | `DOB: 1974-03-12` on PDF page 2 | A new upload creates another document; corrections do not edit source text |
| Saved extraction result | Two conflicting date-of-birth candidates and their quotes | Run extraction creates another snapshot; old runs remain unchanged |

Copying a candidate changes only the unsaved correction draft. Running extraction
does not overwrite saved referral values. Adding a document makes an older run
outdated; the UI warns about this until a new run includes the current attachments.

For example, two documents might contain different birth dates. Extraction retains
both candidates, the assessment selects neither and reports **conflicting**, and
the coordinator can inspect both quotes before saving a correction. That correction
does not erase the conflicting finding in the historical extraction run.

## Understand one button at a time

For **Run extraction**, follow these responsibilities in order:

| Responsibility | What happens | Code entry point |
| --- | --- | --- |
| Browser action | Request a run, prevent duplicate clicks while pending, then select the saved result | [Workspace coordinator](../frontend/src/hooks/useReferralWorkspace.ts) |
| API route | Validate the requested method and enforce server enablement | [Extraction routes](../backend/app/api/extractions.py) |
| Service | Capture page text, release the read session, request an assessment, and save in a new write session | [Extraction service](../backend/app/services/referral_extraction.py) |
| Extractor | Produce candidates from source text using Rules or opt-in Gemini | [Rule extractor](../backend/app/extraction/rule_based.py) |
| Assessment | Check evidence and normalization; derive field findings, then apply configured requirements and mandatory source coverage | [Shared assessment](../backend/app/extraction/assessment.py) |
| Repository | Store the assessed snapshot including its policy definition/outcomes, document links, and a separate original-output artifact in one transaction | [Extraction repository](../backend/app/repositories/extractions.py) |
| Review panel | Show the saved findings, evidence, provenance, and usable candidates | [Extraction panel](../frontend/src/components/ExtractionPanel.tsx) |

You do not need to learn every helper function first. Start with the service to see
the task's sequence, then open the component responsible for the part you want to
understand. Routes receive requests; services coordinate tasks; repositories store
records; schemas define the information passed between them. Manual referral
operations are simpler and use a repository directly from their routes.

For **Upload PDF**, start with the [document ingestion service](../backend/app/services/document_ingestion.py).
For **Save corrections**, start with the [referral routes](../backend/app/api/referrals.py).

## Know what is saved where

| Information | Location | What the reviewer can see |
| --- | --- | --- |
| Referral values | PostgreSQL | Saved values and the correction form |
| Original PDF | Local file storage | Attachment metadata; original-PDF viewing/download is not implemented |
| Document metadata and numbered page text | PostgreSQL | Document list and page-text viewer |
| Assessed extraction snapshots and input document links | PostgreSQL | Run history, candidates, findings, warnings, and recorded provenance |
| Original extraction output and available model claims/raw response | Separate PostgreSQL artifact table | An allowlisted provenance summary is shown; raw artifacts have no public endpoint |
| Unsaved correction draft | Browser memory | Editable values; unsaved edits are lost on reload/navigation |
| Evaluation reports | Files written by the evaluator; selected reports are retained in Git | Developer comparison reports, separate from referral history |

## Current boundaries

- The browser/API defaults to **rules/1**. Explicitly enabled Gemini sends synthetic
  source text to Google and may incur usage charges. Both methods use shared
  assessment, atomic artifact retention, evidence review, and correction drafts.
- The extraction service owns short read and write sessions; provider waiting holds
  no database connection. A run uses the attachments captured before extraction.
  The browser refreshes attachments afterward to identify outdated results.
- Method discovery checks local configuration, not provider connectivity. Failures
  return safe errors without saving a failed run or silently falling back to Rules.
  Processing is synchronous; leaving the page does not cancel it. Refresh history
  before retrying an interrupted request. Jobs and retry deduplication are future work.
- The separate [evaluation command](../backend/app/evaluation/README.md) compares
  quality without creating referral records. Browser integration checks use a
  deterministic provider stub unless live mode is explicitly selected.
- Evidence checks establish literal source support and controlled formatting.
  They do not prove semantic correctness or resistance to document instructions.
- Review shows extracted page text. OCR, original-PDF viewing, approvals, correction audit
  history, authentication, and document-first intake are not implemented.
- Completeness uses one server-configured, versioned JSON policy over the five
  supported extraction fields. The default requires all five. Every field still
  receives evidence checks and a finding; optional field issues remain visible
  without blocking completeness. Readable source coverage is always mandatory.
- Policy configuration is validated at startup; edits take effect after restart.
  New runs retain the exact definition and requirement results in their JSON
  snapshot. Older runs retain their checklist version without invented definitions.
  No policy tables or database migration are needed. Saved referral values and
  correction drafts never satisfy source requirements. The evaluator explicitly
  retains its original five-field policy regardless of application configuration.
- Policies are fictitious prototype checklists, not institutional policy or
  approval. Specialty selection, document-type requirements, policy editing, and
  human confirmation are future work. All data used in this project is synthetic.

## Keep this map useful

Update this page whenever a user action, component responsibility, storage boundary,
or implemented capability changes. Update the glossary when a new recurring term
is introduced or an existing meaning changes. Keep function-by-function detail in
the code and avoid turning this map into a second roadmap.

When explaining a change, answer: **What does the user do? What happens to the data?
Which responsibility changed?** Introduce function names only when they help locate
that behavior. For proof that the workflow works, use the repository's
[verification guide](../.agents/skills/verify-hospital-referrals/SKILL.md) and
[feature coverage map](../.agents/skills/verify-hospital-referrals/features/README.md).
The [retained Gemini workflow check](verification/gemini-workflow-2026-11-04.md)
distinguishes the default stubbed suite from the live synthetic provider journey.

The [retained completeness-policy check](verification/completeness-policy-2026-11-06.md)
records configuration retention, real API persistence and the optional-field UI probe.

## Coordinator workflow history

The workflow API records a missing-information request and explicitly resumes review.
New and migrated referrals start at **received**, with no invented historical events.
Requests move received/review-required referrals to **missing information**; Resume
review moves them to **review required**. Each action records the supplied demo reviewer,
server time, reason, previous/new status and workflow version. Requests also retain
what information is needed and an optional reference to a saved extraction run.

Workflow routes delegate to the [workflow service](../backend/app/services/referral_workflow.py).
The service locks the referral, checks the caller's expected workflow version and allowed
transition, verifies any extraction belongs to the referral, and commits status plus an
append-only review event together. The repository does not commit separately. History
is scoped to the referral and ordered by workflow version, newest first. Review events
live in PostgreSQL; they are separate from immutable extraction snapshots and artifacts.

Uploads, extraction and corrections do not change workflow status or close requests.
The application records requests locally; it sends no email or other notification.
Reviewer names are supplied demo identities, not authenticated identities. This history
covers workflow actions only; correction auditing and administrative approval remain
future work. An interrupted action should be checked through referral/history reads
before retrying; stale workflow versions and invalid transitions return a conflict.
