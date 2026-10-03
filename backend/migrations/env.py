from alembic import context

from app import models  # noqa: F401
from app.db import Base, engine

target_metadata = Base.metadata
if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        sqlite = connection.dialect.name == "sqlite"
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True, render_as_batch=True
        )
        with context.begin_transaction():
            context.run_migrations()

        if sqlite:
            connection.commit()
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Migration left invalid foreign keys")
