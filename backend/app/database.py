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

def get_session():
    with Session(engine) as session:
        yield session
