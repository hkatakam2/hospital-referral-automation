# Implemented feature map

Scope: the browser referral workflow through Level 6, offline quality evaluation,
opt-in browser/API Gemini extraction, and file-configured field completeness policies. Paths below are relative to the repository root. Every feature distinguishes real integration evidence from mocked probes. For all current functionality, run the skill helper with its default `--feature all`.

| Feature | User surface | Verification map |
| --- | --- | --- |
| Intake | Inbox, creation, registered referral | [intake.md](intake.md) |
| Documents | PDF upload, attachment list, numbered text | [documents.md](documents.md) |
| Extraction | Run action, checklist, saved history | [extraction.md](extraction.md) |
| Review | Candidate evidence, correction draft, saved values | [review.md](review.md) |
| Evaluation | Rule baseline and Gemini command-line comparison | [evaluation.md](evaluation.md) |
| Persistence | Reload/restart recovery, storage, transactions | [persistence.md](persistence.md) |

Source of truth: current code and executable assertions, with the roadmap as context. Current exclusions include original-PDF rendering/download, OCR, approvals, audit events, authentication, and document-first drafts. Inbox processing status is not a persisted lifecycle model.
