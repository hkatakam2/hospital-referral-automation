# PDF document intake

## Sub-features

Upload to an existing referral, inspect attachment metadata and ordered page text, preserve partial pages, and reject unsupported/oversized inputs safely. Original bytes live in private local storage; metadata/text live in PostgreSQL.

Sources: `frontend/src/components/DocumentPanel.tsx`, `SourceTextViewer.tsx`, `backend/app/api/documents.py`, `services/document_ingestion.py`, `document_processing/pdf.py`, `storage/local.py`, `repositories/documents.py`.

## How to get to it (user POV)

Open a referral. Choose a file under Attach a synthetic PDF and select Upload PDF. Select its filename to open source text. Change Page to inspect each numbered page.

## Driving it with Playwright

Run `verify.py run --feature documents`. In `frontend/tests/review.spec.ts`, real synthetic PDFs are uploaded through the file input; successful uploads produce an attachment and source text. The rejection/partial-page journey submits non-PDF bytes, observes an error, uploads a two-page packet with one textless page, and observes its no-usable-text warning.

`backend/tests/test_documents.py` proves original bytes/checksum/size, generated private storage filenames and permissions, metadata/path boundaries, page persistence, scope isolation, stable repeated-upload behavior, and rollback/file cleanup on failures. Rejection cases cover empty, corrupt, blank, image-only, encrypted, byte/page/text limits, missing files and invalid identifiers. `test_pdf_reader.py` probes the reader/storage boundaries.

## Gotchas

`parsed` means text was extracted, not that all image content was read. `partial` cannot distinguish blank from scanned pages. OCR and original-PDF rendering/download are absent. Repeating an upload creates another document; no automatic retries or deduplication. Ordinary failures roll back; crash reconciliation across filesystem/database is not implemented. Not every parser rejection is driven in the UI; the backend suite supplies that coverage.
