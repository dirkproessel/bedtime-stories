"""
Persistent storage service for bedtime stories (SQLite).
"""

import json
import logging
from pathlib import Path
from sqlmodel import Session, select
from app.models import StoryMeta, User
from app.database import engine, create_db_and_tables
from app.config import settings
from app.auth_utils import get_password_hash
import uuid

logger = logging.getLogger(__name__)

class StoryStore:
    def __init__(self):
        # Create DB tables if they don't exist
        create_db_and_tables()
        # Optional: migrate from old JSON if it exists and DB is empty
        self._migrate_json_to_db()
        # Ensure admin user exists
        self._seed_admin()

    def _migrate_json_to_db(self):
        """One-time migration from stories.json to SQLite."""
        old_json_path = settings.AUDIO_OUTPUT_DIR / "stories.json"
        if not old_json_path.exists():
            return
            
        with Session(engine) as session:
            existing = session.exec(select(StoryMeta)).first()
            if existing: # Migration already happened
                return
                
            try:
                data = json.loads(old_json_path.read_text(encoding="utf-8"))
                for story_id, story_data in data.items():
                    # Handle old fields or differences if any
                    if "user_id" not in story_data:
                        story_data["user_id"] = None
                    story = StoryMeta(**story_data)
                    session.add(story)
                session.commit()
                logger.info(f"Migrated {len(data)} stories from JSON to SQLite!")
                # Move original file to prevent re-reading
                old_json_path.rename(old_json_path.with_suffix(".json.migrated"))
            except Exception as e:
                logger.error(f"Failed to migrate old JSON data: {e}")

    def _seed_admin(self):
        """Ensure the admin user exists in the database."""
        email = settings.POCKETBASE_ADMIN_EMAIL
        password = settings.POCKETBASE_ADMIN_PASSWORD
        
        if not email or not password:
            logger.warning("Admin credentials not set in environment. Skipping seeding.")
            return
            
        with Session(engine) as session:
            existing = session.exec(select(User).where(User.email == email.lower())).first()
            if existing:
                return
                
            try:
                admin_user = User(
                    id=str(uuid.uuid4()),
                    email=email.lower(),
                    hashed_password=get_password_hash(password),
                    is_admin=True
                )
                session.add(admin_user)
                session.commit()
                logger.info(f"Admin user {email} seeded successfully!")
            except Exception as e:
                logger.error(f"Failed to seed admin user: {e}")

    def get_all(self, only_spotify: bool = False, user_id: str | None = None) -> list[StoryMeta]:
        """Get all stories, sorted by creation date (newest first)."""
        with Session(engine) as session:
            statement = select(StoryMeta).order_by(StoryMeta.created_at.desc())
            if only_spotify:
                statement = statement.where(StoryMeta.is_on_spotify == True)
            if user_id:
                statement = statement.where(StoryMeta.user_id == user_id)
            
            results = session.exec(statement).all()
            return list(results)

    def get_all_users(self) -> list[User]:
        """Get all users for admin lookup."""
        with Session(engine) as session:
            return list(session.exec(select(User)).all())

    def get_by_id(self, story_id: str) -> StoryMeta | None:
        """Get a specific story by ID."""
        with Session(engine) as session:
            return session.get(StoryMeta, story_id)

    def add_story(self, story: StoryMeta):
        """Add or update a story."""
        with Session(engine) as session:
            # Try to get existing one
            existing = session.get(StoryMeta, story.id)
            if existing:
                # Update all fields from the passed story
                story_data = story.model_dump(exclude_unset=True)
                for key, value in story_data.items():
                    setattr(existing, key, value)
                session.add(existing)
            else:
                session.add(story)
            session.commit()

    def update_spotify_status(self, story_id: str, enabled: bool) -> bool:
        """Toggle Spotify status for a story."""
        with Session(engine) as session:
            story = session.get(StoryMeta, story_id)
            if story:
                story.is_on_spotify = enabled
                session.add(story)
                session.commit()
                return True
            return False

    def delete_story(self, story_id: str) -> bool:
        """Remove a story from the database."""
        with Session(engine) as session:
            story = session.get(StoryMeta, story_id)
            if story:
                session.delete(story)
                session.commit()
                return True
            return False

# Singleton instance
store = StoryStore()
