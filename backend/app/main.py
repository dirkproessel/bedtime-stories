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

# Deploy Trigger: Live Feed Generation v1.2.1
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.config import settings

# Log file for remote debugging (cross-worker)
DEBUG_LOG_PATH = settings.AUDIO_OUTPUT_DIR / "debug.log"

class LogFileHandler(logging.Handler):
    def emit(self, record):
        try:
            with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")
        except:
            pass

log_handler = LogFileHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(log_handler)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel


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
_generation_status: dict[str, dict] = {}


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
            prompt=req.system_prompt or req.prompt, # Use system_prompt for generation if available, else fallback
            genre=req.genre,
            style=req.style,
            characters=req.characters,
            target_minutes=req.target_minutes,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
            original_prompt=req.prompt, # Pass original prompt for metadata
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
            genre="Realismus",
            style="Douglas Adams",
            characters=None,
            target_minutes=req.target_minutes,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
            original_prompt=req.text,
        )
    )

    return {"id": story_id, "status": "started"}


async def _run_pipeline(
    story_id: str,
    prompt: str,
    genre: str,
    style: str,
    characters: list[str] | None,
    target_minutes: int,
    voice_key: str,
    speech_rate: str,
    original_prompt: str | None = None,
):
    """Full pipeline: text → TTS → merge → save."""
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    # Resolve voice name
    voice_name = "Unbekannt"
    all_voices = get_available_voices()
    for v in all_voices:
        if v["key"] == voice_key:
            voice_name = v["name"]
            break

    # Initial record creation
    story_meta = StoryMeta(
        id=story_id,
        title=f"Schreibe '{style}'-Geschichte ({target_minutes} Min)...",
        description=f"Idee: {(original_prompt or prompt)[:100]}...",
        prompt=original_prompt or prompt,
        genre=genre,
        style=style,
        voice_key=voice_key,
        voice_name=voice_name,
        duration_seconds=0,
        chapter_count=0,
        is_on_spotify=False,
        status="generating",
        progress="Starte Generierung...",
        created_at=datetime.now(timezone.utc),
    )
    store.add_story(story_meta)

    async def on_progress(status_type: str, message: str, pct: int | None = None):
        _generation_status[story_id]["status"] = status_type
        _generation_status[story_id]["progress"] = message
        if pct is not None:
            _generation_status[story_id]["progress_pct"] = pct
        
        # Also update persistent store
        curr = store.get_by_id(story_id)
        if curr:
            curr.status = "generating" if status_type != "done" and status_type != "error" else status_type
            curr.progress = message
            if pct is not None:
                curr.progress_pct = pct
            store.add_story(curr)

    try:
        # Step 1: Generate story text (Single-pass)
        story_data = await generate_full_story(
            prompt=prompt,
            genre=genre,
            style=style,
            characters=characters,
            target_minutes=target_minutes,
            on_progress=on_progress,
        )

        _generation_status[story_id]["title"] = story_data["title"]
        
        # Update title in store
        curr = store.get_by_id(story_id)
        if curr:
            curr.title = story_data["title"]
            curr.description = story_data.get("synopsis", curr.description)
            store.add_story(curr)

        # Save text
        text_path = story_dir / "story.json"
        text_path.write_text(
            json.dumps(story_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Step 2: TTS – chapters to audio
        await on_progress("generating_audio", "Bereite Vertonung vor...", 30)
        chunks_dir = story_dir / "chunks"
        audio_files = await chapters_to_audio(
            chapters=story_data["chapters"],
            output_dir=chunks_dir,
            voice_key=voice_key,
            rate=speech_rate,
            on_progress=on_progress,
        )

        # Step 2.5: Generate title audio
        await on_progress("generating_audio", "Vertone Titel...", 80)
        title_tts_path = chunks_dir / "title.mp3"
        await generate_tts_chunk(
            text=story_data["title"],
            output_path=title_tts_path,
            voice_key=voice_key,
            rate=speech_rate
        )

        # Step 4: Merge and Post-process
        await on_progress("processing", "Mische Audio-Spuren und optimiere Klang...", 85)
        final_audio_path = story_dir / "story.mp3"
        await merge_audio_files(
            audio_files=audio_files,
            output_path=final_audio_path,
            intro_path=settings.INTRO_MUSIC_PATH,
            outro_path=settings.OUTRO_MUSIC_PATH,
            title_path=title_tts_path,
        )

        # Step 5: Get Final Duration
        duration = await get_audio_duration(final_audio_path)

        # Step 3.5: Generate story image
        await on_progress("processing", "Generiere Titelbild...", 95)
        image_path = story_dir / "cover.png"
        image_url = None
        try:
            res = await generate_story_image(story_data.get("synopsis", ""), image_path, genre=genre, style=style)
            if res:
                image_url = f"{settings.BASE_URL}/api/stories/{story_id}/image.png"
                logger.info(f"Image generated successfully for {story_id}: {image_url}")
            else:
                logger.warning(f"Image generation returned None for {story_id}")
        except Exception as e:
            logger.error(f"Failed to call generate_story_image for {story_id}: {e}", exc_info=True)

        # Calculate word count
        total_text = "\n".join([c["text"] for c in story_data["chapters"]])
        word_count = len(total_text.split())

        # Step 4: Finalize metadata
        story_meta = store.get_by_id(story_id)
        if story_meta:
            story_meta.title = story_data["title"]
            story_meta.description = story_data.get("synopsis", story_meta.description)
            story_meta.duration_seconds = duration
            story_meta.chapter_count = len(story_data["chapters"])
            story_meta.word_count = word_count
            story_meta.image_url = image_url
            story_meta.voice_name = voice_name
            story_meta.status = "done"
            story_meta.progress = "Fertig! Geschichte bereit zum Anhören."
            story_meta.progress_pct = 100
            store.add_story(story_meta)

    except Exception as e:
        _generation_status[story_id]["status"] = "error"
        _generation_status[story_id]["progress"] = f"Fehler: {str(e)}"
        
        curr = store.get_by_id(story_id)
        if curr:
            curr.status = "error"
            curr.progress = f"Fehler: {str(e)}"
            store.add_story(curr)
            
        logger.error(f"Generation error for {story_id}: {e}", exc_info=True)


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
    
    logger.info(f"Generating RSS feed with {len(stories)} stories. IDs: {[s.id for s in stories]}")
    
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
# Health & Debug
# ──────────────────────────────────

@app.get("/api/health")
async def health():
    import os
    logger.info("Health check ping - testing log buffer")
    return {
        "status": "ok", 
        "version": "1.4.0",
        "build": "pivot-001",
        "worker_pid": os.getpid(),
        "store_path": str(store.db_path.absolute()),
        "store_exists": store.db_path.exists()
    }


@app.get("/api/debug/store")
async def debug_store():
    """Debug endpoint to inspect the store contents."""
    stories = store.get_all()
    return {
        "count": len(stories),
        "stories": [s.model_dump(mode="json") for s in stories]
    }


@app.get("/api/debug/logs")
async def get_debug_logs():
    """Return the last 100 log lines from the shared file."""
    if not DEBUG_LOG_PATH.exists():
        return {"logs": []}
    
    try:
        lines = DEBUG_LOG_PATH.read_text(encoding="utf-8").splitlines()
        return {"logs": lines[-100:]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {e}"]}
