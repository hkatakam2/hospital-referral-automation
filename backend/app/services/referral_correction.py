from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.correction_event import CorrectionEventRecord
from app.repositories.corrections import CorrectionRepository
from app.schemas.referral import CorrectionCommand, Referral, ReferralUpdate


class ReferralCorrectionService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = CorrectionRepository(session)

    def apply(self, referral_id: UUID, command: CorrectionCommand) -> Referral:
        try:
            record = self.repository.get_for_update(referral_id)
            if record is None:
                raise HTTPException(404, "Referral not found")
            if record.values_version != command.expected_values_version:
                raise HTTPException(
                    409, "Saved values changed; refresh corrections before retrying",
                )
            supplied = command.model_dump(
                exclude_unset=True, include=set(ReferralUpdate.model_fields),
            )
            changes = {}
            for field, value in supplied.items():
                previous = getattr(record, field)
                if previous != value:
                    changes[field] = {"previous": str(previous), "new": str(value)}
                    setattr(record, field, value)
            if changes:
                record.values_version += 1
                self.repository.add_event(CorrectionEventRecord(
                    id=uuid4(), referral_id=referral_id, values_version=record.values_version,
                    reviewer=command.reviewer, reason=command.reason, changes=changes,
                    created_at=datetime.now(timezone.utc),
                ))
            self.session.flush()
            result = Referral.model_validate(record, from_attributes=True)
            self.session.commit()
            return result
        except Exception:
            self.session.rollback()
            raise
