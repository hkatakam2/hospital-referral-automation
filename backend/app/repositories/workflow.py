from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.referral import ReferralRecord
from app.models.review_event import ReviewEventRecord
from app.schemas.workflow import ReviewEvent


class WorkflowRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_for_update(self, referral_id: UUID) -> ReferralRecord | None:
        return self.session.scalar(
            select(ReferralRecord).where(ReferralRecord.id == referral_id).with_for_update(),
        )

    def add_event(self, event: ReviewEventRecord) -> None:
        self.session.add(event)

    def list_events(self, referral_id: UUID) -> list[ReviewEvent]:
        records = self.session.scalars(select(ReviewEventRecord).where(
            ReviewEventRecord.referral_id == referral_id,
        ).order_by(ReviewEventRecord.workflow_version.desc()))
        return [ReviewEvent.model_validate(record) for record in records]
