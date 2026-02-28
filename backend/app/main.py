"""
Bedtime Stories API – FastAPI Application

Endpoints:
  POST /api/stories/generate     – Start story generation
  GET  /api/stories              – List all stories
  GET  /api/stories/{id}         – Get story details
  GET  /api/stories/{id}/audio   – Stream audio file
  GET  /api/voices               – List available voice profiles
  GET  /api/voices/{key}/preview – Preview a voice
  GET  /api/feed.xml             – Podcast RSS feed
  GET  /api/status/{id}          – Generation status (SSE)
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response

from app.config import settings
from app.models import (
    StoryRequest,
    FreeTextRequest,
    StoryMeta,
    StoryListResponse,
    VoiceProfile,
)
from app.services.story_generator import generate_full_story
from app.services.tts_service import (
    chapters_to_audio,
    get_available_voices,
    generate_voice_preview,
)
from app.services.audio_processor import merge_audio_files, get_audio_duration
from app.services.rss_generator import generate_rss_feed

app = FastAPI(title="Bedtime Stories API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for generation status & story metadata
# In production this would be PocketBase, but this works standalone too
_generation_status: dict[str, dict] = {}
_stories_db: dict[str, dict] = {}
_stories_db_path = settings.AUDIO_OUTPUT_DIR / "stories.json"


def _load_stories():
    """Load stories from JSON file on disk."""
    global _stories_db
    if _stories_db_path.exists():
        _stories_db = json.loads(_stories_db_path.read_text(encoding="utf-8"))


def _save_stories():
    """Persist stories to JSON file."""
    _stories_db_path.parent.mkdir(parents=True, exist_ok=True)
    _stories_db_path.write_text(
        json.dumps(_stories_db, default=str, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# Load on startup
_load_stories()


# ──────────────────────────────────
# Voices
# ──────────────────────────────────

@app.get("/api/voices", response_model=list[VoiceProfile])
async def list_voices():
    """List all available voice profiles."""
    return get_available_voices()


@app.get("/api/voices/{voice_key}/preview")
async def preview_voice(voice_key: str):
    """Generate and return a voice preview clip."""
    preview_dir = settings.AUDIO_OUTPUT_DIR / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{voice_key}.mp3"

    # Regenerate if missing or empty (0 bytes)
    if not preview_path.exists() or preview_path.stat().st_size == 0:
        try:
            await generate_voice_preview(voice_key, preview_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"TTS Error: {e}")

    return FileResponse(preview_path, media_type="audio/mpeg")


# ──────────────────────────────────
# Story Generation
# ──────────────────────────────────

@app.post("/api/stories/generate")
async def start_generation(req: StoryRequest):
    """Start async story generation. Returns story ID to poll status."""
    story_id = str(uuid.uuid4())[:8]

    _generation_status[story_id] = {
        "status": "starting",
        "progress": "Starte Generierung...",
        "title": None,
    }

    # Run generation in background
    asyncio.create_task(
        _run_pipeline(
            story_id=story_id,
            prompt=req.prompt,
            style=req.style,
            characters=req.characters,
            target_minutes=req.target_minutes,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
        )
    )

    return {"id": story_id, "status": "started"}


@app.post("/api/stories/generate-free")
async def start_free_generation(req: FreeTextRequest):
    """Start generation from free text prompt."""
    story_id = str(uuid.uuid4())[:8]

    _generation_status[story_id] = {
        "status": "starting",
        "progress": "Starte Generierung...",
        "title": None,
    }

    asyncio.create_task(
        _run_pipeline(
            story_id=story_id,
            prompt=req.text,
            style="frei",
            characters=None,
            target_minutes=req.target_minutes,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
        )
    )

    return {"id": story_id, "status": "started"}


async def _run_pipeline(
    story_id: str,
    prompt: str,
    style: str,
    characters: list[str] | None,
    target_minutes: int,
    voice_key: str,
    speech_rate: str,
):
    """Full pipeline: text → TTS → merge → save."""
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    async def on_progress(status_type: str, message: str):
        _generation_status[story_id]["status"] = status_type
        _generation_status[story_id]["progress"] = message

    try:
        # Step 1: Generate story text
        await on_progress("generating_text", "Generiere Gliederung...")
        story_data = await generate_full_story(
            prompt=prompt,
            style=style,
            characters=characters,
            target_minutes=target_minutes,
            on_progress=on_progress,
        )

        _generation_status[story_id]["title"] = story_data["title"]

        # Save text
        text_path = story_dir / "story.json"
        text_path.write_text(
            json.dumps(story_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Step 2: TTS – chapters to audio
        await on_progress("generating_audio", "Starte Vertonung...")
        chunks_dir = story_dir / "chunks"
        audio_files = await chapters_to_audio(
            chapters=story_data["chapters"],
            output_dir=chunks_dir,
            voice_key=voice_key,
            rate=speech_rate,
            on_progress=on_progress,
        )

        # Step 3: Merge & normalize
        await on_progress("processing", "Zusammenfügen & Normalisieren...")
        final_path = story_dir / "story.mp3"
        
        # Check for intro/outro in static dir
        static_dir = Path(__file__).parent / "static"
        intro_path = static_dir / "Intro.mp3"
        outro_path = static_dir / "Outro.mp3"
        
        merge_audio_files(
            audio_files, 
            final_path,
            intro_path=intro_path if intro_path.exists() else None,
            outro_path=outro_path if outro_path.exists() else None,
        )

        # Get duration
        duration = get_audio_duration(final_path)

        # Step 4: Save metadata
        story_meta = {
            "id": story_id,
            "title": story_data["title"],
            "description": story_data.get("synopsis", f"Geschichte: {prompt}"),
            "prompt": prompt,
            "style": style,
            "voice_key": voice_key,
            "duration_seconds": duration,
            "chapter_count": len(story_data["chapters"]),
            "filename": "story.mp3",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        _stories_db[story_id] = story_meta
        _save_stories()

        # Update RSS feed
        _regenerate_rss()

        await on_progress("done", "Fertig! Geschichte bereit zum Anhören.")

    except Exception as e:
        _generation_status[story_id]["status"] = "error"
        _generation_status[story_id]["progress"] = f"Fehler: {str(e)}"
        raise


# ──────────────────────────────────
# Status (Polling)
# ──────────────────────────────────

@app.get("/api/status/{story_id}")
async def get_status(story_id: str):
    """Get current generation status."""
    status = _generation_status.get(story_id)
    if not status:
        raise HTTPException(status_code=404, detail="Story not found")
    return {
        "id": story_id,
        **status,
    }


# ──────────────────────────────────
# Stories CRUD
# ──────────────────────────────────

@app.get("/api/stories", response_model=StoryListResponse)
async def list_stories():
    """List all generated stories."""
    stories = sorted(
        _stories_db.values(),
        key=lambda s: s["created_at"],
        reverse=True,
    )
    return StoryListResponse(stories=stories, total=len(stories))


@app.get("/api/stories/{story_id}")
async def get_story(story_id: str):
    """Get story details including chapter text."""
    if story_id not in _stories_db:
        raise HTTPException(status_code=404, detail="Story not found")

    meta = _stories_db[story_id]

    # Load full text if available
    text_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.json"
    chapters = []
    if text_path.exists():
        story_data = json.loads(text_path.read_text(encoding="utf-8"))
        chapters = story_data.get("chapters", [])

    return {**meta, "chapters": chapters}


@app.get("/api/stories/{story_id}/audio")
async def get_audio(story_id: str):
    """Stream the final MP3 audio file."""
    audio_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=f"{_stories_db.get(story_id, {}).get('title', story_id)}.mp3",
    )


@app.delete("/api/stories/{story_id}")
async def delete_story(story_id: str):
    """Delete a story and its files."""
    if story_id not in _stories_db:
        raise HTTPException(status_code=404, detail="Story not found")

    import shutil
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    if story_dir.exists():
        shutil.rmtree(story_dir)

    del _stories_db[story_id]
    _save_stories()
    _regenerate_rss()

    return {"status": "deleted"}


# ──────────────────────────────────
# RSS Feed
# ──────────────────────────────────

@app.get("/api/podcast-cover.png")
async def get_podcast_cover():
    """Serve the podcast cover art."""
    cover_path = Path(__file__).parent / "static" / "podcast-cover.png"
    if not cover_path.exists():
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(cover_path, media_type="image/png")


@app.get("/api/feed.xml")
async def get_rss_feed():
    """Serve the podcast RSS feed."""
    rss_path = settings.AUDIO_OUTPUT_DIR / "feed.xml"
    if not rss_path.exists():
        _regenerate_rss()

    if rss_path.exists():
        return Response(
            content=rss_path.read_text(encoding="utf-8"),
            media_type="application/xml",
        )
    return Response(content="<rss></rss>", media_type="application/xml")


def _regenerate_rss():
    """Regenerate the RSS feed from current stories."""
    stories = list(_stories_db.values())
    rss_path = settings.AUDIO_OUTPUT_DIR / "feed.xml"
    image_url = f"{settings.BASE_URL}/api/podcast-cover.png"
    email = "dirk@proessel.de"  # Required by Spotify
    try:
        generate_rss_feed(
            stories,
            settings.BASE_URL,
            rss_path,
            image_url=image_url,
            email=email,
        )
    except Exception:
        pass  # Non-critical


# ──────────────────────────────────
# Health
# ──────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

# ──────────────────────────────────
# Startup
# ──────────────────────────────────

# Force RSS regeneration on startup to update metadata/cover
try:
    rss_path = settings.AUDIO_OUTPUT_DIR / "feed.xml"
    if rss_path.exists():
        rss_path.unlink()
    _regenerate_rss()
except Exception as e:
    logger.error(f"Failed to force RSS regeneration on startup: {e}")
