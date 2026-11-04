from collections.abc import Sequence
from typing import Protocol

from app.schemas.extraction import FieldName, FieldResult, SourceDocument


class Extractor(Protocol):
    version: str

    def extract(self, sources: Sequence[SourceDocument]) -> dict[FieldName, FieldResult]: ...
