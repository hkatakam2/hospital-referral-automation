from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentPageRecord, DocumentRecord
from app.schemas.document import DocumentDetail, DocumentPage, DocumentSummary


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
