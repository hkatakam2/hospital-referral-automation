import os
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app import database
from app.config import settings
from app.main import app


@pytest.fixture(scope="session")
def postgres_engine():
    # Never migrate or clear the configured development database. Create an owned,
    # randomly named test database instead, on the same local PostgreSQL server.
    url = make_url(os.environ.get("TEST_DATABASE_URL", settings.database_url))
    name = "referral_test_" + uuid4().hex
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(url.set(database=name))
    try:
        config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def db_engine(postgres_engine, monkeypatch):
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE review_events, extraction_artifacts, extraction_run_documents, "
            "extraction_runs, "
            "document_pages, documents, referrals"
        ))
    monkeypatch.setattr(database, "engine", postgres_engine)
    monkeypatch.setattr(settings, "gemini_enabled", False)
    yield postgres_engine
    with postgres_engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE review_events, extraction_artifacts, extraction_run_documents, "
            "extraction_runs, "
            "document_pages, documents, referrals"
        ))


@pytest.fixture
def document_storage(tmp_path, monkeypatch):
    directory = tmp_path / "documents"
    monkeypatch.setattr(settings, "document_storage_dir", directory)
    return directory


@pytest.fixture
def client(db_engine, document_storage):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def pdf_factory():
    """Build fictional text, image, and blank PDFs without a renderer dependency."""
    def build(pages=("Patient: Avery Morgan", "ECG: Attached"), encrypted=False, images=False):
        writer = PdfWriter()
        font = writer._add_object(DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }))
        for text_value in pages:
            page = writer.add_blank_page(width=612, height=792)
            if text_value is not None:
                page[NameObject("/Resources")] = DictionaryObject({
                    NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
                })
                stream = DecodedStreamObject()
                escaped = text_value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii"))
                page[NameObject("/Contents")] = writer._add_object(stream)
            elif images:
                image = DecodedStreamObject()
                image.update({
                    NameObject("/Type"): NameObject("/XObject"),
                    NameObject("/Subtype"): NameObject("/Image"),
                    NameObject("/Width"): NumberObject(1),
                    NameObject("/Height"): NumberObject(1),
                    NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                    NameObject("/BitsPerComponent"): NumberObject(8),
                })
                image.set_data(b"\xff\x00\x00")
                page[NameObject("/Resources")] = DictionaryObject({
                    NameObject("/XObject"): DictionaryObject({
                        NameObject("/Im1"): writer._add_object(image),
                    }),
                })
                stream = DecodedStreamObject()
                stream.set_data(b"q 100 0 0 100 72 600 cm /Im1 Do Q")
                page[NameObject("/Contents")] = writer._add_object(stream)
        if encrypted:
            writer.encrypt("synthetic-test-password")
        target = BytesIO()
        writer.write(target)
        return target.getvalue()
    return build
