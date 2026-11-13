from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.main import app
from app.schemas.workflow import InformationRequest
from app.services.referral_workflow import ReferralWorkflowService

DATA = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside Primary Care", "requested_specialty": "cardiology",
    "referral_reason": "Palpitations",
}
REQUEST = {
    "reviewer": " Demo coordinator ", "reason": " Conflicting dates ",
    "requested_information": " Confirm date of birth ", "expected_workflow_version": 0,
}


AUDIT = {"reviewer": "Test coordinator", "reason": "Confirmed source",
         "expected_values_version": 0}


def create(client):
    return client.post("/api/referrals", json=DATA).json()


def test_request_resume_and_history_survive_reconnection(client, db_engine):
    referral = create(client)
    base = f"/api/referrals/{referral['id']}"
    assert referral['status'] == 'received' and referral['workflow_version'] == 0
    assert client.get(base + '/review-events').json() == []
    response = client.post(base + '/information-requests', json=REQUEST)
    assert response.status_code == 201
    assert response.json()['status'] == 'missing_information'
    first = client.get(base + '/review-events').json()[0]
    assert first['previous_status'] == 'received'
    assert first['reviewer'] == 'Demo coordinator'
    assert first['reason'] == 'Conflicting dates'
    assert first['requested_information'] == 'Confirm date of birth'
    assert first['extraction_id'] is None
    resumed = client.post(base + '/resume-review', json={
        'reviewer': 'Second coordinator', 'reason': 'Additional information received',
        'expected_workflow_version': 1,
    })
    assert resumed.status_code == 200
    assert resumed.json()['status'] == 'review_required'
    assert resumed.json()['workflow_version'] == 2
    db_engine.dispose()
    with TestClient(app) as reopened:
        assert reopened.get(base).json() == resumed.json()
        events = reopened.get(base + '/review-events').json()
        assert [event['workflow_version'] for event in events] == [2, 1]
        assert events[1] == first
        assert events[0]['previous_status'] == 'missing_information'
        assert events[0]['action'] == 'resume_review'
        again = reopened.post(base + '/information-requests', json={
            **REQUEST, 'expected_workflow_version': 2,
        })
        assert again.status_code == 201
        assert len(reopened.get(base + '/review-events').json()) == 3


def test_invalid_and_stale_actions_do_not_append_history(client):
    referral = create(client)
    base = f"/api/referrals/{referral['id']}"
    resume = {key: value for key, value in REQUEST.items() if key != 'requested_information'}
    assert client.post(base + '/resume-review', json=resume).status_code == 409
    assert client.post(base + '/information-requests', json=REQUEST).status_code == 201
    assert client.post(base + '/information-requests', json=REQUEST).status_code == 409
    assert client.post(base + '/information-requests', json={
        **REQUEST, 'expected_workflow_version': 1,
    }).status_code == 409
    assert len(client.get(base + '/review-events').json()) == 1
    assert client.get(base).json()['workflow_version'] == 1


@pytest.mark.parametrize('changes', [
    {'reviewer': ' '}, {'reason': ''}, {'requested_information': ' '},
    {'expected_workflow_version': -1}, {'expected_workflow_version': True},
    {'expected_workflow_version': '0'}, {'status': 'approved'}, {'reason': 'x' * 2001},
])
def test_invalid_commands_leave_referral_unchanged(client, changes):
    referral = create(client)
    base = f"/api/referrals/{referral['id']}"
    response = client.post(base + '/information-requests', json={**REQUEST, **changes})
    assert response.status_code == 422
    assert client.get(base).json() == referral
    assert client.get(base + '/review-events').json() == []


def test_scope_checks_and_server_managed_status(client, pdf_factory):
    first, second = create(client), create(client)
    base = f"/api/referrals/{first['id']}"
    other = f"/api/referrals/{second['id']}"
    client.post(other + '/documents', files={'file': ('source.pdf', pdf_factory())})
    run = client.post(other + '/extractions').json()
    for extraction_id in [run['id'], str(uuid4())]:
        assert client.post(base + '/information-requests', json={
            **REQUEST, 'extraction_id': extraction_id,
        }).status_code == 422
    for field, value in [('status', 'missing_information'), ('workflow_version', 5)]:
        assert client.patch(base, json={**AUDIT, field: value}).status_code == 422
        assert client.post('/api/referrals', json={**DATA, field: value}).status_code == 422
    for route in ['/review-events', '/information-requests', '/resume-review']:
        missing = f'/api/referrals/{uuid4()}' + route
        response = client.get(missing) if route == '/review-events' else client.post(
            missing, json=REQUEST if route == '/information-requests' else {
                'reviewer': 'Coordinator', 'reason': 'Resume', 'expected_workflow_version': 0,
            },
        )
        assert response.status_code == 404
    assert client.get(base + '/review-events').json() == []


def test_upload_extraction_and_corrections_preserve_request_and_snapshots(client, pdf_factory):
    referral = create(client)
    base = f"/api/referrals/{referral['id']}"
    client.post(base + '/documents', files={'file': ('first.pdf', pdf_factory())})
    run = client.post(base + '/extractions').json()
    assert client.post(base + '/information-requests', json={
        **REQUEST, 'extraction_id': run['id'],
    }).status_code == 201
    event = client.get(base + '/review-events').json()[0]
    assert event['extraction_id'] == run['id']
    client.post(base + '/documents', files={'file': ('second.pdf', pdf_factory())})
    client.post(base + '/extractions')
    client.patch(base, json={**AUDIT, 'patient_name': 'Corrected name'})
    current = client.get(base).json()
    assert current['status'] == 'missing_information' and current['workflow_version'] == 1
    assert client.get(base + '/review-events').json() == [event]
    assert client.get(base + '/extractions/' + run['id']).json() == run


def test_commit_failure_rolls_back_status_and_event(client, db_engine, monkeypatch):
    referral = create(client)
    with Session(db_engine) as session:
        def fail():
            raise RuntimeError('simulated commit failure')
        monkeypatch.setattr(session, 'commit', fail)
        with pytest.raises(RuntimeError):
            ReferralWorkflowService(session).apply(
                UUID(referral['id']), 'request_missing_information',
                    InformationRequest(**REQUEST),
            )
    base = f"/api/referrals/{referral['id']}"
    assert client.get(base).json() == referral
    assert client.get(base + '/review-events').json() == []


def test_concurrent_requests_accept_only_one_version(client, db_engine):
    referral = create(client)
    def apply():
        with Session(db_engine) as session:
            try:
                ReferralWorkflowService(session).apply(
                    UUID(referral['id']), 'request_missing_information',
                    InformationRequest(**REQUEST),
                )
                return 201
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: apply(), range(2))) == [201, 409]
    assert len(client.get(f"/api/referrals/{referral['id']}/review-events").json()) == 1


def test_migration_initializes_legacy_referral_without_inventing_events(db_engine):
    config = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
    identifier = uuid4()
    with db_engine.begin() as connection:
        config.attributes['connection'] = connection
        command.downgrade(config, '0004')
        connection.execute(text(
            'INSERT INTO referrals (id, patient_name, date_of_birth, referring_organization, '
            'requested_specialty, referral_reason, created_at) '
            "VALUES (:id, 'Legacy', '1974-03-12', 'Clinic', 'cardiology', 'Review', now())"
        ), {'id': identifier})
        command.upgrade(config, 'head')
        command.check(config)
        row = connection.execute(text(
            'SELECT status, workflow_version FROM referrals WHERE id = :id'
        ), {'id': identifier}).one()
        assert tuple(row) == ('received', 0)
        assert connection.scalar(text('SELECT count(*) FROM review_events')) == 0
