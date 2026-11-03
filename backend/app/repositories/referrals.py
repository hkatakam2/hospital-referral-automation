from datetime import datetime, timezone
from threading import Lock
from uuid import UUID, uuid4

from app.schemas.referral import Referral, ReferralCreate, ReferralUpdate


class InMemoryReferralRepository:
    def __init__(self) -> None:
        self._referrals: dict[UUID, Referral] = {}
        self._lock = Lock()

    def create(self, data: ReferralCreate) -> Referral:
        referral = Referral(
            **data.model_dump(),
            id=uuid4(),
            created_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._referrals[referral.id] = referral
        return referral

    def get(self, referral_id: UUID) -> Referral | None:
        with self._lock:
            return self._referrals.get(referral_id)

    def list(self) -> list[Referral]:
        with self._lock:
            return list(self._referrals.values())

    def update(self, referral_id: UUID, changes: ReferralUpdate) -> Referral | None:
        with self._lock:
            existing = self._referrals.get(referral_id)
            if existing is None:
                return None
            updated = Referral.model_validate({
                **existing.model_dump(),
                **changes.model_dump(exclude_unset=True),
            })
            self._referrals[referral_id] = updated
            return updated
