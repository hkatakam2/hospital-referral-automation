from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.correction_event import CorrectionEventRecord
from app.models.referral import ReferralRecord
from app.schemas.correction import CorrectionEvent


class CorrectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_for_update(self, referral_id: UUID) -> ReferralRecord | None:
        return self.session.scalar(select(ReferralRecord).where(
            ReferralRecord.id == referral_id,
        ).with_for_update())

    def add_event(self, event: CorrectionEventRecord) -> None:
        self.session.add(event)

    def list_events(self, referral_id: UUID) -> list[CorrectionEvent]:
        records = self.session.scalars(select(CorrectionEventRecord).where(
            CorrectionEventRecord.referral_id == referral_id,
        ).order_by(CorrectionEventRecord.values_version.desc()))
        return [CorrectionEvent.model_validate(record) for record in records]
