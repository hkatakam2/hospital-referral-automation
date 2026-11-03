import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
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
        connection.execute(text("TRUNCATE referrals"))
    monkeypatch.setattr(database, "engine", postgres_engine)
    yield postgres_engine
    with postgres_engine.begin() as connection:
        connection.execute(text("TRUNCATE referrals"))


@pytest.fixture
def client(db_engine):
    with TestClient(app) as test_client:
        yield test_client
