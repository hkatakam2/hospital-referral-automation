from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.extraction.base import Extractor
from app.models.referral import ReferralRecord
from app.repositories.documents import DocumentRepository
from app.repositories.extractions import ExtractionRepository
from app.schemas.extraction import ExtractionDetail
from app.services.completeness import CHECKLIST_VERSION, check_completeness


class ExtractionInputError(Exception):
    def __init__(self, detail: str, status_code: int):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class ReferralExtractionService:
    def __init__(self, session: Session, extractor: Extractor):
        self.session = session
        self.extractor = extractor

    def run(self, referral_id: UUID) -> ExtractionDetail:
        if self.session.get(ReferralRecord, referral_id) is None:
            raise ExtractionInputError("Referral not found", 404)
        sources = DocumentRepository(self.session).load_extraction_sources(referral_id)
        if not sources:
            raise ExtractionInputError("Attach at least one document before extraction", 422)
        fields = self.extractor.extract(sources)
        findings, warnings, complete = check_completeness(fields, sources)
        result = ExtractionDetail(
            id=uuid4(), referral_id=referral_id, extractor_version=self.extractor.version,
            checklist_version=CHECKLIST_VERSION, created_at=datetime.now(timezone.utc),
            source_document_ids=[source.document_id for source in sources],
            fields=fields, findings=findings, warnings=warnings, complete=complete,
        )
        try:
            ExtractionRepository(self.session).add(result)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return result
