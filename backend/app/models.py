"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from datetime import datetime


# --- Request Models ---

class StoryRequest(BaseModel):
    """Request to generate a new story."""
    prompt: str  # The raw user idea
    system_prompt: str | None = None  # Optional full formatted prompt
    genre: str = "Realismus"
    style: str = "Douglas Adams"
    characters: list[str] | None = None
    target_minutes: int = 5
    voice_key: str = "seraphina"
    speech_rate: str = "-5%"


class FreeTextRequest(BaseModel):
    """Free text prompt for story generation."""
    text: str
    voice_key: str = "seraphina"
    target_minutes: int = 20
    speech_rate: str = "-5%"


# --- Response Models ---

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
    title: str | None = None


class StoryMeta(BaseModel):
    id: str
    title: str
    description: str
    prompt: str
    genre: str | None = None
    style: str
    voice_key: str
    voice_name: str | None = None
    duration_seconds: float | None = None
    chapter_count: int
    is_on_spotify: bool = False
    image_url: str | None = None
    status: str = "done"  # "generating", "done", "error"
    progress: str | None = None
    created_at: datetime


class StoryListResponse(BaseModel):
    stories: list[StoryMeta]
    total: int
