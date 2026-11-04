"""Real API/storage with the production Gemini adapter and mocked provider HTTP."""
import json

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_extraction_provenance import DATA, intake

from app.config import settings
from app.extraction import selection
from app.extraction.llm import GeminiSettings, LLMExtractor
from app.models.extraction import (
    ExtractionArtifactRecord,
    ExtractionRunDocumentRecord,
    ExtractionRunRecord,
)


def enable(monkeypatch, handler):
    monkeypatch.setattr(settings, "gemini_enabled", True)
    monkeypatch.setattr(selection, "GeminiSettings", lambda: GeminiSettings(
        api_key="private-test-key", model="test-model", _env_file=None,
    ))
    monkeypatch.setattr(selection, "LLMExtractor", lambda config: LLMExtractor(
        config, transport=httpx.MockTransport(handler),
    ))


def test_method_discovery_and_server_enforcement(client, monkeypatch):
    methods = client.get("/api/extraction-methods").json()
    assert methods[0] == {"extractor": "rules", "available": True, "reason": None}
    assert methods[1]["available"] is False
    referral = client.post("/api/referrals", json=DATA).json()
    base = f"/api/referrals/{referral['id']}/extractions"
    assert client.post(base, json={"extractor": "gemini"}).status_code == 503
    for body in ({"extractor": "unknown"}, {"extractor": "rules", "model": "arbitrary"}):
        assert client.post(base, json=body).status_code == 422

    monkeypatch.setattr(settings, "gemini_enabled", True)
    def invalid():
        raise ValidationError.from_exception_data("secret-settings", [])
    monkeypatch.setattr(selection, "GeminiSettings", invalid)
    assert client.get("/api/extraction-methods").json()[1] == {
        "extractor": "gemini", "available": False,
        "reason": "Gemini extraction is not configured on this server",
    }
    response = client.post(base, json={"extractor": "gemini"})
    assert response.status_code == 503
    assert "secret" not in response.text


def test_gemini_api_releases_connection_and_captures_fixed_sources(
    client, pdf_factory, db_engine, monkeypatch,
):
    _, base, document = intake(client, pdf_factory)
    claims = {field: [] for field in DATA}
    claims["patient_name"] = [{
        "source_value": "Avery Morgan", "proposed_value": "Avery Morgan",
        "evidence": [{"document_id": document["id"], "page_number": 1,
                      "quote": "Patient: Avery Morgan"}],
    }]
    # An unsupported value must remain invalid through this public path too.
    claims["referral_reason"] = [{
        "source_value": "Invented reason", "proposed_value": "Invented reason",
        "evidence": [{"document_id": document["id"], "page_number": 1,
                      "quote": "Patient: Avery Morgan"}],
    }]
    calls = []
    def handler(request):
        assert db_engine.pool.checkedout() == 0
        calls.append(request)
        response = client.post(base + "/documents", files={
            "file": ("later.pdf", pdf_factory(pages=("DOB: 1974-03-12",))),
        })
        assert response.status_code == 201
        return httpx.Response(200, json={
            "candidates": [{"finishReason": "STOP", "content": {
                "parts": [{"text": json.dumps(claims)}],
            }}], "modelVersion": "test-revision",
        })
    enable(monkeypatch, handler)
    assert client.get("/api/extraction-methods").json()[1]["available"] is True
    response = client.post(base + "/extractions", json={"extractor": "gemini"})
    assert response.status_code == 201
    saved = response.json()
    assert len(calls) == 1
    assert saved["source_document_ids"] == [document["id"]]
    assert len(client.get(base + "/documents").json()) == 2
    assert saved["fields"]["patient_name"]["value"] == "Avery Morgan"
    assert saved["fields"]["referral_reason"]["value"] is None
    assert saved["provenance"]["provider"] == "gemini"
    assert saved["provenance"]["candidates_rejected"] == 1
    client.patch(base, json={"patient_name": "Human correction"})
    assert client.get(f"{base}/extractions/{saved['id']}").json() == saved
    assert "private-test-key" not in response.text
    with Session(db_engine) as session:
        assert session.scalar(select(func.count()).select_from(ExtractionArtifactRecord)) == 1
    # Explicit rules and the legacy empty-body request remain credential independent.
    assert client.post(base + "/extractions", json={"extractor": "rules"}).status_code == 201
    assert client.post(base + "/extractions").json()["extractor_version"] == "rules/1"


@pytest.mark.parametrize("failure,status", [
    ("timeout", 504), ("transport", 502), ("http", 502),
    ("blocked", 502), ("malformed", 502), ("oversized", 422),
])
def test_failed_gemini_keeps_previous_run_and_saves_nothing(
    client, pdf_factory, db_engine, monkeypatch, failure, status,
):
    referral, base, _ = intake(client, pdf_factory)
    previous = client.post(base + "/extractions").json()
    calls = []
    def handler(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("private provider information")
        if failure == "transport":
            raise httpx.ConnectError("private provider information")
        if failure == "http":
            return httpx.Response(429, text="private provider information")
        if failure == "blocked":
            return httpx.Response(200, json={"candidates": []})
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP", "content": {"parts": [{"text": "not json"}]},
        }]})
    enable(monkeypatch, handler)
    if failure == "oversized":
        monkeypatch.setattr(selection, "GeminiSettings", lambda: GeminiSettings(
            api_key="private-test-key", model="test-model", max_input_chars=1, _env_file=None,
        ))
    response = client.post(base + "/extractions", json={"extractor": "gemini"})
    assert response.status_code == status
    assert "private" not in response.text
    assert len(calls) == (0 if failure == "oversized" else 1)
    history = client.get(base + "/extractions").json()
    assert [run["id"] for run in history] == [previous["id"]]
    assert client.get(f"{base}/extractions/{previous['id']}").json() == previous
    assert client.get(base).json() == referral
    with Session(db_engine) as session:
        for model in (ExtractionRunRecord, ExtractionArtifactRecord, ExtractionRunDocumentRecord):
            assert session.scalar(select(func.count()).select_from(model)) == 1
