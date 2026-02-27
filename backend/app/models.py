"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from datetime import datetime


# --- Request Models ---

class StoryRequest(BaseModel):
    """Request to generate a new story."""
    prompt: str
    style: str = "märchenhaft"
    characters: list[str] | None = None
    target_minutes: int = 20
    voice_key: str = "katja"
    speech_rate: str = "-5%"


class FreeTextRequest(BaseModel):
    """Free text prompt for story generation."""
    text: str
    voice_key: str = "katja"
    target_minutes: int = 20
    speech_rate: str = "-5%"


# --- Response Models ---

class VoiceProfile(BaseModel):
    key: str
    name: str
    gender: str
    engine: str


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
    style: str
    voice_key: str
    duration_seconds: float | None = None
    chapter_count: int
    created_at: datetime


class StoryListResponse(BaseModel):
    stories: list[StoryMeta]
    total: int
