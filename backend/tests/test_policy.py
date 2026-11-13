"""Real configuration/API/database checks; no external provider requests."""
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

from app.config import settings
from app.extraction.assessment import assess_sources
from app.extraction.policy import BASELINE_POLICY, load_policy
from app.extraction.rule_based import RuleBasedExtractor
from app.main import app
from app.schemas.extraction import ReferralPolicy, SourceDocument, SourcePage

DATA = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside", "requested_specialty": "cardiology",
    "referral_reason": "Palpitations",
}


AUDIT = {"reviewer": "Test coordinator", "reason": "Confirmed source",
         "expected_values_version": 0}


def policy_data(**changes):
    return {**BASELINE_POLICY.model_dump(mode="json"), **changes}


@pytest.mark.parametrize("changes", [
    {"required_fields": []}, {"required_fields": ["patient_name", "patient_name"]},
    {"required_fields": ["ecg_report"]}, {"unexpected": True},
    {"version": ""}, {"id": "bad/id"}, {"name": " "}, {"version": 2},
])
def test_policy_rejects_invalid_configuration(changes):
    with pytest.raises(ValidationError):
        ReferralPolicy.model_validate_json(json.dumps(policy_data(**changes)))


def test_policy_is_immutable():
    with pytest.raises(ValidationError):
        BASELINE_POLICY.version = "changed"
    assert isinstance(BASELINE_POLICY.required_fields, tuple)


def test_startup_rejects_invalid_or_missing_policy(tmp_path, monkeypatch):
    path = tmp_path / "policy.json"
    monkeypatch.setattr(settings, "referral_policy_path", path)
    for content in (None, "{", json.dumps(policy_data(required_fields=[]))):
        if content is not None:
            path.write_text(content)
        with pytest.raises(ValueError, match="Invalid referral policy configuration"):
            with TestClient(app):
                pytest.fail("Invalid configuration must prevent startup")


def test_config_changes_new_runs_but_not_saved_findings_or_historical_policy(
    db_engine, document_storage, pdf_factory, tmp_path, monkeypatch,
):
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy_data()))
    monkeypatch.setattr(settings, "referral_policy_path", path)
    with TestClient(app) as client:
        referral = client.post("/api/referrals", json=DATA).json()
        base = f"/api/referrals/{referral['id']}"
        assert client.post(base + "/documents", files={"file": (
            "packet.pdf", pdf_factory(["Patient: Avery Morgan"]),
        )}).status_code == 201
        old = client.post(base + "/extractions").json()
        assert old["complete"] is False
        assert old["checklist_version"] == "five-required-fields/2"
        # A file edit does not change the startup-captured policy of a running server.
        path.write_text(json.dumps(policy_data(version="3", required_fields=["patient_name"])))
        assert client.post(base + "/extractions").json()["checklist_version"] == old[
            "checklist_version"
        ]
    with TestClient(app) as client:
        response = client.post(base + "/extractions")
        assert response.status_code == 201
        new = response.json()
        assert new["complete"] is True
        assert new["fields"] == old["fields"]
        assert new["findings"] == old["findings"]
        assert new["policy_assessment"]["requirements"] == [
            {"field": "patient_name", "satisfied": True, "finding": "found"},
        ]
        assert client.get(f"{base}/extractions/{old['id']}").json() == old
        assert client.get(f"{base}/extractions/{new['id']}").json() == new
        # Saving coordinator values cannot rewrite either source assessment.
        assert client.patch(
            base, json={**AUDIT, "patient_name": "Saved correction"},
        ).status_code == 200
        assert client.get(f"{base}/extractions/{old['id']}").json() == old
        assert client.get(f"{base}/extractions/{new['id']}").json() == new
        # Real legacy JSON remains readable, without inventing a current policy definition.
        with db_engine.begin() as connection:
            connection.execute(text(
                "UPDATE extraction_runs SET result_json = result_json - 'policy_assessment' "
                "WHERE id = :id"
            ), {"id": old["id"]})
        legacy = client.get(f"{base}/extractions/{old['id']}").json()
        assert legacy["policy_assessment"] is None
        assert legacy["checklist_version"] == old["checklist_version"]
        assert legacy["complete"] is False


def test_optional_invalid_candidate_still_checked_and_partial_coverage_blocks():
    policy = BASELINE_POLICY.model_copy(update={"required_fields": ("patient_name",)})
    source = SourceDocument(document_id=uuid4(), parse_status="parsed", pages=[
        SourcePage(page_number=1, text="Patient: Avery Morgan\nDOB: not-a-date"),
    ])
    result = assess_sources(RuleBasedExtractor(), [source], policy)
    assert result.complete
    assert next(f for f in result.findings if f.field == "date_of_birth").status == "invalid"
    assert result.fields["date_of_birth"].candidates[0].issue
    source.parse_status = "partial"
    source.pages.append(SourcePage(page_number=2, text=""))
    assert not assess_sources(RuleBasedExtractor(), [source], policy).complete
    assert not assess_sources(RuleBasedExtractor(), [], policy).complete


def test_packaged_policy_matches_pinned_baseline():
    from app.extraction.policy import DEFAULT_POLICY_PATH
    assert load_policy(DEFAULT_POLICY_PATH) == BASELINE_POLICY


def test_evaluation_ignores_application_policy_configuration(tmp_path, monkeypatch):
    from app.evaluation.__main__ import evaluate
    from app.evaluation.dataset import DEFAULT_DATASET

    before = evaluate(DEFAULT_DATASET)
    # Even an invalid app path must not affect the independent offline evaluator.
    monkeypatch.setattr(settings, "referral_policy_path", tmp_path / "missing.json")
    after = evaluate(DEFAULT_DATASET)
    assert after["checklist_version"] == "five-required-fields/2"
    assert before["overall"] == after["overall"]
