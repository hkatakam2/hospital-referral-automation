from dataclasses import dataclass
from pathlib import Path

import pypdf
from pypdf import PdfReader


class DocumentInputError(Exception):
    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ParsedDocument:
    pages: list[ParsedPage]
    parser_version: str


class PdfReaderAdapter:
    def __init__(self, max_pages: int, max_text_chars: int):
        self.max_pages = max_pages
        self.max_text_chars = max_text_chars

    def read(self, path: Path) -> ParsedDocument:
        try:
            with path.open("rb") as source:
                if source.read(5) != b"%PDF-":
                    raise DocumentInputError("Only PDF documents are supported", 415)
                source.seek(0)
                reader = PdfReader(source, strict=True)
                if reader.is_encrypted:
                    raise DocumentInputError("Encrypted PDFs are unsupported")
                if not reader.pages:
                    raise DocumentInputError("PDF has no pages")
                if len(reader.pages) > self.max_pages:
                    raise DocumentInputError("PDF exceeds the configured page limit", 413)
                pages = []
                text_chars = 0
                for number, page in enumerate(reader.pages, start=1):
                    text = page.extract_text() or ""
                    text_chars += len(text)
                    if text_chars > self.max_text_chars:
                        raise DocumentInputError("PDF exceeds the extracted text limit", 413)
                    pages.append(ParsedPage(number, text))
                if not any(page.text.strip() for page in pages):
                    raise DocumentInputError(
                        "No usable text found; image-only and blank PDFs are unsupported",
                    )
                return ParsedDocument(pages, f"pypdf/{pypdf.__version__}")
        except DocumentInputError:
            raise
        except OSError:
            # Storage errors are server failures, not invalid user documents.
            raise
        except Exception as error:
            # Malformed PDFs can raise several parser/decoder exception types.
            raise DocumentInputError("PDF is corrupt or cannot be parsed") from error
