from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_session
from app.document_processing.pdf import DocumentInputError, PdfReaderAdapter
from app.models.referral import ReferralRecord
from app.repositories.documents import DocumentRepository
from app.schemas.document import DocumentDetail, DocumentSummary
from app.services.document_ingestion import DocumentIngestionService
from app.storage.local import LocalDocumentStorage

router = APIRouter(prefix="/referrals/{referral_id}/documents", tags=["documents"])
DatabaseSession = Annotated[Session, Depends(get_session)]


def get_ingestion_service(session: DatabaseSession) -> DocumentIngestionService:
    return DocumentIngestionService(
        session,
        LocalDocumentStorage(settings.document_storage_dir, settings.document_max_bytes),
        PdfReaderAdapter(settings.document_max_pages, settings.document_max_text_chars),
    )


@router.post("", response_model=DocumentDetail, status_code=201)
def upload_document(
    referral_id: UUID, file: UploadFile,
    service: Annotated[DocumentIngestionService, Depends(get_ingestion_service)],
) -> DocumentDetail:
    try:
        return service.ingest(referral_id, file.file, file.filename)
    except DocumentInputError as error:
        raise HTTPException(error.status_code, detail=error.detail) from error
    finally:
        file.file.close()


@router.get("", response_model=list[DocumentSummary])
def list_documents(referral_id: UUID, session: DatabaseSession) -> list[DocumentSummary]:
    if session.get(ReferralRecord, referral_id) is None:
        raise HTTPException(404, detail="Referral not found")
    return DocumentRepository(session).list(referral_id)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    referral_id: UUID, document_id: UUID, session: DatabaseSession,
) -> DocumentDetail:
    result = DocumentRepository(session).get(referral_id, document_id)
    if result is None:
        raise HTTPException(404, detail="Document not found")
    return result
