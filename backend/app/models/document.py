from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="document_positive_size"),
        CheckConstraint("page_count > 0", name="document_positive_pages"),
        CheckConstraint("parse_status IN ('parsed', 'partial')", name="document_parse_status"),
        CheckConstraint("length(sha256) = 64", name="document_checksum_length"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    referral_id: Mapped[UUID] = mapped_column(ForeignKey("referrals.id"), index=True)
    original_filename: Mapped[str] = mapped_column(Text)
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int] = mapped_column(Integer)
    parse_status: Mapped[str] = mapped_column(String(16))
    parser_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DocumentPageRecord(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        CheckConstraint("page_number > 0", name="document_page_positive_number"),
        CheckConstraint(
            "text_status IN ('extracted', 'no_text')", name="document_page_text_status",
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    text_status: Mapped[str] = mapped_column(String(16))
