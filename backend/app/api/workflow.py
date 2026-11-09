from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.referral import ReferralRecord
from app.repositories.workflow import WorkflowRepository
from app.schemas.referral import Referral
from app.schemas.workflow import InformationRequest, ReviewEvent, WorkflowCommand
from app.services.referral_workflow import ReferralWorkflowService

router = APIRouter(prefix="/referrals/{referral_id}", tags=["workflow"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.post("/information-requests", response_model=Referral, status_code=201)
def request_information(
    referral_id: UUID, data: InformationRequest, session: DatabaseSession,
) -> Referral:
    return ReferralWorkflowService(session).apply(referral_id, "request_missing_information", data)


@router.post("/resume-review", response_model=Referral)
def resume_review(referral_id: UUID, data: WorkflowCommand, session: DatabaseSession) -> Referral:
    return ReferralWorkflowService(session).apply(referral_id, "resume_review", data)


@router.get("/review-events", response_model=list[ReviewEvent])
def list_events(referral_id: UUID, session: DatabaseSession) -> list[ReviewEvent]:
    if session.get(ReferralRecord, referral_id) is None:
        raise HTTPException(404, "Referral not found")
    return WorkflowRepository(session).list_events(referral_id)
