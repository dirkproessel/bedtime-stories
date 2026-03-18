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
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.config import settings

# Log file for remote debugging (cross-worker)
DEBUG_LOG_PATH = settings.AUDIO_OUTPUT_DIR / "debug.log"

# Diagnostic for Image Generation
if settings.GEMINI_API_KEY:
    masked_key = settings.GEMINI_API_KEY[:4] + "..." + settings.GEMINI_API_KEY[-4:]
    logging.info(f"GEMINI_API_KEY detected: {masked_key}")
else:
    logging.warning("GEMINI_API_KEY NOT detected in environment!")

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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel


from app.models import (
    StoryRequest,
    FreeTextRequest,
    HookRequest,
    HookResponse,
    StoryMeta,
    StoryListResponse,
    VoiceProfile,
    KindleExportRequest,
    User,
    UserResponse,
)
from app.auth_utils import get_current_active_user, get_optional_user
from fastapi import Depends
from app.database import create_db_and_tables
from app.models import StoryUpdate
from app.services.story_generator import generate_full_story, generate_story_hook, get_author_names
from app.services.tts_service import (
    chapters_to_audio,
    get_available_voices,
    generate_voice_preview,
    generate_tts_chunk,
)
from app.services.audio_processor import merge_audio_files, get_audio_duration
from app.services.rss_generator import generate_rss_feed
from app.services.image_generator import generate_story_image
from app.services.kindle_service import generate_epub, send_to_kindle

app = FastAPI(title="Bedtime Stories API", version="1.0.0")

@app.on_event("startup")
def on_startup():
    logger.info("Bedtime Stories API starting up - Running database initialization...")
    create_db_and_tables()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Authentication Router
from app.routers import auth
app.include_router(auth.router)

# In-memory store for generation status & story metadata
_generation_status: dict[str, dict] = {}

from app.services.store import store


async def _generate_thumbnail(source: Path, dest: Path, size: int = 256):
    """Create a small JPEG thumbnail from a full-size cover image."""
    import asyncio
    def _resize():
        from PIL import Image
        with Image.open(source) as img:
            img = img.convert("RGB")
            img.thumbnail((size, size), Image.LANCZOS)
            img.save(dest, "JPEG", quality=80, optimize=True)
    await asyncio.to_thread(_resize)


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
async def start_generation(req: StoryRequest, current_user: User = Depends(get_current_active_user)):
    """Start async story generation. Returns story ID to poll status."""
    story_id = str(uuid.uuid4())[:8]

    _generation_status[story_id] = {
        "status": "starting",
        "progress": "Starte Generierung...",
        "title": None,
    }

    # Fetch parent story context if it's a remix/sequel
    parent_meta = None
    parent_text = None
    if req.parent_id:
        parent_meta = store.get_by_id(req.parent_id)
        if parent_meta:
            text_path = settings.AUDIO_OUTPUT_DIR / req.parent_id / "story.json"
            if text_path.exists():
                try:
                    parent_text = json.loads(text_path.read_text(encoding="utf-8"))
                except:
                    logger.warning(f"Failed to load parent text for {req.parent_id}")

    # Run generation in background
    asyncio.create_task(
        _run_pipeline(
            story_id=story_id,
            prompt=req.system_prompt or req.prompt,
            genre=req.genre,
            style=req.style,
            characters=req.characters,
            target_minutes=req.target_minutes,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
            original_prompt=req.prompt,
            user_id=current_user.id,
            parent_id=req.parent_id,
            remix_type=req.remix_type,
            further_instructions=req.further_instructions,
            parent_meta=parent_meta,
            parent_text=parent_text,
        )
    )

    return {"id": story_id, "status": "started"}


class RevoiceRequest(BaseModel):
    voice_key: str
    speech_rate: str = "-15%"


