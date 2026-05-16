from datetime import datetime
import json
import logging
from pathlib import Path
from sqlmodel import Session, select, delete
from app.models import StoryMeta, User, UserFavorite, StoryMetaResponse, UserVoice, SystemVoice, PlaylistEntry, SystemSetting
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
        # Seed system voices
        self._seed_system_voices()
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

    def _seed_system_voices(self):
        """Seed system voices from tts_service constants. Upserts missing voices."""
        with Session(engine) as session:
            from app.services.tts_service import EDGE_VOICES, GEMINI_VOICES, FISH_VOICES, XAI_VOICES
            
            # Helper to add or update a system voice
            def _upsert_voice(k, name, engine_name, gender, description=None, fish_id=None):
                existing = session.get(SystemVoice, k)
                if not existing:
                    new_voice = SystemVoice(id=k, name=name, engine=engine_name, gender=gender, description=description, fish_voice_id=fish_id)
                    session.add(new_voice)
                    return 1
                return 0
                
            added_count = 0
            
            for k, v in EDGE_VOICES.items():
                added_count += _upsert_voice(k, v['name'], "edge", v['gender'], v.get('description'))
            
            for k, v in GEMINI_VOICES.items():
                added_count += _upsert_voice(k, v['name'], "gemini", v['gender'], v.get('description'))
                
            for k, v in FISH_VOICES.items():
                added_count += _upsert_voice(k, v['name'], "fish", v['gender'], v.get('description'), fish_id=v['id'])

            for k, v in XAI_VOICES.items():
                added_count += _upsert_voice(k, v['name'], "xai", v['gender'], v.get('description'))

            if added_count > 0:
                session.commit()
                logger.info(f"Seeded {added_count} missing system voices into database.")

    def _repair_unassigned_stories(self):
        """DEPRECATED: Manual control preferred."""
        pass

    def get_all(self, only_spotify: bool = False, user_id: str | None = None, genre: list[str] | None = None, search: str | None = None, requesting_user_id: str | None = None) -> list[StoryMeta]:
        """Get all stories with optional filtering, sorted by creation date (newest first)."""
        from sqlmodel import or_
        with Session(engine) as session:
            statement = select(StoryMeta).order_by(StoryMeta.created_at.desc())
            if only_spotify:
                statement = statement.where(StoryMeta.is_on_spotify == True)
            if user_id:
                statement = statement.where(StoryMeta.user_id == user_id)
            if genre:
                statement = statement.where(StoryMeta.genre.in_(genre))
            if search:
                import shlex
                try:
                    # Attempt to parse quotes for exact phrases
                    terms = shlex.split(search)
                except ValueError:
                    # Fallback to simple split if quotes are mismatched
                    terms = search.split()
                
                # Filter out empty terms and apply AND logic across terms
                terms = [t for t in terms if t.strip()]
                for term in terms:
                    term_like = f"%{term}%"
                    statement = statement.where(
                        or_(
                            StoryMeta.title.like(term_like),
                            # Adding case insensitive approximation since SQLite handles mostly ascii case naturally with .like()
                            StoryMeta.description.like(term_like)
                        )
                    )
            
            results = session.exec(statement).all()
            stories = [StoryMetaResponse.model_validate(s) for s in results]

            # Populate is_favorite if requesting_user_id is provided
            if requesting_user_id and stories:
                story_ids = [s.id for s in stories]
                fav_statement = select(UserFavorite.story_id).where(
                    UserFavorite.user_id == requesting_user_id,
                    UserFavorite.story_id.in_(story_ids)
                )
                fav_ids = set(session.exec(fav_statement).all())
                for s in stories:
                    s.is_favorite = s.id in fav_ids

            return stories


    def get_all_users(self) -> list[User]:
        """Get all users for admin lookup."""
        with Session(engine) as session:
            return list(session.exec(select(User)).all())

    def get_admin_voices(self):
        """Get all voices (clones and system) for admin management."""
        with Session(engine) as session:
            clones = session.exec(select(UserVoice)).all()
            system = session.exec(select(SystemVoice)).all()
            return {
                "clones": clones,
                "system": system
            }

    def toggle_voice_active(self, voice_type: str, voice_id: str):
        """Toggle is_active for system voice or is_public for UserVoice (Admin override)."""
        with Session(engine) as session:
            if voice_type == "system":
                voice = session.get(SystemVoice, voice_id)
                if voice:
                    voice.is_active = not voice.is_active
                    session.add(voice)
                    session.commit()
                    return voice.is_active
            else:
                voice = session.get(UserVoice, voice_id)
                if voice:
                    voice.is_public = not voice.is_public
                    session.add(voice)
                    session.commit()
                    return voice.is_public
            return None

    def get_by_id(self, story_id: str, requesting_user_id: str | None = None) -> StoryMetaResponse | None:
        """Get a specific story by ID."""
        with Session(engine) as session:
            db_story = session.get(StoryMeta, story_id)
            if not db_story:
                return None
            
            story = StoryMetaResponse.model_validate(db_story)
            if requesting_user_id:
                fav = session.exec(
                    select(UserFavorite).where(
                        UserFavorite.user_id == requesting_user_id,
                        UserFavorite.story_id == story_id
                    )
                ).first()
                story.is_favorite = fav is not None
            return story

    def toggle_favorite(self, user_id: str, story_id: str) -> bool:
        """Toggle favorite status. Returns True if now favorite, False if removed."""
        with Session(engine) as session:
            existing = session.exec(
                select(UserFavorite).where(
                    UserFavorite.user_id == user_id,
                    UserFavorite.story_id == story_id
                )
            ).first()
            
            if existing:
                session.delete(existing)
                session.commit()
                return False
            else:
                fav = UserFavorite(user_id=user_id, story_id=story_id)
                session.add(fav)
                session.commit()
                return True
                
    def get_favorites(self, user_id: str) -> list[StoryMetaResponse]:
        """Get all favorited stories for a user."""
        with Session(engine) as session:
            statement = select(StoryMeta).join(UserFavorite).where(UserFavorite.user_id == user_id).order_by(UserFavorite.created_at.desc())
            results = session.exec(statement).all()
            stories = [StoryMetaResponse.model_validate(s) for s in results]
            for s in stories:
                s.is_favorite = True
            return stories

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

    # ──────────────────────────────────
    # Playlist Management
    # ──────────────────────────────────

    def get_playlist(self, user_id: str) -> list[StoryMetaResponse]:
        """Get the ordered playlist for a user."""
        with Session(engine) as session:
            statement = select(StoryMeta).join(PlaylistEntry).where(
                PlaylistEntry.user_id == user_id
            ).order_by(PlaylistEntry.position.asc())
            results = session.exec(statement).all()
            return [StoryMetaResponse.model_validate(s) for s in results]

    def add_to_playlist(self, user_id: str, story_id: str) -> bool:
        """Add a story to the end of the user's playlist if eligible."""
        with Session(engine) as session:
            # 1. Eligibility Check: Story must exist, be done, and have audio
            story = session.get(StoryMeta, story_id)
            if not story or story.status != "done" or story.voice_key == "none":
                logger.warning(f"Playlist Reject: Story {story_id} not eligible.")
                return False

            # 2. Duplicate Check: Only once in playlist
            existing = session.exec(select(PlaylistEntry).where(
                PlaylistEntry.user_id == user_id, 
                PlaylistEntry.story_id == story_id
            )).first()
            if existing:
                return True # Already there

            # 3. Find next position
            max_pos = session.exec(select(PlaylistEntry.position).where(
                PlaylistEntry.user_id == user_id
            ).order_by(PlaylistEntry.position.desc())).first()
            next_pos = (max_pos + 1) if max_pos is not None else 0

            # 4. Add
            entry = PlaylistEntry(user_id=user_id, story_id=story_id, position=next_pos)
            session.add(entry)
            session.commit()
            return True

    def remove_from_playlist(self, user_id: str, story_id: str) -> bool:
        """Remove a story and re-index positions."""
        with Session(engine) as session:
            entry = session.exec(select(PlaylistEntry).where(
                PlaylistEntry.user_id == user_id, 
                PlaylistEntry.story_id == story_id
            )).first()
            
            if not entry:
                return False
                
            session.delete(entry)
            session.commit()
            
            # Re-index
            others = session.exec(select(PlaylistEntry).where(
                PlaylistEntry.user_id == user_id
            ).order_by(PlaylistEntry.position.asc())).all()
            
            for i, other in enumerate(others):
                other.position = i
                session.add(other)
            session.commit()
            return True

    def clear_playlist(self, user_id: str):
        """Delete all entries for a user."""
        with Session(engine) as session:
            session.exec(delete(PlaylistEntry).where(PlaylistEntry.user_id == user_id))
            session.commit()

    # ──────────────────────────────────
    # System Settings Management
    # ──────────────────────────────────

    def get_system_setting(self, key: str, default: str) -> str:
        """Fetch a system-wide configuration value from the DB."""
        with Session(engine) as session:
            setting = session.get(SystemSetting, key)
            if setting:
                return setting.value
        return default

    def set_system_setting(self, key: str, value: str):
        """Update or create a system setting."""
        from datetime import timezone
        with Session(engine) as session:
            setting = session.get(SystemSetting, key)
            if setting:
                setting.value = value
                setting.updated_at = datetime.now(timezone.utc)
            else:
                setting = SystemSetting(key=key, value=value, updated_at=datetime.now(timezone.utc))
            session.add(setting)
            session.commit()

    def get_all_settings(self) -> list[SystemSetting]:
        """List all system settings."""
        with Session(engine) as session:
            return list(session.exec(select(SystemSetting)).all())


    def get_or_create_whatsapp_user(self, phone: str) -> User:
        """Finds or creates a user for a WhatsApp phone number. Prioritizes linked profiles."""
        # Normalize: remove 'whatsapp:', '+', and spaces
        clean_phone = phone.replace("whatsapp:", "").replace("+", "").replace(" ", "").strip()
        
        with Session(engine) as session:
            # 1. First check if any user has linked this phone number in their profile
            # We use a LIKE or manual check to be safe against leading pluses in DB
            user = session.exec(select(User).where(
                (User.whatsapp_phone == clean_phone) | 
                (User.whatsapp_phone == f"+{clean_phone}")
            )).first()
            
            if user:
                return user
                
            # 2. Then check for an existing shadow user by the specialized WhatsApp email
            email = f"{clean_phone}@whatsapp.storyja.com".lower()
            user = session.exec(select(User).where(User.email == email)).first()
            if user:
                return user
            
            # 3. Create new shadow user if no existing account found
            new_user = User(
                id=f"wa-{str(uuid.uuid4())[:8]}",
                email=email,
                hashed_password="WHATSAPP_SHADOW_USER", # No password login possible
                username=f"WhatsApp ({clean_phone})"
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            logger.info(f"Created new shadow user for WhatsApp: {email}")
            return new_user

    def link_whatsapp_phone(self, user_id: str, phone: str) -> dict:
        """Links a phone number to a user and migrates stories from shadow user."""
        clean_phone = phone.replace("whatsapp:", "").replace("+", "").replace(" ", "").strip()
        shadow_email = f"{clean_phone}@whatsapp.storyja.com".lower()
        
        with Session(engine) as session:
            # 1. Check if phone is already used
            existing = session.exec(select(User).where(
                (User.whatsapp_phone == clean_phone) | 
                (User.whatsapp_phone == f"+{clean_phone}")
            )).first()
            
            if existing and existing.id != user_id:
                return {"status": "error", "message": "Nummer bereits verknüpft"}
                
            user = session.get(User, user_id)
            if not user:
                return {"status": "error", "message": "Nutzer nicht gefunden"}
                
            user.whatsapp_phone = clean_phone
            session.add(user)
            
            # 2. Check for shadow user
            shadow = session.exec(select(User).where(User.email == shadow_email)).first()
            migrated_count = 0
            if shadow:
                from app.models import StoryMeta
                stories = session.exec(select(StoryMeta).where(StoryMeta.user_id == shadow.id)).all()
                for s in stories:
                    s.user_id = user.id
                    session.add(s)
                migrated_count = len(stories)
                session.delete(shadow)
                
            session.commit()
            return {
                "status": "success", 
                "migrated": migrated_count > 0,
                "count": migrated_count
            }


# Singleton instance
store = StoryStore()
