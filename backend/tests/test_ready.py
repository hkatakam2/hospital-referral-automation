from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.document_processing.pdf import PdfReaderAdapter
from app.schemas.workflow import ReadyCommand
from app.services.referral_workflow import ReferralWorkflowService

DATA = {
    "patient_name": "Avery Morgan",
    "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside",
    "requested_specialty": "cardiology",
    "referral_reason": "Palpitations",
}
PAGES = (
    "Patient: Avery Morgan",
    "DOB: 1974-03-12",
    "Referring Clinic: Lakeside",
    "Specialty: cardiology",
    "Reason: Palpitations",
)
ACTION = {
    "reviewer": "Demo reviewer",
    "reason": "Reviewed source and saved values",
    "expected_workflow_version": 0,
}


def packet(client, pdf_factory, pages=PAGES):
    referral = client.post("/api/referrals", json=DATA).json()
    base = f"/api/referrals/{referral['id']}"
    upload = client.post(base + "/documents", files={"file": ("source.pdf", pdf_factory(pages))})
    assert upload.status_code == 201
    response = client.post(base + "/extractions")
    assert response.status_code == 201
    return base, response.json()


def ready(run, **changes):
    return {**ACTION, "extraction_id": run["id"], "expected_values_version": 0, **changes}


def test_ready_reopen_and_retained_decision(client, pdf_factory, db_engine, document_storage):
    base, run = packet(client, pdf_factory)
    corrected = client.patch(
        base,
        json={
            "patient_name": "Reviewed name",
            "reviewer": "Coordinator",
            "reason": "Reviewed spelling",
            "expected_values_version": 0,
        },
    )
    assert corrected.status_code == 200
    response = client.post(base + "/mark-ready", json=ready(run, expected_values_version=1))
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["workflow_version"] == 1
    event = client.get(base + "/review-events").json()[0]
    assert event["action"] == "mark_ready"
    assert event["extraction_id"] == run["id"]
    assert event["reviewed_values_version"] == 1
    files_before = sorted(document_storage.rglob("*"))
    assert (
        client.post(
            base + "/documents",
            files={
                "file": ("later.pdf", pdf_factory(PAGES)),
            },
        ).status_code
        == 409
    )
    assert sorted(document_storage.rglob("*")) == files_before
    assert (
        client.patch(
            base,
            json={
                "patient_name": "Blocked",
                "reviewer": "Coordinator",
                "reason": "Edit",
                "expected_values_version": 1,
            },
        ).status_code
        == 409
    )
    assert (
        client.post(
            base + "/information-requests",
            json={
                **ACTION,
                "expected_workflow_version": 1,
                "requested_information": "More source",
            },
        ).status_code
        == 409
    )
    db_engine.dispose()
    assert client.get(base).json() == response.json()
    assert client.get(base + "/review-events").json() == [event]
    assert client.get(base + "/extractions/" + run["id"]).json() == run
    resumed = client.post(base + "/reopen-review", json={**ACTION, "expected_workflow_version": 1})
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "review_required"
    assert (
        client.post(
            base + "/documents",
            files={
                "file": ("later.pdf", pdf_factory(PAGES)),
            },
        ).status_code
        == 201
    )
    assert (
        client.patch(
            base,
            json={
                "patient_name": "After reopening",
                "reviewer": "Coordinator",
                "reason": "Edit",
                "expected_values_version": 1,
            },
        ).status_code
        == 200
    )
    assert client.get(base + "/review-events").json()[1] == event
    assert client.get(base + "/review-events").json()[0]["action"] == "reopen_review"


@pytest.mark.parametrize("pages", [PAGES[:-1], (*PAGES, "DOB: 1974-03-21"), (*PAGES, None)])
def test_incomplete_conflicting_or_partial_packet_cannot_be_ready(client, pdf_factory, pages):
    base, run = packet(client, pdf_factory, pages)
    assert not run["complete"]
    assert client.post(base + "/mark-ready", json=ready(run)).status_code == 409
    assert client.get(base + "/review-events").json() == []
    assert client.get(base).json()["status"] == "received"


def test_ready_requires_latest_current_scoped_run_and_saved_values(client, pdf_factory):
    base, first = packet(client, pdf_factory)
    _, foreign = packet(client, pdf_factory)
    for identifier in [foreign["id"], str(uuid4())]:
        assert (
            client.post(
                base + "/mark-ready", json=ready(first, extraction_id=identifier)
            ).status_code
            == 409
        )
    latest = client.post(base + "/extractions").json()
    assert client.post(base + "/mark-ready", json=ready(first)).status_code == 409
    assert (
        client.post(base + "/mark-ready", json=ready(latest, expected_values_version=1)).status_code
        == 409
    )
    assert (
        client.post(
            base + "/mark-ready", json=ready(latest, expected_workflow_version=1)
        ).status_code
        == 409
    )
    assert client.post(base + "/reopen-review", json=ACTION).status_code == 409
    client.post(base + "/documents", files={"file": ("later.pdf", pdf_factory(PAGES))})
    assert client.post(base + "/mark-ready", json=ready(latest)).status_code == 409
    assert client.get(base + "/review-events").json() == []


