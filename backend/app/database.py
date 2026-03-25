import os
from pathlib import Path
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

# Store the database in the audio output directory so it persists
# alongside the audio files.
sqlite_file_name = "bedtime_stories.db"
sqlite_url = f"sqlite:///{settings.AUDIO_OUTPUT_DIR}/{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    ensure_migrations()

def ensure_migrations():
    """Simple SQLite migrations for existing tables."""
    import sqlite3
    from datetime import datetime, timezone
    db_path = Path(settings.AUDIO_OUTPUT_DIR) / sqlite_file_name
    if not db_path.exists():
        return
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    try:
        # Check if columns exist in storymeta
        cur.execute("PRAGMA table_info(storymeta)")
        columns = [row[1] for row in cur.fetchall()]
        
        # Define needed columns and their SQL types/defaults
        needed_columns = [
            ("parent_id", "TEXT"),
            ("user_id", "TEXT"),
            ("is_public", "BOOLEAN DEFAULT 0"),
            ("user_email", "TEXT"),
            ("word_count", "INTEGER"),
            ("voice_name", "TEXT"),
            ("duration_seconds", "FLOAT"),
            ("image_url", "TEXT"),
            ("is_on_spotify", "BOOLEAN DEFAULT 0")
        ]
        
        for col_name, col_type in needed_columns:
            if col_name.lower() not in [c.lower() for c in columns]:
                print(f"Migration: Adding {col_name} to storymeta...")
                cur.execute(f"ALTER TABLE storymeta ADD COLUMN {col_name} {col_type}")
                conn.commit()

        if "updated_at" not in [c.lower() for c in columns]:
            print("Migration: Adding updated_at to storymeta...")
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(f"ALTER TABLE storymeta ADD COLUMN updated_at DATETIME DEFAULT '{now_iso}'")
            conn.commit()

        # Check if columns exist in user table
        cur.execute("PRAGMA table_info(user)")
        user_columns = [row[1] for row in cur.fetchall()]
        
        user_needed = [
            ("username", "TEXT"),
            ("kindle_email", "TEXT"),
            ("avatar_url", "TEXT"),
            ("alexa_user_id", "TEXT")
        ]
        
        for col_name, col_type in user_needed:
            if col_name.lower() not in [c.lower() for c in user_columns]:
                print(f"Migration: Adding {col_name} to user...")
                cur.execute(f"ALTER TABLE user ADD COLUMN {col_name} {col_type}")
                if col_name == "alexa_user_id":
                    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_user_alexa_user_id ON user (alexa_user_id)")
                conn.commit()

        if "created_at" not in [c.lower() for c in user_columns]:
            print("Migration: Adding created_at to user...")
            now_iso = datetime.now(timezone.utc).isoformat()
            cur.execute(f"ALTER TABLE user ADD COLUMN created_at DATETIME DEFAULT '{now_iso}'")
            conn.commit()
            
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()

def get_session():
    with Session(engine) as session:
        yield session
