from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.referral import CorrectionCommand
from app.services.referral_correction import ReferralCorrectionService

DATA = {
    "patient_name": "Avery Morgan", "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside Primary Care", "requested_specialty": "cardiology",
    "referral_reason": "Palpitations",
}
AUDIT = {"reviewer": " Demo coordinator ", "reason": " Confirmed source ",
         "expected_values_version": 0}


def create(client):
    referral = client.post('/api/referrals', json=DATA).json()
    return f"/api/referrals/{referral['id']}", referral


def test_atomic_changes_history_scoping_and_new_connections(client, db_engine):
    base, original = create(client)
    other, _ = create(client)
    before = datetime.now(timezone.utc)
    updated = client.patch(base, json={**AUDIT, 'date_of_birth': '1974-03-21',
                                      'patient_name': ' Avery Corrected '})
    after = datetime.now(timezone.utc)
    assert updated.status_code == 200
    assert updated.json()['values_version'] == 1
    assert updated.json()['workflow_version'] == original['workflow_version']
    assert updated.json()['status'] == original['status']
    db_engine.dispose()
    events = client.get(base + '/correction-events').json()
    assert len(events) == 1
    event = events[0]
    assert event['changes'] == {
        'patient_name': {'previous': 'Avery Morgan', 'new': 'Avery Corrected'},
        'date_of_birth': {'previous': '1974-03-12', 'new': '1974-03-21'},
    }
    assert event['reviewer'] == 'Demo coordinator' and event['reason'] == 'Confirmed source'
    assert before <= datetime.fromisoformat(event['created_at'].replace('Z', '+00:00')) <= after
    assert client.get(other + '/correction-events').json() == []
    assert client.get(base + '/review-events').json() == []
    assert client.get(f'/api/referrals/{uuid4()}/correction-events').status_code == 404
    assert client.patch(base, json={**AUDIT, 'expected_values_version': 1,
                                    'patient_name': 'Avery Final'}).status_code == 200
    history = client.get(base + '/correction-events').json()
    assert [event['values_version'] for event in history] == [2, 1]
    assert history[1] == event
    assert client.delete(base + '/correction-events').status_code == 405


@pytest.mark.parametrize('changes', [{}, {'patient_name': ' Avery Morgan '}])
def test_no_op_has_no_event_or_version_increment(client, changes):
    base, referral = create(client)
    response = client.patch(base, json={**AUDIT, **changes})
    assert response.status_code == 200 and response.json() == referral
    assert client.get(base + '/correction-events').json() == []


@pytest.mark.parametrize('metadata', [
    {}, {key: value for key, value in AUDIT.items() if key != 'reviewer'},
    {key: value for key, value in AUDIT.items() if key != 'reason'},
    {key: value for key, value in AUDIT.items() if key != 'expected_values_version'},
    {**AUDIT, 'reviewer': ''}, {**AUDIT, 'reason': '  '},
    {**AUDIT, 'reviewer': 'x' * 2001}, {**AUDIT, 'reason': None},
    {**AUDIT, 'expected_values_version': -1}, {**AUDIT, 'expected_values_version': True},
    {**AUDIT, 'expected_values_version': '0'},
])
def test_required_audit_metadata_and_version_are_validated(client, metadata):
    base, referral = create(client)
    assert client.patch(base, json={**metadata, 'patient_name': 'Changed'}).status_code == 422
    assert client.get(base).json() == referral
    assert client.get(base + '/correction-events').json() == []


def test_concurrent_commands_accept_one_and_reject_stale_retry(client, db_engine):
    base, referral = create(client)
    def apply():
        with Session(db_engine) as session:
            try:
                ReferralCorrectionService(session).apply(UUID(referral['id']), CorrectionCommand(
                    **AUDIT, patient_name='Changed',
                ))
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: apply(), range(2))) == [200, 409]
    assert client.patch(base, json={**AUDIT, 'patient_name': 'Retry'}).status_code == 409
    assert client.get(base).json()['patient_name'] == 'Changed'
    assert len(client.get(base + '/correction-events').json()) == 1


def test_failed_commit_rolls_back_values_version_and_event(client, db_engine, monkeypatch):
    base, referral = create(client)
    with Session(db_engine) as session:
        def fail():
            raise RuntimeError('injected commit failure')
        monkeypatch.setattr(session, 'commit', fail)
        with pytest.raises(RuntimeError):
            ReferralCorrectionService(session).apply(UUID(referral['id']), CorrectionCommand(
                **AUDIT, patient_name='Not saved',
            ))
    assert client.get(base).json() == referral
    assert client.get(base + '/correction-events').json() == []


def test_legacy_migration_preserves_values_without_inventing_history(db_engine):
    config = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
    identifier = uuid4()
    with db_engine.begin() as connection:
        config.attributes['connection'] = connection
        command.downgrade(config, '0005')
        connection.execute(text(
            'INSERT INTO referrals (id, patient_name, date_of_birth, referring_organization, '
            'requested_specialty, referral_reason, created_at) VALUES '
            "(:id, 'Legacy', '1974-03-12', 'Clinic', 'cardiology', 'Review', now())"
        ), {'id': identifier})
        command.upgrade(config, 'head')
        command.check(config)
        assert connection.execute(text(
            'SELECT patient_name, values_version FROM referrals WHERE id = :id'
        ), {'id': identifier}).one() == ('Legacy', 0)
        assert connection.scalar(text('SELECT count(*) FROM correction_events')) == 0
