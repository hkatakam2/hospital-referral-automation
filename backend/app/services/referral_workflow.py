from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentRecord
from app.models.extraction import ExtractionRunRecord
from app.models.review_event import ReviewEventRecord
from app.repositories.workflow import WorkflowRepository
from app.schemas.referral import Referral
from app.schemas.workflow import InformationRequest, ReadyCommand, WorkflowAction, WorkflowCommand


class ReferralWorkflowService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = WorkflowRepository(session)

    def apply(
        self,
        referral_id: UUID,
        action: WorkflowAction,
        command: WorkflowCommand,
    ) -> Referral:
        try:
            record = self.repository.get_for_update(referral_id)
            if record is None:
                raise HTTPException(404, "Referral not found")
            if record.workflow_version != command.expected_workflow_version:
                raise HTTPException(
                    409,
                    "Workflow changed; refresh referral and history before retrying",
                )
            requesting = action == "request_missing_information"
            allowed = {
                "request_missing_information": {"received", "review_required"},
                "resume_review": {"missing_information"},
                "mark_ready": {"received", "review_required"},
                "reopen_review": {"ready"},
            }[action]
            if record.status not in allowed:
                raise HTTPException(409, "Action is not allowed in the current referral status")
            extraction_id = None
            requested_information = None
            if requesting:
                assert isinstance(command, InformationRequest)
                extraction_id = command.extraction_id
                requested_information = command.requested_information
                if extraction_id is not None:
                    run = self.session.get(ExtractionRunRecord, extraction_id)
                    if run is None or run.referral_id != referral_id:
                        raise HTTPException(422, "Extraction does not belong to this referral")
            reviewed_values_version = None
            if action == "mark_ready":
                assert isinstance(command, ReadyCommand)
                if record.values_version != command.expected_values_version:
                    raise HTTPException(
                        409, "Saved values changed; refresh corrections before retrying"
                    )
                run = self.session.scalar(
                    select(ExtractionRunRecord)
                    .where(
                        ExtractionRunRecord.referral_id == referral_id,
                    )
                    .order_by(ExtractionRunRecord.created_at.desc(), ExtractionRunRecord.id.desc())
                    .limit(1)
                )
                if run is None or run.id != command.extraction_id:
                    raise HTTPException(409, "Review the latest extraction before marking ready")
                document_ids = set(
                    self.session.scalars(
                        select(DocumentRecord.id).where(
                            DocumentRecord.referral_id == referral_id,
                        )
                    )
                )
                if not document_ids or document_ids != {
                    UUID(value) for value in run.result_json["source_document_ids"]
                }:
                    raise HTTPException(409, "Documents changed; run extraction and review again")
                if not run.result_json["complete"]:
                    raise HTTPException(409, "The latest extraction checklist is not satisfied")
                extraction_id = run.id
                reviewed_values_version = record.values_version
            previous_status = record.status
            record.status = {
                "request_missing_information": "missing_information",
                "resume_review": "review_required",
                "mark_ready": "ready",
                "reopen_review": "review_required",
            }[action]
            record.workflow_version += 1
            self.repository.add_event(
                ReviewEventRecord(
                    id=uuid4(),
                    referral_id=referral_id,
                    action=action,
                    previous_status=previous_status,
                    new_status=record.status,
                    workflow_version=record.workflow_version,
                    reviewer=command.reviewer,
                    reason=command.reason,
                    requested_information=requested_information,
                    extraction_id=extraction_id,
                    reviewed_values_version=reviewed_values_version,
                    created_at=datetime.now(timezone.utc),
                )
            )
            self.session.flush()
            result = Referral.model_validate(record, from_attributes=True)
            self.session.commit()
            return result
        except Exception:
            self.session.rollback()
            raise
