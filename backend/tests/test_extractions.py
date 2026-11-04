from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.extraction.rule_based import RuleBasedExtractor
from app.main import app
from app.models.extraction import ExtractionRunDocumentRecord, ExtractionRunRecord
from app.schemas.extraction import SourceDocument, SourcePage
from app.services.completeness import check_completeness
from app.services.referral_extraction import ReferralExtractionService

DATA = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside Primary Care", "requested_specialty": "cardiology",
    "referral_reason": "Recurrent palpitations",
}
FIXTURES = Path(__file__).parent / "fixtures" / "referrals"


def extract(text):
    source = SourceDocument(
        document_id=uuid4(), parse_status="parsed",
        pages=[SourcePage(page_number=1, text=text)],
    )
    fields = RuleBasedExtractor().extract([source])
    return source, fields, check_completeness(fields, [source])


@pytest.mark.parametrize("name,status,complete", [
    ("complete", "found", True),
    ("missing_information", "missing", False),
    ("conflicting_information", "conflicting", False),
])
def test_ground_truth(name, status, complete):
    source, fields, (findings, warnings, actual) = extract((FIXTURES / f"{name}.txt").read_text())
    field = "date_of_birth" if status == "conflicting" else "referring_organization"
    assert next(f.status for f in findings if f.field == field) == status
    assert actual is complete
    assert warnings == []
    if status != "found":
        assert fields[field].value is None
    for result in fields.values():
        for candidate in result.candidates:
            for evidence in candidate.evidence:
                assert evidence.document_id == source.document_id
                assert evidence.quote in source.pages[0].text


@pytest.mark.parametrize("value", ["tomorrow", "2025-02-30", "2999-01-01", ""])
def test_invalid_dates_remain_visible(value):
    _, fields, (findings, _, complete) = extract(f"DOB: {value}")
    assert fields["date_of_birth"].value is None
    assert fields["date_of_birth"].candidates[0].raw_value == value
    assert next(f.status for f in findings if f.field == "date_of_birth") == "invalid"
    assert not complete


def test_aliases_repeated_evidence_and_unknown_values():
    _, fields, _ = extract(
        "Patient Name: Avery Morgan\nDOB: 1974-03-12\nDOB: 1974-03-12\n"
        "Referring Clinic: Lakeside\nRequested Service: Cardiology consultation\n"
        "Referral Reason: Palpitations\nUnrecognized: invented"
    )
    assert fields["requested_specialty"].value == "cardiology"
    assert len(fields["date_of_birth"].candidates) == 1
    assert len(fields["date_of_birth"].candidates[0].evidence) == 2
    _, fields, (findings, _, _) = extract("Specialty: neurology")
    assert fields["requested_specialty"].value is None
    assert next(f.status for f in findings if f.field == "requested_specialty") == "invalid"


def attach(client, base, pdf_factory, pages):
    response = client.post(
        base + "/documents", files={"file": ("synthetic.pdf", pdf_factory(pages=pages))},
    )
    assert response.status_code == 201
    return response.json()


def test_api_snapshot_conflicts_scope_and_reopened_connections(client, pdf_factory, db_engine):
    referral = client.post("/api/referrals", json=DATA).json()
    base = f"/api/referrals/{referral['id']}"
    first = attach(client, base, pdf_factory, ("Patient: Avery Morgan", "DOB: 1974-03-12"))
    response = client.post(base + "/extractions")
    assert response.status_code == 201
    original = response.json()
    assert original["fields"]["referring_organization"]["value"] is None
    second = attach(client, base, pdf_factory, ("DOB: 1974-03-21",))
    current = client.post(base + "/extractions").json()
    assert current["id"] != original["id"]
    assert current["source_document_ids"] == [first["id"], second["id"]]
    dob = current["fields"]["date_of_birth"]
    assert dob["value"] is None
    assert len(dob["candidates"]) == 2
    assert dob["candidates"][0]["evidence"][0]["page_number"] == 2
    assert client.get(base).json() == referral
    db_engine.dispose()
    with TestClient(app) as reopened:
        assert reopened.get(base + f"/extractions/{original['id']}").json() == original
    other = client.post("/api/referrals", json=DATA).json()["id"]
    assert client.get(f"/api/referrals/{other}/extractions/{original['id']}").status_code == 404
    assert client.get(base + f"/extractions/{uuid4()}").status_code == 404


def test_partial_source_blocks_complete(client, pdf_factory):
    referral = client.post("/api/referrals", json=DATA).json()
    base = f"/api/referrals/{referral['id']}"
    attach(client, base, pdf_factory, (
        "Patient: Avery Morgan", "DOB: 1974-03-12", "Referring Clinic: Lakeside",
        "Specialty: cardiology", "Reason: Palpitations", None,
    ))
    result = client.post(base + "/extractions").json()
    assert all(f["status"] == "found" for f in result["findings"])
    assert result["warnings"]
    assert result["complete"] is False


def test_errors(client):
    assert client.post(f"/api/referrals/{uuid4()}/extractions").status_code == 404
    assert client.post("/api/referrals/not-a-uuid/extractions").status_code == 422
    referral = client.post("/api/referrals", json=DATA).json()
    assert client.post(f"/api/referrals/{referral['id']}/extractions").status_code == 422


def test_commit_failure_rolls_back_run_and_links(client, pdf_factory, db_engine, monkeypatch):
    referral = client.post("/api/referrals", json=DATA).json()
    attach(client, f"/api/referrals/{referral['id']}", pdf_factory, ("Patient: Avery Morgan",))
    with Session(db_engine) as session:
        service = ReferralExtractionService(session, RuleBasedExtractor())
        def fail():
            raise RuntimeError("commit failed")
        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", fail)
            with pytest.raises(RuntimeError, match="commit failed"):
                service.run(referral["id"])
        assert session.scalar(select(func.count()).select_from(ExtractionRunRecord)) == 0
        assert session.scalar(select(func.count()).select_from(ExtractionRunDocumentRecord)) == 0
        assert service.run(referral["id"]).id
