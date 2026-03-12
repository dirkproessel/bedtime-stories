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

# Fixed ID for the main admin to ensure RSS Feed stability (legacy link migration)
ADMIN_ID = "3aef172e-d006-4444-8888-migration-admin"

class StoryStore:
    def __init__(self):
        # Create DB tables if they don't exist
        create_db_and_tables()
        # Optional: migrate from old JSON if it exists and DB is empty
        self._migrate_json_to_db()
        # Ensure admin user exists
        self._seed_admin()
        # Repair: Assign owner-less stories to admin
        self._repair_unassigned_stories()
        # EMERGENCY: Revert mistaken transfer to Admin
        self._repair_ownership_mistake()

    def _repair_ownership_mistake(self):
        """DEPRECATED: One-time fix was completed. Manual control is preferred now."""
        pass

    def _migrate_json_to_db(self):
        """One-time migration from stories.json to SQLite."""
        old_json_path = settings.AUDIO_OUTPUT_DIR / "stories.json"
        
        # Also check for already migrated but incomplete stories (missing story.json)
        migrated_json_path = settings.AUDIO_OUTPUT_DIR / "stories.json.migrated"
        
        target_path = old_json_path if old_json_path.exists() else migrated_json_path
        
        if not target_path.exists():
            return
            
        with Session(engine) as session:
            # We don't skip entirely if migrated_json exists, because we might need to repair files
            try:
                data = json.loads(target_path.read_text(encoding="utf-8"))
                migrated_count = 0
                repaired_count = 0
                
                for story_id, story_data in data.items():
                    # 1. Ensure story metadata is in DB
                    existing = session.get(StoryMeta, story_id)
                    
                    # USE ORIGINAL IDs (Do not force to ADMIN_ID anymore)
                    owner_id = story_data.get("user_id")
                    owner_email = story_data.get("user_email")
                    
                    # Only fallback to admin if absolutely no owner info exists
                    if not owner_id:
                        owner_id = ADMIN_ID
                        owner_email = settings.ADMIN_EMAIL
                    
                    if not existing:
                        # Ensure created_at is a datetime object
                        if "created_at" in story_data:
                            story_data["created_at"] = parse_date(story_data["created_at"])
                            
                        # Extract chapters before creating StoryMeta (which doesn't have chapters field)
                        story_data_for_meta = story_data.copy()
                        chapters = story_data_for_meta.pop("chapters", [])
                        
                        # Re-assign calculated owner
                        story_data_for_meta["user_id"] = owner_id
                        story_data_for_meta["user_email"] = owner_email
                        
                        story = StoryMeta(**story_data_for_meta)
                        session.add(story)
                        migrated_count += 1
                    else:
                        chapters = story_data.get("chapters", [])

                    # 2. Ensure story.json exists in the subdirectory

                    # 2. Ensure story.json exists in the subdirectory
                    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
                    story_json_file = story_dir / "story.json"
                    if chapters and not story_json_file.exists():
                        try:
                            story_dir.mkdir(parents=True, exist_ok=True)
                            story_json_file.write_text(json.dumps({
                                "id": story_id,
                                "title": story_data.get("title", "Story"),
                                "chapters": chapters
                            }, indent=2, ensure_ascii=False), encoding="utf-8")
                            repaired_count += 1
                        except Exception as e:
                            logger.error(f"Failed to create story.json for {story_id}: {e}")

                session.commit()
                if migrated_count > 0:
                    logger.info(f"Migrated {migrated_count} stories to SQLite!")
                if repaired_count > 0:
                    logger.info(f"Repaired {repaired_count} story.json files from backup!")
                
                # Move original file only if it was the fresh one
                if target_path == old_json_path:
                    old_json_path.rename(old_json_path.with_suffix(".json.migrated"))
            except Exception as e:
                logger.error(f"Failed to migrate/repair JSON data: {e}", exc_info=True)

    def _seed_admin(self):
        """Ensure the admin user exists in the database."""
        email = settings.ADMIN_EMAIL
        password = settings.ADMIN_PASSWORD
        
        if not email or not password:
            logger.warning("Admin credentials not set in environment. Skipping seeding.")
            return
            
        with Session(engine) as session:
            # 1. First, check if there's any user with this ID already
            existing_by_id = session.get(User, ADMIN_ID)
            
            # 2. Then check if there's a user with this email
            existing_by_email = session.exec(select(User).where(User.email == email.lower())).first()
            
            if existing_by_email:
                # Always ensure ID, is_admin and kindle_email are correct for the admin
                needs_update = False
                
                # Check if we need to sync the ID (Manual registration mismatch)
                if existing_by_email.id != ADMIN_ID:
                    logger.info(f"Admin ID mismatch. Moving {email} from {existing_by_email.id} to {ADMIN_ID}")
                    # Direct SQL to update PK - safest way in SQLite/SQLModel for this one-time fix
                    from sqlalchemy import text
                    session.execute(text("UPDATE user SET id = :new_id WHERE email = :email"), {"new_id": ADMIN_ID, "email": email.lower()})
                    session.execute(text("UPDATE storymeta SET user_id = :new_id WHERE user_id = :old_id"), {"new_id": ADMIN_ID, "old_id": existing_by_email.id})
                    session.commit()
                    # Refresh object
                    existing_by_email = session.get(User, ADMIN_ID)
                
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

    def _repair_unassigned_stories(self):
        """Find stories without user_id and assign them to the main admin."""
        with Session(engine) as session:
            # Handle actual orphans (user_id is None)
            orphans = session.exec(select(StoryMeta).where(StoryMeta.user_id == None)).all()
            
            if orphans:
                logger.info(f"Repairing {len(orphans)} orphaned stories - assigning to Admin.")
                for story in orphans:
                    story.user_id = ADMIN_ID
                    story.user_email = settings.ADMIN_EMAIL
                    session.add(story)
                session.commit()

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
