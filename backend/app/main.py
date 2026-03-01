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
from pydantic import BaseModel

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
    generate_tts_chunk,
)
from app.services.audio_processor import merge_audio_files, get_audio_duration
from app.services.rss_generator import generate_rss_feed
from app.services.image_generator import generate_story_image

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


from app.services.store import store


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

        # Step 2.5: Generate title audio
        await on_progress("generating_audio", "Vertone Titel...")
        title_path = chunks_dir / "title.mp3"
        await generate_tts_chunk(
            text=story_data["title"],
            output_path=title_path,
            voice_key=voice_key,
            rate=speech_rate
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
            title_path=title_path,
        )

        # Get duration
        duration = get_audio_duration(final_path)

        # Step 3.5: Generate story image
        await on_progress("processing", "Generiere Titelbild...")
        image_path = story_dir / "cover.png"
        image_url = None
        if await generate_story_image(story_data["synopsis"], image_path):
            image_url = f"{settings.BASE_URL}/api/stories/{story_id}/image.png"

        # Step 4: Save metadata
        story_meta = StoryMeta(
            id=story_id,
            title=story_data["title"],
            description=story_data.get("synopsis", f"Geschichte: {prompt}"),
            prompt=prompt,
            style=style,
            voice_key=voice_key,
            duration_seconds=duration,
            chapter_count=len(story_data["chapters"]),
            image_url=image_url,
            is_on_spotify=False,
            created_at=datetime.now(timezone.utc),
        )

        store.add_story(story_meta)

        await on_progress("done", "Fertig! Geschichte bereit zum Anhören.")

    except Exception as e:
        _generation_status[story_id]["status"] = "error"
        _generation_status[story_id]["progress"] = f"Fehler: {str(e)}"
        logger.error(f"Generation error: {e}", exc_info=True)


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
    stories = store.get_all()
    return StoryListResponse(stories=stories, total=len(stories))


@app.get("/api/stories/{story_id}")
async def get_story(story_id: str):
    """Get story details including chapter text."""
    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Story not found")

    # Load full text if available
    text_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.json"
    chapters = []
    if text_path.exists():
        story_data = json.loads(text_path.read_text(encoding="utf-8"))
        chapters = story_data.get("chapters", [])

    return {**meta.model_dump(), "chapters": chapters}


@app.get("/api/stories/{story_id}/audio")
async def get_audio(story_id: str):
    """Stream the final MP3 audio file."""
    audio_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    meta = store.get_by_id(story_id)
    filename = f"{meta.title if meta else story_id}.mp3"

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )


@app.delete("/api/stories/{story_id}")
async def delete_story(story_id: str):
    """Delete a story and its files."""
    if not store.delete_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")

    import shutil
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    if story_dir.exists():
        shutil.rmtree(story_dir)

    return {"status": "deleted"}


@app.get("/api/stories/{story_id}/image.png")
async def get_story_image(story_id: str):
    """Serve the story cover image."""
    image_path = settings.AUDIO_OUTPUT_DIR / story_id / "cover.png"
    if not image_path.exists():
        # Fallback to podcast cover if story image is missing
        image_path = Path(__file__).parent / "static" / "podcast-cover.png"
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
        
    return FileResponse(image_path, media_type="image/png")


class SpotifyToggleRequest(BaseModel):
    enabled: bool


@app.post("/api/stories/{story_id}/spotify")
async def toggle_spotify(story_id: str, body: SpotifyToggleRequest):
    """Toggle whether a story is included in the Spotify RSS feed."""
    if not store.update_spotify_status(story_id, body.enabled):
        raise HTTPException(status_code=404, detail="Story not found")
    
    return {"id": story_id, "is_on_spotify": body.enabled}


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
    """Serve the podcast RSS feed (generated dynamically)."""
    # Only include stories that have is_on_spotify=True
    stories = store.get_all(only_spotify=True)
    
    image_url = f"{settings.BASE_URL}/api/podcast-cover.png"
    email = "dirk@proessel.de"  # Required by Spotify
    
    try:
        xml_content = generate_rss_feed(
            stories,
            settings.BASE_URL,
            image_url=image_url,
            email=email,
        )
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"RSS generation error: {e}")
        return Response(content="<rss><channel><title>Error</title></channel></rss>", media_type="application/xml")


# ──────────────────────────────────
# Health
# ──────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.1.0"}
