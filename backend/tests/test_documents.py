import hashlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.main import app
from app.models.document import DocumentPageRecord, DocumentRecord
from app.repositories.documents import DocumentRepository
from app.storage.local import LocalDocumentStorage

DATA = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside Primary Care", "requested_specialty": "cardiology",
    "referral_reason": "Recurrent palpitations",
}


@pytest.fixture
def documents_url(client):
    referral = client.post("/api/referrals", json=DATA).json()
    return f"/api/referrals/{referral['id']}/documents"


def assert_no_document_artifacts(client, url, directory, engine):
    assert client.get(url).json() == []
    assert not directory.exists() or list(directory.iterdir()) == []
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(DocumentRecord)) == 0
        assert session.scalar(select(func.count()).select_from(DocumentPageRecord)) == 0


def test_upload_list_retrieve_and_persist_original(
    client, documents_url, pdf_factory, document_storage, db_engine,
):
    assert client.get(documents_url).json() == []
    content = pdf_factory()
    response = client.post(
        documents_url, files={"file": ("referral.pdf", content, "application/pdf")},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["original_filename"] == "referral.pdf"
    assert document["sha256"] == hashlib.sha256(content).hexdigest()
    assert document["size_bytes"] == len(content)
    assert document["page_count"] == 2
    assert document["parse_status"] == "parsed"
    assert document["parser_version"].startswith("pypdf/")
    assert [page["page_number"] for page in document["pages"]] == [1, 2]
    assert [page["text"].strip() for page in document["pages"]] == [
        "Patient: Avery Morgan", "ECG: Attached",
    ]
    assert all(page["text_status"] == "extracted" for page in document["pages"])
    assert "storage_key" not in document
    assert list(document_storage.iterdir()) == [document_storage / f"{document['id']}.pdf"]
    assert (document_storage / f"{document['id']}.pdf").read_bytes() == content
    # Default permissions of mkstemp remain private after promotion.
    assert (document_storage / f"{document['id']}.pdf").stat().st_mode & 0o777 == 0o600
    summary = {key: value for key, value in document.items() if key != "pages"}
    assert client.get(documents_url).json() == [summary]
    db_engine.dispose()
    with TestClient(app) as reopened:
        assert reopened.get(f"{documents_url}/{document['id']}").json() == document
        assert reopened.get(documents_url).json() == [summary]


def test_mixed_pages_are_partial_without_guessing_why_text_is_absent(
    client, documents_url, pdf_factory,
):
    response = client.post(documents_url, files={
        "file": ("mixed.pdf", pdf_factory(
            ["Patient: Avery Morgan", None, "ECG: Attached"], images=True,
        )),
    })
    assert response.status_code == 201
    document = response.json()
    assert document["parse_status"] == "partial"
    assert document["page_count"] == 3
    assert document["pages"][1] == {"page_number": 2, "text": "", "text_status": "no_text"}
    assert document["pages"][2]["page_number"] == 3


def test_filename_and_mime_do_not_control_storage_or_content_validation(
    client, documents_url, pdf_factory, document_storage,
):
    response = client.post(documents_url, files={
        "file": ("../../unsafe/referral.txt", pdf_factory(), "text/plain"),
    })
    assert response.status_code == 201
    document = response.json()
    assert document["original_filename"] == "referral.txt"
    assert [path.name for path in document_storage.iterdir()] == [f"{document['id']}.pdf"]


def test_repeat_uploads_are_independent_and_list_order_is_stable(
    client, documents_url, pdf_factory, db_engine,
):
    documents = [client.post(documents_url, files={"file": ("a.pdf", pdf_factory())}).json()
                 for _ in range(2)]
    assert documents[0]["sha256"] == documents[1]["sha256"]
    assert documents[0]["id"] != documents[1]["id"]
    assert [item["id"] for item in client.get(documents_url).json()] == [
        item["id"] for item in documents
    ]
    with db_engine.begin() as connection:
        connection.execute(text("UPDATE documents SET created_at = '2026-01-01T00:00:00Z'"))
    assert [item["id"] for item in client.get(documents_url).json()] == sorted(
        item["id"] for item in documents
    )


@pytest.mark.parametrize("kind,status", [
    ("empty", 422), ("fake", 415), ("corrupt", 422), ("blank", 422),
    ("image_only", 422), ("encrypted", 422),
    ("oversized", 413), ("pages", 413), ("text", 413),
])
def test_rejected_uploads_leave_no_rows_or_files(
    client, documents_url, pdf_factory, document_storage, db_engine, monkeypatch, kind, status,
):
    content = pdf_factory()
    if kind == "empty":
        content = b""
    elif kind == "fake":
        content = b"this is a text file pretending to be PDF"
    elif kind == "corrupt":
        content = b"%PDF-1.7\ninvalid contents"
    elif kind == "blank":
        content = pdf_factory([None])
    elif kind == "image_only":
        content = pdf_factory([None], images=True)
    elif kind == "encrypted":
        content = pdf_factory(encrypted=True)
    elif kind == "oversized":
        monkeypatch.setattr(settings, "document_max_bytes", len(content) - 1)
    elif kind == "pages":
        monkeypatch.setattr(settings, "document_max_pages", 1)
    elif kind == "text":
        monkeypatch.setattr(settings, "document_max_text_chars", 5)
    response = client.post(
        documents_url, files={"file": ("referral.pdf", content, "application/pdf")},
    )
    assert response.status_code == status
    assert isinstance(response.json()["detail"], str)
    assert_no_document_artifacts(client, documents_url, document_storage, db_engine)


def test_missing_or_malformed_identifiers_and_missing_file(
    client, documents_url, pdf_factory, document_storage,
):
    assert client.post(documents_url).status_code == 422
    unknown_url = f"/api/referrals/{uuid4()}/documents"
    assert client.get(unknown_url).status_code == 404
    assert client.post(unknown_url, files={"file": ("a.pdf", pdf_factory())}).status_code == 404
    assert client.get(f"{documents_url}/{uuid4()}").status_code == 404
    assert client.get(f"{documents_url}/not-a-uuid").status_code == 422
    assert client.get("/api/referrals/not-a-uuid/documents").status_code == 422
    assert client.post("/api/referrals/not-a-uuid/documents", files={
        "file": ("a.pdf", pdf_factory()),
    }).status_code == 422
    assert not document_storage.exists()


def test_document_cannot_be_retrieved_through_another_referral(client, documents_url, pdf_factory):
    document = client.post(documents_url, files={"file": ("a.pdf", pdf_factory())}).json()
    other_referral = client.post(
        "/api/referrals", json={**DATA, "patient_name": "Jordan Ellis"},
    ).json()
    other_url = f"/api/referrals/{other_referral['id']}/documents"
    assert client.get(other_url).json() == []
    assert client.get(f"{other_url}/{document['id']}").status_code == 404
    assert client.get(f"/api/referrals/{uuid4()}/documents/{document['id']}").status_code == 404


@pytest.mark.parametrize("phase", ["promote", "insert", "commit"])
def test_failed_writes_roll_back_rows_and_clean_files(
    client, documents_url, pdf_factory, document_storage, db_engine, monkeypatch, phase,
):
    def fail(*args, **kwargs):
        raise OSError("Simulated storage/transaction failure")

    with monkeypatch.context() as patch:
        if phase == "promote":
            patch.setattr(LocalDocumentStorage, "promote", fail)
        elif phase == "commit":
            patch.setattr(Session, "commit", fail)
        else:
            original = DocumentRepository.add

            def invalid_page(self, document, pages):
                pages[-1].page_number = 0  # Exercise a real database constraint failure.
                original(self, document, pages)

            patch.setattr(DocumentRepository, "add", invalid_page)
        with pytest.raises((OSError, IntegrityError)):
            client.post(documents_url, files={"file": ("a.pdf", pdf_factory())})
    assert_no_document_artifacts(client, documents_url, document_storage, db_engine)
    # A later upload works after the failed request/session.
    assert client.post(documents_url, files={"file": ("a.pdf", pdf_factory())}).status_code == 201