@app.post("/api/stories/{story_id}/revoice")
async def start_revoice(
    story_id: str, 
    req: RevoiceRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Start async re-voicing of an existing story (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen neu vertonen.")

    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Story not found")

    meta.status = "generating"
    meta.progress = "Starte Neuvertonung..."
    meta.voice_key = req.voice_key
    meta.progress_pct = 0
    store.add_story(meta)

    _generation_status[story_id] = {
        "status": "starting",
        "progress": "Starte Neuvertonung...",
        "title": meta.title,
    }

    # Run revoice in background
    asyncio.create_task(
        _run_revoice_pipeline(
            story_id=story_id,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
        )
    )

    return {"id": story_id, "status": "revoicing"}


async def _run_revoice_pipeline(
    story_id: str,
    voice_key: str,
    speech_rate: str,
):
    """Revoice pipeline: load text → TTS → merge → save."""
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    text_path = story_dir / "story.json"
    
    if not text_path.exists():
        logger.error(f"Cannot revoice: {text_path} missing")
        return

    story_data = json.loads(text_path.read_text(encoding="utf-8"))
    real_title = story_data["title"]

    async def on_progress(status_type: str, message: str, pct: int | None = None):
        combined_message = f"{real_title}: {message}"
        _generation_status[story_id]["status"] = status_type
        _generation_status[story_id]["progress"] = combined_message
        if pct is not None:
            _generation_status[story_id]["progress_pct"] = pct
        
        curr = store.get_by_id(story_id)
        if curr:
            curr.status = "generating" if status_type != "done" and status_type != "error" else status_type
            curr.progress = combined_message
            if pct is not None:
                curr.progress_pct = pct
            store.add_story(curr)

    try:
        # Step 1: TTS
        await on_progress("generating_audio", "Bereite Neuvertonung vor...", 10)
        chunks_dir = story_dir / "chunks"
        # Clear old chunks
        import shutil
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir)
        chunks_dir.mkdir(parents=True, exist_ok=True)

        audio_files, actual_voice = await chapters_to_audio(
            chapters=story_data["chapters"],
            output_dir=chunks_dir,
            voice_key=voice_key,
            rate=speech_rate,
            on_progress=on_progress,
        )

        # Step 2: Title audio
        await on_progress("generating_audio", "Vertone Titel...", 80)
        title_tts_path = chunks_dir / "title.mp3"
        await generate_tts_chunk(
            text=story_data["title"],
            output_path=title_tts_path,
            voice_key=actual_voice,
            rate=speech_rate,
            is_title=True
        )

        # Step 3: Merge
        await on_progress("processing", "Mische Audio-Spuren...", 85)
        final_audio_path = story_dir / "story.mp3"
        await merge_audio_files(
            audio_files=audio_files,
            output_path=final_audio_path,
            intro_path=settings.INTRO_MUSIC_PATH,
            outro_path=settings.OUTRO_MUSIC_PATH,
            title_path=title_tts_path,
        )

        duration = await get_audio_duration(final_audio_path)

        # Update metadata
        all_voices = get_available_voices()
        actual_voice_name = next((v["name"] for v in all_voices if v["key"] == actual_voice), "Unbekannt")

        story_meta = store.get_by_id(story_id)
        if story_meta:
            story_meta.duration_seconds = duration
            story_meta.voice_key = actual_voice
            story_meta.voice_name = actual_voice_name
            story_meta.status = "done"
            story_meta.progress = "Neuvertonung fertig!"
            story_meta.progress_pct = 100
            store.add_story(story_meta)

    except Exception as e:
        logger.error(f"Revoice error for {story_id}: {e}", exc_info=True)
        await on_progress("error", f"Neuvertonung fehlgeschlagen: {e}")


@app.post("/api/stories/generate-free")
async def start_free_generation(req: FreeTextRequest, current_user: User = Depends(get_current_active_user)):
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
            user_id=current_user.id,
        )
    )

    return {"id": story_id, "status": "started"}



