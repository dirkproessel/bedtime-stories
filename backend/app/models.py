"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

# --- DB Models (SQLModel) ---

class User(SQLModel, table=True):
    """User representation for database."""
    id: Optional[str] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    username: Optional[str] = Field(default=None)
    kindle_email: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    alexa_user_id: Optional[str] = Field(default=None, unique=True, index=True)
    custom_voice_id: Optional[str] = Field(default=None)
    custom_voice_name: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    custom_voices: list["UserVoice"] = Relationship()

class UserVoice(SQLModel, table=True):
    """Custom cloned voices for a user."""
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    fish_voice_id: str = Field(index=True)
    name: str = Field(default="My Voice")
    is_public: bool = Field(default=False)
    gender: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SystemVoice(SQLModel, table=True):
    """System-wide predefined voices (Edge, Gemini, etc)."""
    id: str = Field(primary_key=True)
    name: str
    engine: str  # "edge", "gemini", "fish", "openai"
    gender: str  # "male", "female", "neutral"
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    fish_voice_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserFavorite(SQLModel, table=True):
    """Many-to-many relationship for favorites."""
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    story_id: str = Field(foreign_key="storymeta.id", primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlaylistEntry(SQLModel, table=True):
    """Sequential queue for Alexa playback."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    story_id: str = Field(foreign_key="storymeta.id", index=True)
    position: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SystemSetting(SQLModel, table=True):
    """Global system-wide settings stored in database."""
    key: str = Field(primary_key=True)
    value: str
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StoryMeta(SQLModel, table=True):
    """Story Metadata stored in database."""
    id: str = Field(primary_key=True)
    title: str
    description: str
    prompt: str
    genre: Optional[str] = Field(default=None)
    style: str
    voice_key: str
    voice_name: Optional[str] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    chapter_count: int
    word_count: Optional[int] = Field(default=None)
    is_on_spotify: bool = Field(default=False)
    image_url: Optional[str] = Field(default=None)
    status: str = Field(default="done")  # "generating", "done", "error"
    progress: Optional[str] = Field(default=None)
    progress_pct: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Multi-User & Remix Features
    user_id: Optional[str] = Field(default=None, foreign_key="user.id")
    is_public: bool = Field(default=False)
    user_email: Optional[str] = Field(default=None) # Persistent for display cache
    parent_id: Optional[str] = Field(default=None) # Reference to original story
    highlights: Optional[str] = Field(default=None) # AI-extracted punchlines/highlights

class StoryMetaResponse(StoryMeta):
    """Story Metadata including transient API fields."""
    is_favorite: bool = False


# --- API Request Options Models ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    is_admin: bool = Field(default=False)
    username: Optional[str] = None
    kindle_email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    story_count: int = 0
    alexa_user_id: Optional[str] = None
    custom_voice_id: Optional[str] = None # Deprecated, keep for backward compat
    custom_voice_name: Optional[str] = None # Deprecated, keep for backward compat
    custom_voices: list["UserVoiceResponse"] = []

class UserVoiceResponse(BaseModel):
    id: str
    user_id: str
    fish_voice_id: str
    name: str
    is_public: bool
    gender: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class KindleEmailUpdate(BaseModel):
    kindle_email: str | None

class UsernameUpdate(BaseModel):
    username: str

class VoiceNameUpdate(BaseModel):
    voice_name: str

class StoryRequest(BaseModel):
    """Request to generate a new story."""
    prompt: str  # The raw user idea
    system_prompt: str | None = None  # Optional full formatted prompt
    genre: str = "Realismus"
    style: str = "Douglas Adams"
    characters: list[str] | None = None
    target_minutes: int = 5
    voice_key: str = "seraphina"
    speech_rate: str = "0%"
    
    # Remix Features
    parent_id: Optional[str] = None
    remix_type: Optional[str] = None # "improvement" | "sequel"
    further_instructions: Optional[str] = None

class FreeTextRequest(BaseModel):
    """Free text prompt for story generation."""
    text: str
    voice_key: str = "seraphina"
    target_minutes: int = 20
    speech_rate: str = "0%"

class HookRequest(BaseModel):
    """Request to generate a hook idea via the dice feature."""
    genre: str
    author_id: str
    user_input: Optional[str] = None

class KindleExportRequest(BaseModel):
    """Request to export a story to Kindle via email."""
    email: str

class StoryUpdate(BaseModel):
    """Request to update story visibility/metadata."""
    is_public: Optional[bool] = None
    title: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[str] = None
    chapters: Optional[list[dict]] = None

# --- API Response Models ---

class HookResponse(BaseModel):
    hook_text: str

class VoiceProfile(BaseModel):
    key: str
    name: str
    gender: str
    engine: str
    description: str | None = None
    accent: str | None = "DE"
    style: str | None = "Standard"

class StoryOutline(BaseModel):
    title: str
    chapters: list[dict]

class StoryStatus(BaseModel):
    id: str
    status: str  # "generating_text" | "generating_audio" | "processing" | "done" | "error"
    progress: str  # Human-readable progress message
    progress_pct: int = 0
    title: str | None = None

class StoryListResponse(BaseModel):
    stories: list[StoryMetaResponse]
    total: int
    total_my: int = 0
    total_public: int = 0
    available_genres: list[str] = []

class SystemSettingResponse(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime

class SystemSettingUpdate(BaseModel):
    value: str

