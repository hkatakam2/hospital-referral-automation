from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.referral import ReferralRecord
from app.schemas.referral import Referral, ReferralCreate


class ReferralRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _response(record: ReferralRecord) -> Referral:
        return Referral.model_validate(record, from_attributes=True)

    def create(self, data: ReferralCreate) -> Referral:
        record = ReferralRecord(
            **data.model_dump(), id=uuid4(), created_at=datetime.now(timezone.utc),
        )
        self.session.add(record)
        self.session.commit()
        return self._response(record)

    def get(self, referral_id: UUID) -> Referral | None:
        record = self.session.get(ReferralRecord, referral_id)
        return self._response(record) if record is not None else None

    def list(self) -> list[Referral]:
        records = self.session.scalars(
            select(ReferralRecord).order_by(ReferralRecord.created_at, ReferralRecord.id),
        )
        return [self._response(record) for record in records]
