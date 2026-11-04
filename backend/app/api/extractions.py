from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.extraction.rule_based import RuleBasedExtractor
from app.models.referral import ReferralRecord
from app.repositories.extractions import ExtractionRepository
from app.schemas.extraction import ExtractionDetail, ExtractionSummary
from app.services.referral_extraction import ExtractionInputError, ReferralExtractionService

router = APIRouter(prefix="/referrals/{referral_id}/extractions", tags=["extractions"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("", response_model=ExtractionDetail, status_code=201)
def create_extraction(referral_id: UUID, session: DatabaseSession) -> ExtractionDetail:
    try:
        return ReferralExtractionService(session, RuleBasedExtractor()).run(referral_id)
    except ExtractionInputError as error:
        raise HTTPException(error.status_code, detail=error.detail) from error


@router.get("", response_model=list[ExtractionSummary])
def list_extractions(referral_id: UUID, session: DatabaseSession) -> list[ExtractionSummary]:
    if session.get(ReferralRecord, referral_id) is None:
        raise HTTPException(404, detail="Referral not found")
    return ExtractionRepository(session).list(referral_id)


@router.get("/{extraction_id}", response_model=ExtractionDetail)
def get_extraction(
    referral_id: UUID, extraction_id: UUID, session: DatabaseSession,
) -> ExtractionDetail:
    result = ExtractionRepository(session).get(referral_id, extraction_id)
    if result is None:
        raise HTTPException(404, detail="Extraction not found")
    return result
