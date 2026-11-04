from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentPageRecord, DocumentRecord
from app.schemas.document import DocumentDetail, DocumentPage, DocumentSummary
from app.schemas.extraction import SourceDocument, SourcePage


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, document: DocumentRecord, pages: list[DocumentPageRecord]) -> None:
        # The ingestion service owns the transaction across the file and these rows.
        self.session.add(document)
        self.session.flush()
        self.session.add_all(pages)
        self.session.flush()

    def list(self, referral_id: UUID) -> list[DocumentSummary]:
        records = self.session.scalars(
            select(DocumentRecord).where(DocumentRecord.referral_id == referral_id)
            .order_by(DocumentRecord.created_at, DocumentRecord.id),
        )
        return [DocumentSummary.model_validate(record) for record in records]

    def get(self, referral_id: UUID, document_id: UUID) -> DocumentDetail | None:
        record = self.session.scalar(select(DocumentRecord).where(
            DocumentRecord.id == document_id, DocumentRecord.referral_id == referral_id,
        ))
        if record is None:
            return None
        pages = self.session.scalars(
            select(DocumentPageRecord).where(DocumentPageRecord.document_id == document_id)
            .order_by(DocumentPageRecord.page_number),
        )
        return DocumentDetail(
            **DocumentSummary.model_validate(record).model_dump(),
            pages=[DocumentPage.model_validate(page) for page in pages],
        )

    def load_extraction_sources(self, referral_id: UUID) -> list[SourceDocument]:
        # One joined query captures the documents/pages visible to this run.
        rows = self.session.execute(
            select(DocumentRecord, DocumentPageRecord)
            .join(DocumentPageRecord, DocumentPageRecord.document_id == DocumentRecord.id)
            .where(DocumentRecord.referral_id == referral_id)
            .order_by(DocumentRecord.created_at, DocumentRecord.id, DocumentPageRecord.page_number)
        )
        sources: dict[UUID, SourceDocument] = {}
        for document, page in rows:
            if document.id not in sources:
                sources[document.id] = SourceDocument(
                    document_id=document.id, parse_status=document.parse_status, pages=[],
                )
            sources[document.id].pages.append(SourcePage(
                page_number=page.page_number, text=page.text,
            ))
        return list(sources.values())
