from io import BytesIO

import pytest

from app.document_processing.pdf import DocumentInputError, PdfReaderAdapter
from app.storage.local import LocalDocumentStorage


def test_reader_preserves_page_numbers_and_flags_no_text(tmp_path, pdf_factory):
    path = tmp_path / "packet.pdf"
    path.write_bytes(pdf_factory(["Patient: Avery Morgan", None, "ECG: Attached"]))
    result = PdfReaderAdapter(100, 2_000_000).read(path)
    assert [(page.page_number, page.text.strip()) for page in result.pages] == [
        (1, "Patient: Avery Morgan"), (2, ""), (3, "ECG: Attached"),
    ]
    assert result.parser_version.startswith("pypdf/")


@pytest.mark.parametrize("kind,expected_status", [
    ("non_pdf", 415), ("corrupt", 422), ("encrypted", 422),
    ("blank", 422), ("image_only", 422), ("no_pages", 422),
    ("page_limit", 413), ("text_limit", 413),
])
def test_reader_rejects_unsupported_documents(tmp_path, pdf_factory, kind, expected_status):
    content = {
        "non_pdf": b"Patient: Avery Morgan",
        "corrupt": b"%PDF-1.7\nthis is not a valid PDF",
        "encrypted": pdf_factory(encrypted=True),
        "blank": pdf_factory([None]),
        "image_only": pdf_factory([None], images=True),
        "no_pages": pdf_factory([]),
        "page_limit": pdf_factory(),
        "text_limit": pdf_factory(),
    }[kind]
    path = tmp_path / "packet.pdf"
    path.write_bytes(content)
    reader = PdfReaderAdapter(1 if kind == "page_limit" else 100,
                              5 if kind == "text_limit" else 2_000_000)
    with pytest.raises(DocumentInputError) as failure:
        reader.read(path)
    assert failure.value.status_code == expected_status


def test_reader_does_not_report_storage_failure_as_invalid_pdf(tmp_path):
    with pytest.raises(FileNotFoundError):
        PdfReaderAdapter(100, 2_000_000).read(tmp_path / "missing.pdf")


@pytest.mark.parametrize("content,limit,status", [(b"", 10, 422), (b"12345", 4, 413)])
def test_staging_cleans_rejected_uploads(tmp_path, content, limit, status):
    storage = LocalDocumentStorage(tmp_path, limit)
    with pytest.raises(DocumentInputError) as failure:
        with storage.stage(BytesIO(content)):
            pytest.fail("Rejected content should not be staged")
    assert failure.value.status_code == status
    assert list(tmp_path.iterdir()) == []


def test_staging_accepts_exact_size_limit_and_cleans_after_consumer_failure(tmp_path):
    storage = LocalDocumentStorage(tmp_path, 4)
    with pytest.raises(RuntimeError, match="consumer failed"):
        with storage.stage(BytesIO(b"1234")) as staged:
            assert staged.size_bytes == 4
            assert staged.path.read_bytes() == b"1234"
            raise RuntimeError("consumer failed")
    assert list(tmp_path.iterdir()) == []
