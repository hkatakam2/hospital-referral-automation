from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.repositories.referrals import InMemoryReferralRepository
from app.schemas.referral import Referral, ReferralCreate

router = APIRouter(prefix="/referrals", tags=["referrals"])


def get_referral_repository(request: Request) -> InMemoryReferralRepository:
    return request.app.state.referral_repository


Repository = Annotated[InMemoryReferralRepository, Depends(get_referral_repository)]


@router.post("", response_model=Referral, status_code=status.HTTP_201_CREATED)
def create_referral(data: ReferralCreate, repository: Repository) -> Referral:
    return repository.create(data)


@router.get("/{referral_id}", response_model=Referral)
def get_referral(referral_id: UUID, repository: Repository) -> Referral:
    referral = repository.get(referral_id)
    if referral is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")
    return referral
