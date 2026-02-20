import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'openworld.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate(engine)


def _migrate(eng):
    """Add columns that may be missing from older schemas."""
    from sqlalchemy import text, inspect
    insp = inspect(eng)

    # Map of table -> list of (column_name, column_ddl)
    migrations = {
        "users": [
            ("is_admin", "BOOLEAN DEFAULT 0"),
        ],
        "game_versions": [
            ("parent_version_id", "VARCHAR"),
            ("is_suggested", "BOOLEAN DEFAULT 0"),
            ("suggestion_status", "VARCHAR"),
            ("suggested_at", "DATETIME"),
            ("reviewed_at", "DATETIME"),
            ("reviewed_by", "VARCHAR"),
            ("user_prompt", "TEXT"),
        ],
    }

    with eng.connect() as conn:
        for table, columns in migrations.items():
            existing = {c["name"] for c in insp.get_columns(table)}
            for col_name, col_ddl in columns:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_ddl}"))
        conn.commit()
