"""Validated, independently annotated source-text evaluation packets."""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.extraction.assessment import REQUIRED_FIELDS
from app.schemas.extraction import Evidence, FieldName, SourceDocument

DEFAULT_DATASET = Path(__file__).parent / "data" / "referrals-v1.json"


class Annotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["found", "missing", "invalid", "conflicting"]
    value: str | None
    evidence: list[Evidence]

    @model_validator(mode="after")
    def consistent_value(self):
        if (self.status == "found") != (self.value is not None):
            raise ValueError("Only found fields must have a selected value")
        if (self.status == "missing") != (not self.evidence):
            raise ValueError("Missing fields alone must have no evidence")
        return self


class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    document_type: str
    sources: list[SourceDocument]
    expected: dict[FieldName, Annotation]
    complete: bool

    @model_validator(mode="after")
    def validate_annotations(self):
        if set(self.expected) != set(REQUIRED_FIELDS):
            raise ValueError("Every packet must annotate all five fields")
        ids = [source.document_id for source in self.sources]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Sources must have unique document IDs and cannot be empty")
        pages = {}
        for source in self.sources:
            numbers = [page.page_number for page in source.pages]
            if numbers != list(range(1, len(numbers) + 1)) or not numbers:
                raise ValueError("Source pages must be contiguous and one-based")
            partial = any(not page.text.strip() for page in source.pages)
            if partial != (source.parse_status == "partial"):
                raise ValueError("Parse status must describe text coverage")
            for page in source.pages:
                pages[source.document_id, page.page_number] = page.text
        for annotation in self.expected.values():
            for evidence in annotation.evidence:
                source_text = pages.get((evidence.document_id, evidence.page_number), "")
                if not evidence.quote.strip() or evidence.quote not in source_text:
                    raise ValueError("Expected evidence must exist on its source page")
        expected_complete = all(a.status == "found" for a in self.expected.values()) and all(
            source.parse_status == "parsed" for source in self.sources
        )
        if self.complete != expected_complete:
            raise ValueError("Expected completeness must agree with findings and coverage")
        return self


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    description: str
    packets: list[Packet]

    @model_validator(mode="after")
    def unique_packets(self):
        ids = [packet.id for packet in self.packets]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("Packet IDs must be unique and dataset cannot be empty")
        return self


def load_dataset(path: Path = DEFAULT_DATASET) -> Dataset:
    return Dataset.model_validate(json.loads(path.read_text()))
