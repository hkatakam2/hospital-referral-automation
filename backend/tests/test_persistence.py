from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import app
from app.models.referral import ReferralRecord
from app.repositories.referrals import ReferralRepository
from app.schemas.referral import ReferralCreate

DATA = {
    "patient_name": "Avery Morgan",
    "date_of_birth": "1974-03-12",
    "referring_organization": "Lakeside Primary Care",
    "requested_specialty": "cardiology",
    "referral_reason": "Recurrent palpitations",
}


AUDIT = {"reviewer": "Test coordinator", "reason": "Confirmed source",
         "expected_values_version": 0}


def test_records_and_corrections_survive_new_connections(client, db_engine):
    first = client.post("/api/referrals", json=DATA).json()
    second = client.post("/api/referrals", json={**DATA, "patient_name": "Jordan Ellis"}).json()
    corrected = client.patch(
        f"/api/referrals/{first['id']}", json={**AUDIT, "date_of_birth": "1974-03-21"},
    ).json()
    # Discard pooled connections and use a new client and new sessions.
    db_engine.dispose()
    with TestClient(app) as reopened:
        assert reopened.get(f"/api/referrals/{first['id']}").json() == corrected
        assert reopened.get(f"/api/referrals/{second['id']}").json() == second
        assert reopened.get("/api/referrals").json() == [corrected, second]


def test_migration_can_downgrade_and_rebuild_empty_database(db_engine):
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert "referrals" not in inspect(connection).get_table_names()
        command.upgrade(config, "head")
        assert "referrals" in inspect(connection).get_table_names()
        assert "documents" in inspect(connection).get_table_names()
        assert "document_pages" in inspect(connection).get_table_names()
        assert connection.scalar(text("SELECT count(*) FROM referrals")) == 0
        command.check(config)


def test_document_migration_preserves_existing_referrals(db_engine):
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0001")
    identifier = uuid4()
    # Use the historical schema directly; today's ORM also includes workflow columns.
    with db_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO referrals (id, patient_name, date_of_birth, referring_organization, "
            "requested_specialty, referral_reason, created_at) VALUES "
            "(:id, :patient_name, :date_of_birth, :referring_organization, "
            ":requested_specialty, :referral_reason, :created_at)"
        ), {**DATA, "id": identifier, "created_at": datetime.now(timezone.utc)})
    with db_engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
        command.check(config)
    with Session(db_engine) as session:
        referral = ReferralRepository(session).get(identifier)
        assert referral is not None
        assert referral.patient_name == DATA["patient_name"]
        assert referral.status == "received" and referral.workflow_version == 0


def test_database_rejects_invalid_write_and_request_session_rolls_back(db_engine):
    dependency = get_session()
    session = next(dependency)
    record = ReferralRecord(
        **ReferralCreate(**DATA).model_dump(), id=uuid4(), created_at=datetime.now(timezone.utc),
    )
    record.patient_name = "   "
    session.add(record)
    with pytest.raises(IntegrityError) as failure:
        session.commit()
    with pytest.raises(IntegrityError):
        dependency.throw(failure.value)
    assert not session.in_transaction()
    with Session(db_engine) as fresh:
        repository = ReferralRepository(fresh)
        assert repository.list() == []
        assert repository.create(ReferralCreate(**DATA)).patient_name == DATA["patient_name"]


def test_list_orders_equal_timestamps_by_uuid(db_engine):
    timestamp = datetime.now(timezone.utc)
    low = UUID(int=1)
    high = UUID(int=2)
    with Session(db_engine) as session:
        for identifier in [high, low]:
            session.add(ReferralRecord(
                **ReferralCreate(**DATA).model_dump(), id=identifier, created_at=timestamp,
            ))
        session.commit()
        assert [record.id for record in ReferralRepository(session).list()] == [low, high]
