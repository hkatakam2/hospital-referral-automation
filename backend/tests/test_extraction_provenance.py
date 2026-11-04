import json
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.extraction.base import ExtractionOutput
from app.extraction.llm import GeminiSettings, LLMExtractor
from app.extraction.rule_based import RuleBasedExtractor
from app.models.extraction import ExtractionArtifactRecord, ExtractionRunRecord
from app.schemas.extraction import Candidate, FieldResult
from app.services.referral_extraction import ReferralExtractionService

DATA = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside", "requested_specialty": "cardiology",
    "referral_reason": "Palpitations",
}


def intake(client, pdf_factory):
    referral = client.post("/api/referrals", json=DATA).json()
    base = f"/api/referrals/{referral['id']}"
    document = client.post(base + "/documents", files={
        "file": ("synthetic.pdf", pdf_factory(pages=("Patient: Avery Morgan",))),
    }).json()
    return referral, base, document


@pytest.mark.parametrize("unsupported", [False, True])
def test_gemini_claims_response_and_provenance_survive_without_public_raw_output(
    client, pdf_factory, db_engine, unsupported,
):
    referral, base, document = intake(client, pdf_factory)
    claims = {name: [] for name in DATA}
    claims["patient_name"] = [{
        "source_value": "Invented Person" if unsupported else "Avery Morgan",
        "proposed_value": "Invented Person" if unsupported else "Avery Morgan",
        "evidence": [{"document_id": document["id"], "page_number": 1,
                      "quote": "Patient: Avery Morgan"}],
    }]
    raw = {
        "candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(claims)}],
        }}],
        "modelVersion": "test-revision",
        "usageMetadata": {"promptTokenCount": 12},
        "internal_test_marker": "backend-only-response",
    }
    extractor = LLMExtractor(
        GeminiSettings(api_key="test-credential", model="test-model", _env_file=None),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=raw)),
    )
    result = ReferralExtractionService(sessionmaker(db_engine), extractor).run(
        referral["id"],
    )
    db_engine.dispose()
    saved = client.get(f"{base}/extractions/{result.id}").json()
    assert saved == result.model_dump(mode="json")
    assert saved["provenance"]["model_version"] == "test-revision"
    assert saved["provenance"]["prompt_version"] == "referral-claims/1"
    assert saved["provenance"]["candidates_checked"] == 1
    assert saved["provenance"]["candidates_rejected"] == int(unsupported)
    assert saved["fields"]["patient_name"]["value"] == (
        None if unsupported else "Avery Morgan"
    )
    assert saved["findings"][0]["status"] == ("invalid" if unsupported else "found")
    for payload in (saved, client.get(base + "/extractions").json()):
        serialized = json.dumps(payload)
        for private in ("raw_response", "original_claims", "backend-only-response",
                        "test-credential", "usageMetadata"):
            assert private not in serialized
    with Session(db_engine) as session:
        artifact = session.get(ExtractionArtifactRecord, result.id).artifact_json
        assert artifact["schema_version"] == 1
        assert artifact["raw_response"] == raw
        assert artifact["original_claims"] == claims
        assert artifact["execution"]["usage"] == {"promptTokenCount": 12}
        assert "test-credential" not in json.dumps(artifact)
        assert "raw_response" not in artifact["execution"]
        before = json.loads(json.dumps(artifact))
    client.patch(base, json={"patient_name": "Human correction"})
    client.post(base + "/extractions")
    assert client.get(f"{base}/extractions/{result.id}").json() == saved
    with Session(db_engine) as session:
        assert session.get(ExtractionArtifactRecord, result.id).artifact_json == before


def test_preassessment_output_retains_rejected_claims(client, pdf_factory, db_engine):
    referral, base, _ = intake(client, pdf_factory)

    class FaultyExtractor:
        version = "faulty/test"

        def extract(self, sources):
            return ExtractionOutput(fields={"patient_name": FieldResult(candidates=[
                Candidate(raw_value="Invented", value="Invented"),
            ])})

    result = ReferralExtractionService(sessionmaker(db_engine), FaultyExtractor()).run(
        referral["id"],
    )
    saved = client.get(f"{base}/extractions/{result.id}").json()
    assert saved["fields"]["patient_name"]["candidates"][0]["issue"] == "Missing evidence"
    with Session(db_engine) as session:
        artifact = session.get(ExtractionArtifactRecord, result.id).artifact_json
        original = artifact["extractor_output"]["fields"]["patient_name"]["candidates"][0]
        assert original["value"] == "Invented"
        assert original["issue"] is None
        assert artifact["raw_response"] is None


def test_artifact_migration_preserves_legacy_snapshots(client, pdf_factory, db_engine):
    _, base, _ = intake(client, pdf_factory)
    saved = client.post(base + "/extractions").json()
    legacy = {key: value for key, value in saved.items() if key != "provenance"}
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    with Session(db_engine) as session:
        session.get(ExtractionRunRecord, UUID(saved["id"])).result_json = legacy
        session.commit()
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0003")
        command.upgrade(config, "head")
        command.check(config)
    assert client.get(f"{base}/extractions/{saved['id']}").json() == {
        **legacy, "provenance": None,
    }
    with Session(db_engine) as session:
        assert session.get(ExtractionArtifactRecord, UUID(saved["id"])) is None
        assert session.scalar(select(ExtractionRunRecord)).result_json == legacy
        new = ReferralExtractionService(sessionmaker(db_engine), RuleBasedExtractor()).run(
            saved["referral_id"],
        )
        assert session.get(ExtractionArtifactRecord, new.id) is not None
