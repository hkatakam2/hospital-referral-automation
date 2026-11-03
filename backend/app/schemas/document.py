from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    referral_id: UUID
    original_filename: str
    sha256: str
    size_bytes: int
    page_count: int
    parse_status: Literal["parsed", "partial"]
    parser_version: str
    created_at: datetime


class DocumentPage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    page_number: int
    text: str
    text_status: Literal["extracted", "no_text"]


class DocumentDetail(DocumentSummary):
    pages: list[DocumentPage]
