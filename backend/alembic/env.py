from alembic import context
from sqlalchemy import create_engine, pool

from app.config import settings
from app.database import Base
from app.models.referral import ReferralRecord  # noqa: F401

config = context.config
target_metadata = Base.metadata
# Tests can supply their own connection without changing the application database.
connection = config.attributes.get("connection")


def migrate(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=settings.database_url, target_metadata=target_metadata, literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    migrate(connection)
else:
    engine = create_engine(settings.database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        migrate(connection)
    engine.dispose()
