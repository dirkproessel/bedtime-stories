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
            ("alexa_user_id", "TEXT"),
            ("custom_voice_id", "TEXT"),
            ("custom_voice_name", "TEXT")
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
            
        print("Migration: Migrating legacy custom_voice_id to uservoice table...")
        import uuid
        cur.execute("SELECT id, custom_voice_id, custom_voice_name, created_at FROM user WHERE custom_voice_id IS NOT NULL")
        users_with_voice = cur.fetchall()
        for u_id, c_id, c_name, u_created in users_with_voice:
            # Check if this voice is already in uservoice table
            cur.execute("SELECT id FROM uservoice WHERE user_id = ? AND fish_voice_id = ?", (u_id, c_id))
            if not cur.fetchone():
                v_id = str(uuid.uuid4())
                v_name = c_name if c_name else "My Voice"
                cur.execute("INSERT INTO uservoice (id, user_id, fish_voice_id, name, is_public, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (v_id, u_id, c_id, v_name, False, u_created))
        conn.commit()

        # We keep custom_voice_id on user table for easy fallback for now.
        
        # Check if columns exist in uservoice table
        try:
            cur.execute("PRAGMA table_info(uservoice)")
            voice_columns = [row[1] for row in cur.fetchall()]
            
            voice_needed = [
                ("gender", "TEXT"),
                ("description", "TEXT")
            ]
            
            for col_name, col_type in voice_needed:
                if col_name.lower() not in [c.lower() for c in voice_columns]:
                    print(f"Migration: Adding {col_name} to uservoice...")
                    cur.execute(f"ALTER TABLE uservoice ADD COLUMN {col_name} {col_type}")
                    conn.commit()
            
            # --- Check if columns exist in systemvoice table ---
            cur.execute("PRAGMA table_info(systemvoice)")
            sys_columns = [row[1] for row in cur.fetchall()]
            
            sys_needed = [
                ("description", "TEXT"),
                ("is_active", "BOOLEAN DEFAULT 1"),
                ("fish_voice_id", "TEXT"),
                ("created_at", "DATETIME")
            ]
            
            for col_name, col_type in sys_needed:
                if col_name.lower() not in [c.lower() for c in sys_columns]:
                    print(f"Migration: Adding {col_name} to systemvoice...")
                    cur.execute(f"ALTER TABLE systemvoice ADD COLUMN {col_name} {col_type}")
                    conn.commit()

            # --- Check if systemsetting table exists and seed it ---
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='systemsetting'")
            if not cur.fetchone():
                print("Migration: Creating systemsetting table...")
                cur.execute("""
                    CREATE TABLE systemsetting (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        description TEXT,
                        updated_at DATETIME
                    )
                """)
                # Seed defaults
                now_iso = datetime.now(timezone.utc).isoformat()
                defaults = [
                    ("gemini_text_model", settings.GEMINI_TEXT_MODEL, "Current Gemini model used for story text generation"),
                    ("gemini_image_model", settings.GEMINI_IMAGE_MODEL, "Current Gemini model used for story cover generation")
                ]
                for k, v, d in defaults:
                    cur.execute("INSERT INTO systemsetting (key, value, description, updated_at) VALUES (?, ?, ?, ?)", (k, v, d, now_iso))
                conn.commit()
                    
        except Exception as e:
            print(f"Migration voice/systemvoice warning: {e}")
        
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()

def get_session():
    with Session(engine) as session:
        yield session
