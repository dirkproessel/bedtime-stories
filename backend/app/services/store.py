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

# Ownership stability: No more automatic migrations or repairs.
# Manual user assignment is the source of truth.

class StoryStore:
    def __init__(self):
        # Create DB tables if they don't exist
        create_db_and_tables()
        # Seed admin with is_admin=True but don't force ID syncs or ownership transfers
        self._seed_admin()
        # All automatic repairs and migrations are disabled to respect manual user fixes.

    def _repair_ownership_mistake(self):
        """DEPRECATED: One-time fix was completed. Manual control is preferred now."""
        pass

    def _migrate_json_to_db(self):
        """DEPRECATED: Manual control preferred."""
        pass

    def _seed_admin(self):
        """Ensure the admin user exists in the database."""
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD
        
        if not email or not password:
            logger.warning("Admin credentials not set in environment. Skipping seeding.")
            return
            
        with Session(engine) as session:
            # Check if there's a user with this email
            existing_by_email = session.exec(select(User).where(User.email == email.lower())).first()
            
            if existing_by_email:
                # Always ensure ID, is_admin and kindle_email are correct for the admin
                needs_update = False
                
                # ID is already correct or we don't care about forced sync anymore
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
                    logger.info(f"User {email} settings updated.")
                return
                
            # If user doesn't exist at all, create with generated ID
            try:
                admin_user = User(
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

    def _repair_unassigned_stories(self):
        """DEPRECATED: Manual control preferred."""
        pass

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
