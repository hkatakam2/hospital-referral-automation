from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.extraction import (
    ExtractionArtifactRecord,
    ExtractionRunDocumentRecord,
    ExtractionRunRecord,
)
from app.schemas.extraction import ExtractionDetail, ExtractionSummary


class ExtractionRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, result: ExtractionDetail, artifact: dict) -> None:
        self.session.add(ExtractionRunRecord(
            id=result.id, referral_id=result.referral_id,
            extractor_version=result.extractor_version, checklist_version=result.checklist_version,
            created_at=result.created_at, result_json=result.model_dump(mode="json"),
        ))
        self.session.flush()
        self.session.add(ExtractionArtifactRecord(
            extraction_run_id=result.id, artifact_json=artifact,
        ))
        self.session.add_all([
            ExtractionRunDocumentRecord(extraction_run_id=result.id, document_id=document_id)
            for document_id in result.source_document_ids
        ])
        self.session.flush()

    def get(self, referral_id: UUID, extraction_id: UUID) -> ExtractionDetail | None:
        record = self.session.scalar(select(ExtractionRunRecord).where(
            ExtractionRunRecord.id == extraction_id, ExtractionRunRecord.referral_id == referral_id,
        ))
        return ExtractionDetail.model_validate(record.result_json) if record else None

    def list(self, referral_id: UUID) -> list[ExtractionSummary]:
        records = self.session.scalars(
            select(ExtractionRunRecord).where(ExtractionRunRecord.referral_id == referral_id)
            .order_by(ExtractionRunRecord.created_at.desc(), ExtractionRunRecord.id.desc())
        )
        return [ExtractionSummary.model_validate(record.result_json) for record in records]