def test_missing_information_must_be_explicitly_resumed(client, pdf_factory):
    base, run = packet(client, pdf_factory)
    assert (
        client.post(
            base + "/information-requests",
            json={
                **ACTION,
                "requested_information": "Confirm documents",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(base + "/mark-ready", json=ready(run, expected_workflow_version=1)).status_code
        == 409
    )
    assert (
        client.post(
            base + "/resume-review", json={**ACTION, "expected_workflow_version": 1}
        ).status_code
        == 200
    )
    assert (
        client.post(base + "/mark-ready", json=ready(run, expected_workflow_version=2)).status_code
        == 200
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"reviewer": " "},
        {"reason": ""},
        {"expected_values_version": True},
        {"expected_values_version": -1},
        {"expected_values_version": "0"},
        {"extraction_id": None},
        {"reviewed_values_version": 0},
    ],
)
def test_invalid_ready_commands_do_not_write(client, pdf_factory, changes):
    base, run = packet(client, pdf_factory)
    assert client.post(base + "/mark-ready", json=ready(run, **changes)).status_code == 422
    assert client.get(base + "/review-events").json() == []


def test_ready_without_extraction_and_unknown_referral(client):
    referral = client.post("/api/referrals", json=DATA).json()
    payload = ready({"id": str(uuid4())})
    assert (
        client.post(f"/api/referrals/{referral['id']}/mark-ready", json=payload).status_code == 409
    )
    assert client.post(f"/api/referrals/{uuid4()}/mark-ready", json=payload).status_code == 404
    assert client.post(f"/api/referrals/{uuid4()}/reopen-review", json=ACTION).status_code == 404


def test_ready_commit_failure_rolls_back(client, pdf_factory, db_engine, monkeypatch):
    base, run = packet(client, pdf_factory)
    before = client.get(base).json()
    with Session(db_engine) as session:

        def fail():
            raise RuntimeError("simulated commit failure")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(RuntimeError):
            ReferralWorkflowService(session).apply(
                UUID(run["referral_id"]),
                "mark_ready",
                ReadyCommand(**ready(run)),
            )
    assert client.get(base).json() == before
    assert client.get(base + "/review-events").json() == []


def test_concurrent_ready_accepts_one_decision(client, pdf_factory, db_engine):
    base, run = packet(client, pdf_factory)

    def apply():
        with Session(db_engine) as session:
            try:
                ReferralWorkflowService(session).apply(
                    UUID(run["referral_id"]),
                    "mark_ready",
                    ReadyCommand(**ready(run)),
                )
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: apply(), range(2))) == [200, 409]
    assert len(client.get(base + "/review-events").json()) == 1


def test_upload_started_before_ready_rechecks_status_after_parsing(
    client, pdf_factory, monkeypatch
):
    base, run = packet(client, pdf_factory)
    parsing, release = Event(), Event()
    original = PdfReaderAdapter.read

    def paused_read(self, path):
        result = original(self, path)
        parsing.set()
        assert release.wait(10)
        return result

    monkeypatch.setattr(PdfReaderAdapter, "read", paused_read)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            client.post,
            base + "/documents",
            files={
                "file": ("racing.pdf", pdf_factory(PAGES)),
            },
        )
        try:
            assert parsing.wait(10)
            assert client.post(base + "/mark-ready", json=ready(run)).status_code == 200
        finally:
            release.set()
        assert future.result().status_code == 409
    assert len(client.get(base + "/documents").json()) == 1


def test_ready_migration_preserves_legacy_history_and_refuses_lossy_downgrade(
    client, pdf_factory, db_engine
):
    base, run = packet(client, pdf_factory)
    client.post(base + "/information-requests", json={**ACTION, "requested_information": "Confirm"})
    client.post(base + "/resume-review", json={**ACTION, "expected_workflow_version": 1})
    history = client.get(base + "/review-events").json()
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0006")
        command.upgrade(config, "head")
        command.check(config)
    assert client.get(base + "/review-events").json() == history
    assert all(event["reviewed_values_version"] is None for event in history)
    assert (
        client.post(base + "/mark-ready", json=ready(run, expected_workflow_version=2)).status_code
        == 200
    )
    with pytest.raises(RuntimeError, match="Cannot downgrade"):
        with db_engine.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "0006")
    with db_engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0007"
    assert client.get(base).json()["status"] == "ready"
