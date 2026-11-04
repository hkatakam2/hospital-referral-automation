from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, Field

from app.schemas.extraction import FieldResult, SourceDocument


class ExecutionMetadata(BaseModel):
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    request_ms: float | None = None
    request_config: dict[str, int | float] = Field(default_factory=dict)
    source_checks: dict[str, int] = Field(default_factory=dict)
    usage: dict[str, int] = Field(default_factory=dict)
    raw_response: dict | None = Field(default=None, exclude=True)


class ExtractionOutput(BaseModel):
    fields: dict[str, FieldResult]
    execution: ExecutionMetadata = Field(default_factory=ExecutionMetadata)
    original_claims: dict | None = Field(default=None, exclude=True)


class Extractor(Protocol):
    """Produce source candidates; assessment owns selected values and findings."""

    version: str

    def extract(self, sources: Sequence[SourceDocument]) -> ExtractionOutput: ...
