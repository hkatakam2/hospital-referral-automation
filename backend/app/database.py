from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    # Writes commit in the repository before a successful response is returned.
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
