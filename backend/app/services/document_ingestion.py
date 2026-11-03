from datetime import datetime, timezone
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.document_processing.pdf import DocumentInputError, PdfReaderAdapter
from app.models.document import DocumentPageRecord, DocumentRecord
from app.models.referral import ReferralRecord
from app.repositories.documents import DocumentRepository
from app.schemas.document import DocumentDetail
from app.storage.local import LocalDocumentStorage


class DocumentIngestionService:
    def __init__(self, session: Session, storage: LocalDocumentStorage, reader: PdfReaderAdapter):
        self.session = session
        self.storage = storage
        self.reader = reader

    def ingest(self, referral_id: UUID, source: BinaryIO, filename: str | None) -> DocumentDetail:
        if self.session.get(ReferralRecord, referral_id) is None:
            raise DocumentInputError("Referral not found", 404)
        # Client filenames are display-only. Never use them as filesystem paths.
        filename = (filename or "document.pdf").replace("\\", "/").rsplit("/", 1)[-1]
        filename = "".join(char for char in filename if char.isprintable())[:255]
        filename = filename or "document.pdf"
        repository = DocumentRepository(self.session)
        key = None
        try:
            with self.storage.stage(source) as staged:
                parsed = self.reader.read(staged.path)
                document_id = uuid4()
                pages = [DocumentPageRecord(
                    document_id=document_id, page_number=page.page_number, text=page.text,
                    text_status="extracted" if page.text.strip() else "no_text",
                ) for page in parsed.pages]
                key = self.storage.promote(staged, document_id)
                repository.add(DocumentRecord(
                    id=document_id, referral_id=referral_id, original_filename=filename,
                    storage_key=key, sha256=staged.sha256, size_bytes=staged.size_bytes,
                    page_count=len(pages), parser_version=parsed.parser_version,
                    parse_status="partial" if any(p.text_status == "no_text" for p in pages)
                    else "parsed", created_at=datetime.now(timezone.utc),
                ), pages)
                result = repository.get(referral_id, document_id)
                assert result is not None
                self.session.commit()
                return result
        except Exception:
            self.session.rollback()
            if key is not None:
                self.storage.remove(key)
            raise
