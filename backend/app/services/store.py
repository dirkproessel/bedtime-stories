from datetime import datetime
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

def parse_date(date_val):
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val
    try:
        if isinstance(date_val, str):
            # Handle ISO format with 'Z' suffix
            clean_date = date_val.replace('Z', '+00:00')
            return datetime.fromisoformat(clean_date)
    except Exception as e:
        logger.warning(f"Could not parse date {date_val}: {e}")
    return None

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
                    
                    # Ensure created_at is a datetime object
                    if "created_at" in story_data:
                        story_data["created_at"] = parse_date(story_data["created_at"])
                        
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
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD
        
        if not email or not password:
            logger.warning("Admin credentials not set in environment. Skipping seeding.")
            return
            
        # Fixed ID for the main admin to ensure RSS Feed stability (legacy link migration)
        ADMIN_ID = "3aef172e-d006-4444-8888-migration-admin"
        
        with Session(engine) as session:
            # 1. First, check if there's any user with this ID already
            existing_by_id = session.get(User, ADMIN_ID)
            
            # 2. Then check if there's a user with this email
            existing_by_email = session.exec(select(User).where(User.email == email.lower())).first()
            
            if existing_by_email:
                # Always ensure is_admin and kindle_email are set for the configured admin
                needs_update = False
                if not existing_by_email.is_admin:
                    existing_by_email.is_admin = True
                    needs_update = True
                if not existing_by_email.kindle_email and settings.KINDLE_EMAIL:
                    existing_by_email.kindle_email = settings.KINDLE_EMAIL
                    needs_update = True
                    
                if needs_update:
                    session.add(existing_by_email)
                    session.commit()
                    logger.info(f"User {email} settings updated (admin/kindle).")
                return
                
            # If user doesn't exist at all, create with stable ID
            try:
                admin_user = User(
                    id=ADMIN_ID,
                    email=email.lower(),
                    hashed_password=get_password_hash(password),
                    is_admin=True,
                    kindle_email=settings.KINDLE_EMAIL
                )
                session.add(admin_user)
                session.commit()
                logger.info(f"Admin user {email} seeded with stable ID and Kindle settings!")
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
