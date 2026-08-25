from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy import text

# Insert project root to sys.path so it works when run from anywhere
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import engine
from backend.models import Base
# Import all models to ensure Base.metadata is fully populated
import backend.models


def reset_database() -> None:
    table_names = list(Base.metadata.tables.keys())
    if not table_names:
        print("No tables found in Base.metadata.")
        return

    # Filter out alembic_version if it is present in Base.metadata (usually it isn't)
    table_names = [name for name in table_names if name != "alembic_version"]

    print(f"Truncating tables: {', '.join(table_names)}...")
    with engine.begin() as conn:
        # PostgreSQL specific query to truncate all tables and restart identities
        sql = f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE;"
        conn.execute(text(sql))
    print("Database has been reset successfully.")


if __name__ == "__main__":
    reset_database()
