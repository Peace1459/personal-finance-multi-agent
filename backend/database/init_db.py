
from backend.database.connection import Base, engine
from sqlalchemy import inspect, text

def migrate_import_batches():
    """Add file_hash to existing import_batches tables safely."""

    inspector = inspect(engine)

    if "import_batches" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("import_batches")
    }

    if "file_hash" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE import_batches "
                    "ADD COLUMN file_hash VARCHAR(64)"
                )
            )

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "uq_import_batches_file_hash "
                "ON import_batches (file_hash)"
            )
        )
Base.metadata.create_all(bind=engine)
migrate_import_batches()

print("Database tables initialized successfully.")
