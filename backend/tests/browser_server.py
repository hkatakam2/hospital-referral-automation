"""Serve the real API with an owned temporary database and document directory."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))
os.chdir(backend)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

from app.config import settings  # noqa: E402

url = make_url(os.environ.get("TEST_DATABASE_URL", settings.database_url))
name = "referral_test_browser_" + uuid4().hex
admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as connection:
    connection.execute(text(f'CREATE DATABASE "{name}"'))
try:
    with TemporaryDirectory(prefix="referral-browser-") as storage:
        # Default to no Gemini. Playwright explicitly selects stub or live mode.
        mode = os.environ.get("REFERRAL_TEST_GEMINI_MODE", "disabled")
        if mode not in {"disabled", "stub", "live"}:
            raise ValueError("Unknown browser Gemini test mode")
        settings.gemini_enabled = mode == "live"
        if mode == "stub":
            from gemini_browser_stub import enable
            enable()
        settings.database_url = url.set(database=name).render_as_string(hide_password=False)
        settings.document_storage_dir = Path(storage)
        command.upgrade(Config(str(backend / "alembic.ini")), "head")
        import uvicorn

        uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="warning")
finally:
    # Only the database created by this process is dropped. Never touch development data.
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    admin.dispose()
