import hashlib
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from app.document_processing.pdf import DocumentInputError


@dataclass(frozen=True)
class StagedFile:
    path: Path
    size_bytes: int
    sha256: str


class LocalDocumentStorage:
    def __init__(self, root: Path, max_bytes: int):
        self.root = root
        self.max_bytes = max_bytes

    @contextmanager
    def stage(self, source: BinaryIO) -> Iterator[StagedFile]:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, name = tempfile.mkstemp(prefix=".upload-", dir=self.root)
        path = Path(name)
        try:
            digest = hashlib.sha256()
            size = 0
            with os.fdopen(descriptor, "wb") as target:
                while chunk := source.read(64 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise DocumentInputError("Upload exceeds the configured size limit", 413)
                    digest.update(chunk)
                    target.write(chunk)
                if not size:
                    raise DocumentInputError("Uploaded file is empty")
            yield StagedFile(path, size, digest.hexdigest())
        finally:
            path.unlink(missing_ok=True)

    def promote(self, staged: StagedFile, document_id: UUID) -> str:
        key = f"{document_id}.pdf"
        staged.path.replace(self.root / key)
        return key

    def remove(self, key: str) -> None:
        (self.root / key).unlink(missing_ok=True)
