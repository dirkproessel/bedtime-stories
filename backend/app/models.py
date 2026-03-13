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
    kindle_email: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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
    
    # Multi-User & Remix Features
    user_id: Optional[str] = Field(default=None, foreign_key="user.id")
    is_public: bool = Field(default=False)
    user_email: Optional[str] = Field(default=None) # Persistent for display cache
    parent_id: Optional[str] = Field(default=None) # Reference to original story


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
    is_admin: bool
    kindle_email: Optional[str] = None
    created_at: datetime

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class KindleEmailUpdate(BaseModel):
    kindle_email: str | None

class StoryRequest(BaseModel):
    """Request to generate a new story."""
    prompt: str  # The raw user idea
    system_prompt: str | None = None  # Optional full formatted prompt
    genre: str = "Realismus"
    style: str = "Douglas Adams"
    characters: list[str] | None = None
    target_minutes: int = 5
    voice_key: str = "seraphina"
    speech_rate: str = "-15%"
    
    # Remix Features
    parent_id: Optional[str] = None
    remix_type: Optional[str] = None # "improvement" | "sequel"
    further_instructions: Optional[str] = None

class FreeTextRequest(BaseModel):
    """Free text prompt for story generation."""
    text: str
    voice_key: str = "seraphina"
    target_minutes: int = 20
    speech_rate: str = "-15%"

class HookRequest(BaseModel):
    """Request to generate a hook idea via the dice feature."""
    genre: str
    author_id: str

class KindleExportRequest(BaseModel):
    """Request to export a story to Kindle via email."""
    email: str

class StoryUpdate(BaseModel):
    """Request to update story visibility/metadata."""
    is_public: Optional[bool] = None
    title: Optional[str] = None

# --- API Response Models ---

class HookResponse(BaseModel):
    hook_text: str

class VoiceProfile(BaseModel):
    key: str
    name: str
    gender: str
    engine: str
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
    stories: list[StoryMeta]
    total: int
    total_my: int = 0
    total_public: int = 0

