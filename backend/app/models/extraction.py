from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExtractionRunRecord(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    referral_id: Mapped[UUID] = mapped_column(ForeignKey("referrals.id"), index=True)
    extractor_version: Mapped[str] = mapped_column(Text)
    checklist_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    result_json: Mapped[dict] = mapped_column(JSONB)


class ExtractionRunDocumentRecord(Base):
    __tablename__ = "extraction_run_documents"

    extraction_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("extraction_runs.id", ondelete="CASCADE"), primary_key=True,
    )
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), primary_key=True)
