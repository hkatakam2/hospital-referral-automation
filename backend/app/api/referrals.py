from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.repositories.referrals import ReferralRepository
from app.schemas.referral import Referral, ReferralCreate, ReferralUpdate

router = APIRouter(prefix="/referrals", tags=["referrals"])


def get_referral_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ReferralRepository:
    return ReferralRepository(session)


Repository = Annotated[ReferralRepository, Depends(get_referral_repository)]


@router.post("", response_model=Referral, status_code=status.HTTP_201_CREATED)
def create_referral(data: ReferralCreate, repository: Repository) -> Referral:
    return repository.create(data)


@router.get("", response_model=list[Referral])
def list_referrals(repository: Repository) -> list[Referral]:
    return repository.list()


@router.get("/{referral_id}", response_model=Referral)
def get_referral(referral_id: UUID, repository: Repository) -> Referral:
    referral = repository.get(referral_id)
    if referral is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")
    return referral


@router.patch("/{referral_id}", response_model=Referral)
def update_referral(
    referral_id: UUID, data: ReferralUpdate, repository: Repository,
) -> Referral:
    referral = repository.update(referral_id, data)
    if referral is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")
    return referral
