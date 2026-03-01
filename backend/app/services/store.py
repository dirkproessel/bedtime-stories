"""
Persistent storage service for bedtime stories.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from app.models import StoryMeta
from app.config import settings

logger = logging.getLogger(__name__)

class StoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._stories: dict[str, StoryMeta] = {}
        self._load()

    def _load(self):
        """Load stories from disk."""
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text(encoding="utf-8"))
                for story_id, story_data in data.items():
                    # Handle legacy date strings and missing fields via Pydantic
                    self._stories[story_id] = StoryMeta(**story_data)
                logger.info(f"Loaded {len(self._stories)} stories from {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to load stories: {e}")
                self._stories = {}
        else:
            logger.info("No stories database found, starting fresh.")

    def save(self):
        """Persist stories to disk."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            # Serialize using Pydantic's dict() / json()
            data = {
                story_id: story.model_dump(mode="json")
                for story_id, story in self._stories.items()
            }
            self.db_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save stories: {e}")

    def get_all(self, only_spotify: bool = False) -> list[StoryMeta]:
        """Get all stories, sorted by creation date (newest first)."""
        stories = list(self._stories.values())
        if only_spotify:
            stories = [s for s in stories if s.is_on_spotify]
        
        return sorted(stories, key=lambda s: s.created_at, reverse=True)

    def get_by_id(self, story_id: str) -> StoryMeta | None:
        """Get a specific story by ID."""
        return self._stories.get(story_id)

    def add_story(self, story: StoryMeta):
        """Add or update a story."""
        self._stories[story.id] = story
        self.save()

    def update_spotify_status(self, story_id: str, enabled: bool) -> bool:
        """Toggle Spotify status for a story."""
        if story_id in self._stories:
            self._stories[story_id].is_on_spotify = enabled
            self.save()
            return True
        return False

    def delete_story(self, story_id: str) -> bool:
        """Remove a story from the database."""
        if story_id in self._stories:
            del self._stories[story_id]
            self.save()
            return True
        return False

# Singleton instance
store = StoryStore(settings.AUDIO_OUTPUT_DIR / "stories.json")