@app.post("/api/generate-hook", response_model=HookResponse)
async def api_generate_hook(req: HookRequest):
    """Generate a quick surreal story idea hook based on genre and author."""
    hook = await generate_story_hook(req.genre, req.author_id, user_input=req.user_input)
    return HookResponse(hook_text=hook)

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
    user_id: str | None = None,
    parent_id: str | None = None,
    remix_type: str | None = None,
    further_instructions: str | None = None,
    parent_meta: StoryMeta | None = None,
    parent_text: dict | None = None,
):
    """Full pipeline: text → TTS → merge → save."""
    logger.info(f"!!! STARTING PIPELINE for story {story_id} (Remix: {remix_type}) !!!")
    logger.info(f"Prompt: {prompt[:50]}...")
    logger.info(f"Voice Key received: '{voice_key}'")
    
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    story_dir.mkdir(parents=True, exist_ok=True)

    # Resolve voice name
    voice_name = "Unbekannt"
    all_voices = get_available_voices()
    for v in all_voices:
        if v["key"] == voice_key:
            voice_name = v["name"]
            break

    # Clean up prompt for display: remove system prefixes if present
    clean_prompt = original_prompt or prompt
    if "Kurzgeschichte im Genre" in clean_prompt and "Idee:" in clean_prompt:
        clean_prompt = clean_prompt.split("Idee:", 1)[-1].strip()
    
    # Initial record creation
    author_display = get_author_names(style)
    story_meta = StoryMeta(
        id=story_id,
        title=f"Schreibe Dein {author_display}-Epos ({target_minutes} Min)...",
        description=f"{(original_prompt or prompt)[:100]}...",
        prompt=clean_prompt,
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
        user_id=user_id,
        parent_id=parent_id,
    )
    store.add_story(story_meta)

    # Point-based progress system
    # Planung: 5
    # Text: 10 * num_chapters
    # Bild: 5 (if enabled)
    # Vertonung: 10 * num_chapters (if enabled)
    # Finalisierung: 10 (if enabled)
    
    # We don't know the exact num_chapters until text is generated, 
    # so we assume 4 for a 20 min story (5 min/chapter) as a baseline for the denominator.
    # target_minutes // 5 is used by _generate_multi_pass (min 2)
    estimated_chapters = max(2, target_minutes // 5)
    
    total_points = 5 # Planung
    total_points += 10 * estimated_chapters # Text
    total_points += 5 # Bild
    if voice_key != "none":
        total_points += 10 * estimated_chapters # Vertonung
        total_points += 10 # Finalisierung
        
    completed_points = 0
    real_num_chapters = estimated_chapters # updated once text is back

    async def on_progress(status_type: str, message: str, points: int | None = None, is_absolute_points: bool = False, **kwargs):
        nonlocal completed_points
        if points is not None:
            if is_absolute_points:
                completed_points = points
            else:
                completed_points += points
        
        pct = int((completed_points / total_points) * 100)
        pct = min(pct, 99) # Keep at 99 until truly done

        # Map internal status to user-visible steps
        label = message
        if status_type == "generating_text": label = "Texterstellung"
        elif status_type == "generating_image": label = "Bild generieren"
        elif status_type == "generating_audio" or status_type == "tts": label = "Vertonung"
        elif status_type == "processing": label = "Finalisierung"
        elif status_type == "planning": label = "Planung"
        
        _generation_status[story_id]["status"] = status_type
        _generation_status[story_id]["progress"] = label
        _generation_status[story_id]["progress_pct"] = pct
        
        if "title" in kwargs:
            _generation_status[story_id]["title"] = kwargs["title"]
        if "synopsis" in kwargs:
            _generation_status[story_id]["synopsis"] = kwargs["synopsis"]

        # Also update persistent store
        curr = store.get_by_id(story_id)
        if curr:
            curr.status = "generating" if status_type != "done" and status_type != "error" else status_type
            curr.progress = label
            curr.progress_pct = pct
            
            if "title" in kwargs:
                curr.title = kwargs["title"]
            if "synopsis" in kwargs:
                curr.description = kwargs["synopsis"]
                
            curr.updated_at = datetime.now(timezone.utc)
            store.add_story(curr)

    try:
        start_time_total = time.time()
        
        # Phase 1: Planung (5 Points)
        await on_progress("planning", "Planung", points=5, is_absolute_points=True)

        # Phase 2: Text Generation
        completed_text_chapters = 0
        async def text_progress_wrapper(stype, msg, pct=None, **kwargs):
            nonlocal completed_text_chapters
            if stype == "text_chapter_done":
                completed_text_chapters += 1
                # Increment points: baseline 5 + (10 * chapters done)
                await on_progress("generating_text", "Texterstellung", points=5 + (10 * completed_text_chapters), is_absolute_points=True, **kwargs)
            elif stype == "outline_done":
                # Report planning done + provide real title/synopsis
                await on_progress("generating_text", "Texterstellung", points=5, is_absolute_points=True, **kwargs)
            else:
                await on_progress("generating_text", "Texterstellung", **kwargs)

        story_data = await generate_full_story(
            prompt=prompt,
            genre=genre,
            style=style,
            characters=characters,
            target_minutes=target_minutes,
            on_progress=text_progress_wrapper,
            remix_type=remix_type,
            further_instructions=further_instructions,
            parent_text=parent_text,
        )
        
        real_title = story_data["title"]
        _generation_status[story_id]["real_title"] = real_title
        real_num_chapters = len(story_data["chapters"])
        
        # Save real title and synopsis to database immediately
        curr = store.get_by_id(story_id)
        if curr:
            curr.title = real_title
            curr.description = story_data.get("synopsis", curr.description)
            store.add_story(curr)
        total_points = 5 + (10 * real_num_chapters) + 5
        if voice_key != "none":
            total_points += (10 * real_num_chapters) + 10
        
        # Mark text as done (5 + 10 * chapters)
        await on_progress("generating_text", "Texterstellung", points=5 + (10 * real_num_chapters), is_absolute_points=True)

        # Phase 3: Background image generation (5 points)
        image_url = None
        async def background_image_gen():
            nonlocal image_url
            try:
                # We don't increment points here because it's background, 
                # but we'll reserve the 5 points for when it finishes or we wait.
                image_path = story_dir / "cover.png"
                res = await generate_story_image(story_data.get("synopsis", ""), image_path, genre=genre, style=style)
                if res:
                    image_url = f"{settings.BASE_URL}/api/stories/{story_id}/image.png"
                    try:
                        await _generate_thumbnail(image_path, story_dir / "cover_thumb.jpg")
                    except: pass
            except Exception as e:
                logger.error(f"Image gen failed: {e}")

        image_task = asyncio.create_task(background_image_gen())

        # Save text
        text_path = story_dir / "story.json"
        text_path.write_text(json.dumps(story_data, ensure_ascii=False, indent=2), encoding="utf-8")

        if voice_key == "none":
            # Phase 3: Wait for image
            await on_progress("generating_image", "Bild generieren", points=5)
            await image_task
            await on_progress("done", "Fertig!", points=total_points, is_absolute_points=True)
            
            total_text = "\n".join([c["text"] for c in story_data["chapters"]])
            curr = store.get_by_id(story_id)
            if curr:
                curr.title = real_title
                curr.status = "done"
                curr.progress = "Fertig!"
                curr.progress_pct = 100
                curr.image_url = image_url
                curr.word_count = len(total_text.split())
                curr.chapter_count = real_num_chapters
                store.add_story(curr)
            return

        # Phase 4: Vertonung (10 Points per Chapter)
        # First, ensure image points are recorded (we don't wait for it yet, but it's part of the count)
        await on_progress("generating_image", "Bild generieren", points=5)
        
        # We need to update chapters_to_audio to use points
        completed_audio_chapters = 0
        async def tts_progress_wrapper(stype, msg, pct=None):
            nonlocal completed_audio_chapters
            if stype == "tts_chapter_done":
                completed_audio_chapters += 1
                # Add 10 points per chapter
                await on_progress("generating_audio", "Vertonung", points=5 + (10 * real_num_chapters) + 5 + (10 * completed_audio_chapters), is_absolute_points=True)
            else:
                await on_progress("generating_audio", "Vertonung")

        chunks_dir = story_dir / "chunks"
        audio_files, actual_voice = await chapters_to_audio(
            chapters=story_data["chapters"],
            output_dir=chunks_dir,
            voice_key=voice_key,
            rate=speech_rate,
            on_progress=tts_progress_wrapper,
        )

        # Phase 5: Finalisierung (10 points)
        await on_progress("processing", "Finalisierung", points=total_points - 10, is_absolute_points=True)
        
        title_tts_path = chunks_dir / "title.mp3"
        await generate_tts_chunk(story_data["title"], title_tts_path, voice_key=actual_voice, rate=speech_rate, is_title=True)

        final_audio_path = story_dir / "story.mp3"
        await merge_audio_files(
            audio_files=audio_files,
            output_path=final_audio_path,
            intro_path=settings.INTRO_MUSIC_PATH,
            outro_path=settings.OUTRO_MUSIC_PATH,
            title_path=title_tts_path,
        )

        duration = await get_audio_duration(final_audio_path)
        await image_task

        # Phase 6: Done
        await on_progress("done", "Fertig!", points=total_points, is_absolute_points=True)

        total_text = "\n".join([c["text"] for c in story_data["chapters"]])
        story_meta = store.get_by_id(story_id)
        if story_meta:
            story_meta.title = real_title
            story_meta.description = story_data.get("synopsis", story_meta.description)
            story_meta.duration_seconds = duration
            story_meta.chapter_count = real_num_chapters
            story_meta.word_count = len(total_text.split())
            story_meta.image_url = image_url
            story_meta.status = "done"
            story_meta.progress = "Fertig!"
            story_meta.progress_pct = 100
            store.add_story(story_meta)

            
        logger.info(f"BENCHMARK [{story_id}]: Total Pipeline Finished in {time.time() - start_time_total:.2f} seconds")

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

from fastapi import Query

@app.get("/api/stories", response_model=StoryListResponse)
async def list_stories(
    page: int = 1,
    page_size: int = 30,
    filter: str = "all", # "my", "public", "all"
    user_id: str | None = None,
    genre: list[str] | None = Query(default=None),
    search: str | None = None,
    current_user: User | None = Depends(get_optional_user)
):
    """List stories with pagination and filtering."""
    try:
        all_stories = store.get_all(genre=genre, search=search)
        
        if not all_stories:
            logger.info("API list_stories: No stories found in database.")

        # Fetch users to map IDs to display names (username or email)
        users_map = {u.id: (u.username or u.email) for u in store.get_all_users()}

        # Calculate counts regardless of filter
        stories_my_all = [s for s in all_stories if s.user_id == (current_user.id if current_user else None)]
        total_my = len(stories_my_all)
        
        if current_user and current_user.is_admin:
            # For admins, "public/all" count means "stories from others"
            total_public = len([s for s in all_stories if s.user_id != current_user.id])
        else:
            total_public = len([s for s in all_stories if s.is_public])

        # Initial bucket: what is visible to this user?
        accessible_stories = []
        for s in all_stories:
            if s.is_public:
                accessible_stories.append(s)
            elif current_user and (s.user_id == current_user.id or current_user.is_admin):
                accessible_stories.append(s)
        
        # Apply user_id filter if provided (server-side)
        if user_id:
            can_filter_by_user = current_user and (current_user.is_admin or current_user.id == user_id)
            if not can_filter_by_user:
                raise HTTPException(status_code=403, detail="Keine Berechtigung diesen Nutzer zu filtern.")
            accessible_stories = [s for s in accessible_stories if s.user_id == user_id]

        # Apply UI filter (Selection from bucket)
        if filter == "my" and current_user:
            stories_to_list = [s for s in accessible_stories if s.user_id == current_user.id]
        elif filter == "public":
            stories_to_list = [s for s in accessible_stories if s.is_public]
        elif filter == "all" and current_user and current_user.is_admin:
            stories_to_list = accessible_stories
        else:
            stories_to_list = accessible_stories
            
        # Sort by creation date (newest first)
        stories_to_list.sort(key=lambda x: x.created_at, reverse=True)

        # Attach display names (username or email) for author display
        for s in stories_to_list:
            if s.user_id:
                s.user_email = users_map.get(s.user_id, "Anonym")
            else:
                s.user_email = "System"
        
        # POPULATE IS_FAVORITE for the current user
        if current_user:
            story_ids = [s.id for s in stories_to_list]
            fav_results = store.get_all(requesting_user_id=current_user.id)
            fav_ids = {f.id for f in fav_results if f.is_favorite}
            for s in stories_to_list:
                s.is_favorite = s.id in fav_ids

        total = len(stories_to_list)
        logger.info(f"API list_stories: Filter='{filter}', UserID='{user_id}', Total={total}")
        
        start = (page - 1) * page_size
        end = start + page_size
        paginated_stories = stories_to_list[start:end]
            
        return StoryListResponse(
            stories=paginated_stories, 
            total=total,
            total_my=total_my,
            total_public=total_public
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CRITICAL: list_stories failed: {e}", exc_info=True)
        return StoryListResponse(stories=[], total=0, total_my=0, total_public=0)


# ──────────────────────────────────
# Admin Actions
# ──────────────────────────────────

@app.get("/api/admin/users", response_model=list[UserResponse])
async def admin_list_users(current_user: User = Depends(get_current_active_user)):
    """List all users (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Benutzer verwalten.")
    
    users = store.get_all_users()
    all_stories = store.get_all()
    
    # Calculate story counts
    counts = {}
    for story in all_stories:
        if story.user_id:
            counts[story.user_id] = counts.get(story.user_id, 0) + 1
            
    # Attach counts to user objects
    response_users = []
    for u in users:
        u_data = u.model_dump()
        u_data["story_count"] = counts.get(u.id, 0)
        response_users.append(UserResponse(**u_data))
        
    return response_users


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, current_user: User = Depends(get_current_active_user)):
    """Delete a user (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Benutzer löschen.")
    
    from app.database import get_session
    from sqlmodel import select
    
    with next(get_session()) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
        if user.email == settings.ADMIN_EMAIL:
            raise HTTPException(status_code=400, detail="Der Haupt-Admin kann nicht gelöscht werden.")
        
        session.delete(user)
        session.commit()
    
    return {"status": "success", "message": "Benutzer gelöscht."}


class UserAdminUpdate(BaseModel):
    is_admin: bool | None = None
    is_active: bool | None = None

@app.patch("/api/admin/users/{user_id}")
async def admin_update_user(
    user_id: str, 
    data: UserAdminUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update user status/role (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Benutzer bearbeiten.")
    
    from app.database import get_session
    
    with next(get_session()) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
            
        if data.is_admin is not None:
            user.is_admin = data.is_admin
        if data.is_active is not None:
            user.is_active = data.is_active
            
        session.add(user)
        session.commit()
    
    return {"status": "success", "message": "Benutzer aktualisiert."}


@app.delete("/api/admin/stories/{story_id}")
async def admin_delete_story(story_id: str, current_user: User = Depends(get_current_active_user)):
    """Delete a story (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Geschichten löschen.")
    
    success = store.delete_story(story_id)
    if not success:
        raise HTTPException(status_code=404, detail="Geschichte nicht gefunden")
        
    # Optional: Delete files from disk
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    if story_dir.exists():
        import shutil
        shutil.rmtree(story_dir)
        
    return {"status": "success", "message": "Geschichte gelöscht."}


@app.get("/api/stories/{story_id}")
async def get_story(
    story_id: str,
    current_user: User | None = Depends(get_optional_user)
):
    """Get full details of a single story."""
    story = store.get_by_id(story_id, requesting_user_id=current_user.id if current_user else None)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Check accessibility
    if not story.is_public:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not (current_user.is_admin or story.user_id == current_user.id):
            raise HTTPException(status_code=403, detail="Story is private")

    text_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.json"
    if not text_path.exists():
        # Fallback for stories without detail JSON
        return {**story.model_dump(), "chapters": []}
        
    try:
        data = json.loads(text_path.read_text(encoding="utf-8"))
        return {**story.model_dump(), "chapters": data.get("chapters", [])}
    except Exception as e:
        logger.error(f"Failed to read story details for {story_id}: {e}")
        return {**story.model_dump(), "chapters": []}


@app.post("/api/stories/{story_id}/favorite")
async def toggle_favorite(
    story_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Toggle a story as favorite for the current user."""
    is_fav = store.toggle_favorite(current_user.id, story_id)
    return {"id": story_id, "is_favorite": is_fav}


@app.get("/api/stories/favorites", response_model=list[StoryMeta])
async def list_favorites(
    current_user: User = Depends(get_current_active_user)
):
    """List all stories favorited by the current user."""
    return store.get_favorites(current_user.id)


@app.get("/api/stories/{story_id}/audio")
async def get_audio(story_id: str, request: Request):
    """Stream the final MP3 audio file with Range support for seeking."""
    audio_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    meta = store.get_by_id(story_id)
    filename = f"{meta.title if meta else story_id}.mp3"
    
    file_size = audio_path.stat().st_size
    range_header = request.headers.get("Range", None)
    
    if range_header:
        byte1, byte2 = 0, None
        match = range_header.replace("bytes=", "").split("-")
        if match[0]:
            byte1 = int(match[0])
        if len(match) > 1 and match[1]:
            byte2 = int(match[1])

        length = file_size - byte1
        if byte2 is not None:
            length = byte2 + 1 - byte1

        def stream_file_range(start, length_to_read, chunk_size=8192):
            with open(audio_path, "rb") as f:
                f.seek(start)
                remaining = length_to_read
                while remaining > 0:
                    read_size = min(chunk_size, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    yield data
                    remaining -= len(data)

        response = StreamingResponse(stream_file_range(byte1, length), status_code=206, media_type="audio/mpeg")
        response.headers["Content-Range"] = f"bytes {byte1}-{byte1 + length - 1}/{file_size}"
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Content-Length"] = str(length)
        return response
    
    response = FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=filename,
    )
    response.headers["Accept-Ranges"] = "bytes"
    return response


@app.patch("/api/stories/{story_id}")
async def update_story(
    story_id: str, 
    req: StoryUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update story metadata or visibility (Admin only for public toggle)."""
    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Story not found")

    # Permissions
    if req.is_public is not None:
        # Only owner or admin can toggle visibility
        if meta.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Nur der Besitzer oder Admins dürfen die Sichtbarkeit ändern.")
        meta.is_public = req.is_public

    if req.title is not None:
        # Only owner or admin can change title
        if meta.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Keine Berechtigung.")
        meta.title = req.title

    store.add_story(meta)
    return meta


@app.delete("/api/stories/{story_id}")
async def delete_story(
    story_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Delete a story and its files (Owner or Admin only)."""
    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Story not found")

    if meta.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Keine Berechtigung zum Löschen.")

    if not store.delete_story(story_id):
        raise HTTPException(status_code=404, detail="Story not found")

    import shutil
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    if story_dir.exists():
        shutil.rmtree(story_dir)

    return {"status": "deleted"}


@app.post("/api/stories/{story_id}/regenerate-image")
async def regenerate_story_image_api(
    story_id: str,
    current_user: User = Depends(get_current_active_user)
):
    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Story not found")

    # Permissions: Only owner or admin
    if meta.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur der Besitzer oder Admins dürfen Bilder neu generieren.")

    # Load text to get synopsis
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    text_path = story_dir / "story.json"
    if not text_path.exists():
        raise HTTPException(status_code=404, detail="Story text data (story.json) missing")

    try:
        story_data = json.loads(text_path.read_text(encoding="utf-8"))
        synopsis = story_data.get("synopsis", "")

        async def background_task():
            image_path = story_dir / "cover.png"
            logger.info(f"MANUAL REGEN: Calling generate_story_image for {story_id}")
            res = await generate_story_image(synopsis, image_path, genre=meta.genre, style=meta.style)
            if res:
                image_url = f"{settings.BASE_URL}/api/stories/{story_id}/image.png"
                meta.image_url = image_url
                meta.updated_at = datetime.now(timezone.utc)
                # Update metadata in store
                store.add_story(meta)
                # Thumbnail
                try:
                    await _generate_thumbnail(image_path, story_dir / "cover_thumb.jpg")
                except Exception as te:
                    logger.warning(f"Manual thumbnail generation failed for {story_id}: {te}")
                logger.info(f"Manual image regeneration successful for {story_id}")
            else:
                logger.error(f"Manual image regeneration FAILED for {story_id}")

        asyncio.create_task(background_task())
        return {"status": "started", "message": "Bild-Generierung gestartet."}
    except Exception as e:
        logger.error(f"Error starting manual regen for {story_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/stories/{story_id}/thumb.jpg")
async def get_story_thumbnail(story_id: str):
    """Serve a small JPEG thumbnail (256x256) for fast loading in lists."""
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    thumb_path = story_dir / "cover_thumb.jpg"
    cover_path = story_dir / "cover.png"
    
    # Generate on demand if thumbnail doesn't exist yet but cover does
    if not thumb_path.exists() and cover_path.exists():
        try:
            await _generate_thumbnail(cover_path, thumb_path)
        except Exception:
            pass
    
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(thumb_path, media_type="image/jpeg")


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

@app.get("/api/users/{user_id}/avatar.jpg")
async def get_user_avatar(user_id: str):
    """Serve the user's main profile picture."""
    avatar_path = settings.AUDIO_OUTPUT_DIR / "avatars" / f"{user_id}.jpg"
    if not avatar_path.exists():
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(avatar_path, media_type="image/jpeg")

@app.get("/api/users/{user_id}/avatar_thumb.jpg")
async def get_user_avatar_thumb(user_id: str):
    """Serve the user's thumbnail profile picture."""
    thumb_path = settings.AUDIO_OUTPUT_DIR / "avatars" / f"{user_id}_thumb.jpg"
    if not thumb_path.exists():
        # Fallback to main avatar if thumb is missing
        avatar_path = settings.AUDIO_OUTPUT_DIR / "avatars" / f"{user_id}.jpg"
        if avatar_path.exists():
            return FileResponse(avatar_path, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Avatar not found")
    return FileResponse(thumb_path, media_type="image/jpeg")


@app.get("/api/feed.xml")
@app.get("/api/feed-labor.xml")
async def get_rss_feed():
    """Serve the global podcast RSS feed (all public/spotify stories)."""
    # Only include stories that have is_on_spotify=True
    stories = store.get_all(only_spotify=True)
    
    logger.info(f"Generating global RSS feed with {len(stories)} stories.")
    
    image_url = f"{settings.BASE_URL}/api/podcast-cover.png"
    email = "dirk@proessel.de"
    
    try:
        xml_content = generate_rss_feed(
            stories,
            settings.BASE_URL,
            image_url=image_url,
            email=email,
        )
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"RSS Feed error: {e}")
        raise HTTPException(status_code=500, detail="Error generating RSS feed")


@app.get("/api/feed/{user_id}.xml")
async def get_personal_rss_feed(user_id: str):
    """Serve a personalized podcast RSS feed for a specific user."""
    # Only include stories for this user that have is_on_spotify=True
    stories = store.get_all(only_spotify=True, user_id=user_id)
    
    logger.info(f"Generating personal RSS feed for user {user_id} with {len(stories)} stories.")
    
    # We might want a different title or image for personal feeds in the future
    image_url = f"{settings.BASE_URL}/api/podcast-cover.png"
    email = "dirk@proessel.de"
    
    try:
        xml_content = generate_rss_feed(
            stories,
            settings.BASE_URL,
            title=f"Bedtime Stories (Privat)",
            image_url=image_url,
            email=email,
        )
        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"Personal RSS Feed error: {e}")
        raise HTTPException(status_code=500, detail="Error generating personal RSS feed")


# ──────────────────────────────────
# Kindle Export
# ──────────────────────────────────

@app.post("/api/stories/{story_id}/export-kindle")
async def export_to_kindle_api(story_id: str, req: KindleExportRequest):
    """Generate EPUB and send to Kindle via email."""
    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Story not found")

    # Load full text
    story_dir = settings.AUDIO_OUTPUT_DIR / story_id
    text_path = story_dir / "story.json"
    if not text_path.exists():
        raise HTTPException(status_code=404, detail="Story text data missing")

    try:
        story_data = json.loads(text_path.read_text(encoding="utf-8"))
        
        # Prepare paths
        epub_path = story_dir / f"{story_id}.epub"
        cover_path = story_dir / "cover.png"
        
        # Generate EPUB (space efficient)
        story_data["id"] = story_id
        await generate_epub(story_data, cover_path if cover_path.exists() else None, epub_path)
        
        # Send via SMTP
        await send_to_kindle(epub_path, req.email, story_data["title"])
        
        return {"status": "success", "message": f"Story an {req.email} gesendet"}
        
    except Exception as e:
        logger.error(f"Kindle export failed for {story_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# ──────────────────────────────────
# Stats
# ──────────────────────────────────

@app.get("/api/stats/popularity")
async def get_popularity():
    """Return genres, authors and voices sorted by usage frequency from the archive."""
    from collections import Counter
    stories = store.get_all()

    genre_counter: Counter = Counter()
    author_counter: Counter = Counter()
    voice_counter: Counter = Counter()

    for s in stories:
        if s.status != "done":
            continue
        if s.genre:
            genre_counter[s.genre] += 1
        if s.style:
            for author_id in [a.strip() for a in s.style.split(",") if a.strip()]:
                author_counter[author_id] += 1
        if s.voice_key:
            voice_counter[s.voice_key] += 1

    return {
        "genres": [g for g, _ in genre_counter.most_common()],
        "authors": [a for a, _ in author_counter.most_common()],
        "voices": [v for v, _ in voice_counter.most_common()],
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
