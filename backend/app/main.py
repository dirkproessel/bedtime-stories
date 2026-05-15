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
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel


from app.models import (
    StoryRequest,
    FreeTextRequest,
    HookRequest,
    HookResponse,
    StoryMeta,
    StoryMetaResponse,
    StoryListResponse,
    VoiceProfile,
    KindleExportRequest,
    User,
    UserResponse,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from app.auth_utils import get_current_active_user, get_optional_user
from fastapi import Depends
from app.database import create_db_and_tables
from app.models import StoryUpdate
from app.services.story_generator import (
    generate_full_story, 
    generate_story_hook, 
    get_author_names,
    generate_post_story_analysis
)
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
from fastapi import Form
from app.services.whatsapp_service import whatsapp_service
from app.services.conversation_service import conversation_service


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
from app.routers import auth, alexa, playlist
app.include_router(auth.router)
app.include_router(alexa.router)
app.include_router(playlist.router)


# Mount Static Files (for Legal Docs / Images)
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/api/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

from app.services.store import store
from app.services.story_service import story_service


# ──────────────────────────────────
# WhatsApp Webhook
# ──────────────────────────────────

async def run_whatsapp_pipeline(from_number: str, **kwargs):
    """Wrapper to run story generation and notify user on WhatsApp when done."""
    try:
        await story_service.run_pipeline(**kwargs)
        story_id = kwargs.get("story_id")
        base_url = settings.BASE_URL.rstrip('/')
        # Link to the public story page
        url = f"{base_url}/stories/{story_id}"
        whatsapp_service.send_message(from_number, f"🌟 Deine Geschichte ist fertig! Du kannst sie hier hören: {url}")
    except Exception as e:
        logger.error(f"WhatsApp Pipeline failed: {e}")
        whatsapp_service.send_message(from_number, "❌ Leider gab es ein Problem bei der Erstellung deiner Geschichte. Bitte versuche es später noch einmal.")

@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...)):
    """Webhook for incoming WhatsApp messages from Twilio."""
    logger.info(f"WhatsApp Message from {From}: {Body}")
    
    # 1. Process message via Conversation Service
    result = await conversation_service.process_message(From, Body)
    
    # 2. Send immediate reply
    whatsapp_service.send_message(From, result["reply"])
    
    # 3. If ready, trigger story generation
    if result.get("status") == "READY" and result.get("story_params"):
        params = result["story_params"]
        story_id = str(uuid.uuid4())[:8]
        
        # Use admin as default user for WhatsApp stories
        all_users = store.get_all_users()
        if not all_users:
            logger.error("No users found in DB to assign WhatsApp story to.")
            return Response(content="OK", media_type="text/plain")
            
        admin_user = next((u for u in all_users if u.email == settings.ADMIN_EMAIL), all_users[0])
        
        # Initialize story record
        story_service.initialize_story(
            story_id=story_id,
            prompt=params["prompt"],
            genre=params["genre"],
            style=params["style"],
            voice_key=params["voice_key"],
            target_minutes=params["target_minutes"],
            user_id=admin_user.id
        )
        
        # Run pipeline in background with notification wrapper
        asyncio.create_task(
            run_whatsapp_pipeline(
                from_number=From,
                story_id=story_id,
                prompt=params["prompt"],
                genre=params["genre"],
                style=params["style"],
                characters=None,
                target_minutes=params["target_minutes"],
                voice_key=params["voice_key"],
                speech_rate="0%",
                user_id=admin_user.id
            )
        )
        
        # Clear session after starting generation
        conversation_service.clear_session(From)
    
    return Response(content="OK", media_type="text/plain")



# ──────────────────────────────────
# Voices
# ──────────────────────────────────

@app.get("/api/voices", response_model=list[VoiceProfile])
async def list_voices(current_user: User | None = Depends(get_optional_user)):
    """List all available voice profiles."""
    return get_available_voices(user_id=current_user.id if current_user else None)


@app.get("/api/voices/{voice_key}/preview")
async def preview_voice(voice_key: str):
    """Generate and return a voice preview clip."""
    preview_dir = settings.AUDIO_OUTPUT_DIR / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_path = preview_dir / f"{voice_key}.mp3"
    
    try:
        await generate_voice_preview(voice_key, preview_path)
    except Exception as e:
        print(f"Preview generation failed: {e}")
        # Return fallback if exists, or error
        if not preview_path.exists():
            raise HTTPException(status_code=500, detail=str(e))
            
    return FileResponse(preview_path, media_type="audio/mpeg")


# ──────────────────────────────────
# Story Generation
# ──────────────────────────────────

@app.post("/api/stories/generate")
async def start_generation(req: StoryRequest, current_user: User = Depends(get_current_active_user)):
    """Start async story generation. Returns story ID to poll status."""
    story_id = str(uuid.uuid4())[:8]

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

    # Initialize story record synchronously so it's guaranteed to be in the store 
    # when the frontend receives the 'started' response and reloads the archive.
    story_service.initialize_story(
        story_id=story_id,
        prompt=req.system_prompt or req.prompt,
        genre=req.genre,
        style=req.style,
        voice_key=req.voice_key,
        target_minutes=req.target_minutes,
        user_id=current_user.id,
        parent_id=req.parent_id,
        original_prompt=req.prompt
    )

    # Run generation in background
    asyncio.create_task(
        story_service.run_pipeline(
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
    speech_rate: str = "0%"


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

    # Run revoice in background
    asyncio.create_task(
        story_service.run_revoice_pipeline(
            story_id=story_id,
            voice_key=req.voice_key,
            speech_rate=req.speech_rate,
        )
    )

    return {"id": story_id, "status": "revoicing"}

class RegenerateImageRequest(BaseModel):
    image_hints: str | None = None


@app.post("/api/stories/generate-free")
async def start_free_generation(req: FreeTextRequest, current_user: User = Depends(get_current_active_user)):
    """Start generation from free text prompt."""
    story_id = str(uuid.uuid4())[:8]

    # Initialize story record synchronously
    story_service.initialize_story(
        story_id=story_id,
        prompt=req.text,
        genre="Realismus",
        style="adams",
        voice_key=req.voice_key,
        target_minutes=req.target_minutes,
        user_id=current_user.id,
        original_prompt=req.text
    )

    # Run generation in background
    asyncio.create_task(
        story_service.run_pipeline(
            story_id=story_id,
            prompt=req.text,
            genre="Realismus",
            style="adams",
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

# ──────────────────────────────────
# Status (Polling)
# ──────────────────────────────────

@app.get("/api/status/{story_id}")
async def get_status(story_id: str):
    """Get current generation status."""
    status = story_service.get_status(story_id)
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
        # Fetch stories with search but WITHOUT genre filter first to calculate available genres
        all_stories_base = store.get_all(search=search)
        
        if not all_stories_base:
            logger.info("API list_stories: No stories found in database.")

        # Fetch users to map IDs to display names (username or email)
        users_map = {u.id: (u.username or u.email) for u in store.get_all_users()}

        # Initial bucket: what is visible to this user?
        accessible_stories_base = []
        for s in all_stories_base:
            if s.is_public:
                accessible_stories_base.append(s)
            elif current_user and (s.user_id == current_user.id or current_user.is_admin):
                accessible_stories_base.append(s)
        
        # Apply user_id filter if provided (server-side)
        if user_id:
            can_filter_by_user = current_user and (current_user.is_admin or current_user.id == user_id)
            if not can_filter_by_user:
                raise HTTPException(status_code=403, detail="Keine Berechtigung diesen Nutzer zu filtern.")
            accessible_stories_base = [s for s in accessible_stories_base if s.user_id == user_id]

        # Calculate base counts for the current search (respecting search but not genre)
        stories_my_base = [s for s in accessible_stories_base if current_user and s.user_id == current_user.id]
        total_my = len(stories_my_base)
        
        if current_user and current_user.is_admin:
            total_public = len([s for s in accessible_stories_base if s.user_id != current_user.id])
        else:
            total_public = len([s for s in accessible_stories_base if s.is_public])

        # Apply UI filter (Selection from bucket)
        if filter == "my" and current_user:
            stories_to_list_base = stories_my_base
        elif filter == "favorites" and current_user:
            fav_stories = store.get_favorites(current_user.id)
            fav_ids = {s.id for s in fav_stories}
            stories_to_list_base = [s for s in accessible_stories_base if s.id in fav_ids]
        elif filter == "public":
            stories_to_list_base = [s for s in accessible_stories_base if s.is_public]
        else:
            stories_to_list_base = accessible_stories_base

        # Calculate available genres for THIS view/search context (ignoring current genre selection)
        available_genres = sorted(list(set(s.genre for s in stories_to_list_base if s.genre)))

        # NOW apply the genre filter to the actual results
        if genre:
            genre_set = set(genre)
            stories_to_list = [s for s in stories_to_list_base if s.genre in genre_set]
        else:
            stories_to_list = stories_to_list_base
            
        # Sort by creation date (newest first)
        stories_to_list.sort(key=lambda x: x.created_at, reverse=True)

        # Attach display names (username or email) for author display
        for s in stories_to_list:
            if s.user_id:
                s.user_email = users_map.get(s.user_id, "Anonym")
            else:
                s.user_email = "System"
        
        # POPULATE IS_FAVORITE for the current user
        stories_to_list = [StoryMetaResponse.model_validate(s) for s in stories_to_list]
        if current_user:
            story_ids = [s.id for s in stories_to_list]
            fav_results = store.get_all(requesting_user_id=current_user.id)
            fav_ids = {f.id for f in fav_results if f.is_favorite}
            for s in stories_to_list:
                s.is_favorite = s.id in fav_ids

        total = len(stories_to_list)
        logger.info(f"API list_stories: Filter='{filter}', UserID='{user_id}', GenreCount={len(genre) if genre else 0}, Total={total}")
        
        start = (page - 1) * page_size
        end = start + page_size
        paginated_stories = stories_to_list[start:end]
            
        return StoryListResponse(
            stories=paginated_stories, 
            total=total,
            total_my=total_my,
            total_public=total_public,
            available_genres=available_genres
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

@app.get("/api/admin/voices")
async def admin_list_voices(current_user: User = Depends(get_current_active_user)):
    """List all voices for management (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Stimmen verwalten.")
    
    data = store.get_admin_voices()
    
    # Map users to clones
    users_map = {u.id: (u.username or u.email) for u in store.get_all_users()}
    
    result_clones = []
    for v in data["clones"]:
        v_dict = v.model_dump()
        v_dict["user_name"] = users_map.get(v.user_id, "Unknown")
        result_clones.append(v_dict)
        
    return {
        "clones": result_clones,
        "system": data["system"]
    }

@app.post("/api/admin/voices/{voice_type}/{voice_id}/toggle")
async def admin_toggle_voice(
    voice_type: str, 
    voice_id: str, 
    current_user: User = Depends(get_current_active_user)
):
    """Toggle visibility/active state of a voice (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Stimmen verwalten.")
    
    new_state = store.toggle_voice_active(voice_type, voice_id)
    if new_state is None:
        raise HTTPException(status_code=404, detail="Stimme nicht gefunden.")
    
    return {"new_state": new_state}


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


@app.post("/api/admin/analyze-story/{story_id}")
async def admin_analyze_story(story_id: str, current_user: User = Depends(get_current_active_user)):
    """Analyze an existing story to refine synopsis and extract highlights (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Geschichten analysieren.")
    
    meta = store.get_by_id(story_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Geschichte nicht gefunden")
    
    text_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.json"
    if not text_path.exists():
        raise HTTPException(status_code=400, detail="Kein Text für diese Geschichte verfügbar.")
    
    try:
        story_data = json.loads(text_path.read_text(encoding="utf-8"))
        analysis = await generate_post_story_analysis(meta.title, story_data.get("chapters", []))
        
        return {
            "story_id": story_id,
            "title": meta.title,
            "current_synopsis": meta.description,
            "new_synopsis": analysis["synopsis"],
            "highlights": analysis["highlights"]
        }
    except Exception as e:
        logger.error(f"Analysis endpoint failed for {story_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/settings", response_model=list[SystemSettingResponse])
async def admin_get_settings(current_user: User = Depends(get_current_active_user)):
    """List all global system settings (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Einstellungen sehen.")
    return store.get_all_settings()


@app.patch("/api/admin/settings/{key}", response_model=SystemSettingResponse)
async def admin_update_setting(
    key: str, 
    data: SystemSettingUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update a specific system setting (Admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Admins dürfen Einstellungen ändern.")
    
    store.set_system_setting(key, data.value)
    
    # Return the updated object
    all_s = store.get_all_settings()
    updated = next((s for s in all_s if s.key == key), None)
    if not updated:
        raise HTTPException(status_code=404, detail="Einstellung nicht gefunden.")
    return updated


@app.get("/api/stories/{story_id}")
async def get_story(
    story_id: str,
    current_user: User | None = Depends(get_optional_user)
):
    """Get full details of a single story."""
    story = store.get_by_id(story_id, requesting_user_id=current_user.id if current_user else None)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    if story.user_id:
        users_map = {u.id: (u.username or u.email) for u in store.get_all_users()}
        story.user_email = users_map.get(story.user_id, "Anonym")
    else:
        story.user_email = "System"
    
    # Accessible by URL to everyone (per user request)
    # The requirement is to allow viewing via direct link even if not public/published.
    # No additional check needed here as ID possession is the access token.

    text_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.json"
    if not text_path.exists():
        # Fallback for stories without detail JSON
        return {**story.model_dump(), "chapters": []}
        
    try:
        data = json.loads(text_path.read_text(encoding="utf-8"))
        chapters = data.get("chapters", [])
        
        # On-demand metadata fix for existing stories
        needs_save = False
        if story.word_count is None or story.word_count == 0:
            story.word_count = len("\n".join([c.get("text", "") for c in chapters]).split())
            needs_save = True
        if story.chapter_count is None or story.chapter_count == 0:
            story.chapter_count = len(chapters)
            needs_save = True
        if story.status == "generating" and (len(chapters) > 0 or story.voice_key == "none"):
            # Check if it also has an mp3 if voice is needed
            audio_path = settings.AUDIO_OUTPUT_DIR / story_id / "story.mp3"
            if audio_path.exists() or story.voice_key == "none":
                story.status = "done"
                story.progress = "Fertig!"
                story.progress_pct = 100
                needs_save = True
        
        if needs_save:
            logger.info(f"Fixed metadata on-demand for story {story_id}")
            store.add_story(story)

        return {**story.model_dump(), "chapters": chapters}
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

    if req.description is not None:
        # Only owner or admin can change description
        if meta.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Keine Berechtigung.")
        meta.description = req.description

    if req.highlights is not None:
        # Only owner or admin can change highlights
        if meta.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Keine Berechtigung.")
        meta.highlights = req.highlights

    if req.chapters is not None:
        # Only owner or admin can change text
        if meta.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Keine Berechtigung zum Bearbeiten des Textes.")
        
        story_dir = settings.AUDIO_OUTPUT_DIR / story_id
        text_path = story_dir / "story.json"
        
        if not text_path.exists():
            story_data = {"title": meta.title, "chapters": req.chapters}
        else:
            try:
                story_data = json.loads(text_path.read_text(encoding="utf-8"))
                story_data["chapters"] = req.chapters
                if req.title:
                    story_data["title"] = req.title
            except Exception as e:
                logger.error(f"Error reading story.json for update: {e}")
                story_data = {"title": meta.title, "chapters": req.chapters}
        
        # Save updated text
        story_dir.mkdir(parents=True, exist_ok=True)
        text_path.write_text(json.dumps(story_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Invalidate audio: Delete MP3 and chunks
        audio_path = story_dir / "story.mp3"
        if audio_path.exists():
            try:
                audio_path.unlink()
                logger.info(f"Deleted audio for story {story_id} due to text change.")
            except Exception as e:
                logger.error(f"Failed to delete audio file: {e}")

        chunks_dir = story_dir / "chunks"
        if chunks_dir.exists():
            try:
                import shutil
                shutil.rmtree(chunks_dir)
            except Exception as e:
                logger.error(f"Failed to delete chunks directory: {e}")
            
        # Update metadata stats
        total_text = "\n".join([c.get("text", "") for c in req.chapters])
        meta.word_count = len(total_text.split())
        meta.chapter_count = len(req.chapters)
        meta.duration_seconds = 0
        meta.updated_at = datetime.now(timezone.utc)

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
    req: RegenerateImageRequest | None = None,
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
            
            hints = req.image_hints if req else None
            res = await generate_story_image(synopsis, image_path, genre=meta.genre, style=meta.style, image_hints=hints)
            if res:
                image_url = f"/api/stories/{story_id}/image.png"
                meta.image_url = image_url
                meta.updated_at = datetime.now(timezone.utc)
                # Update metadata in store
                store.add_story(meta)
                # Thumbnail
                try:
                    await story_service._generate_thumbnail(image_path, story_dir / "cover_thumb.jpg")
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
            success = await story_service._generate_thumbnail(cover_path, thumb_path)
            if not success:
                # FALLBACK: Serve full image as thumb if generation fails
                logger.info(f"Serving cover.png as fallback for {story_id} because thumb gen failed")
                return FileResponse(cover_path, media_type="image/png")
        except Exception as e:
            logger.warning(f"Reactive thumb gen error: {e}")
            return FileResponse(cover_path, media_type="image/png")
    
    if not thumb_path.exists():
        if cover_path.exists():
            return FileResponse(cover_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    
    return FileResponse(thumb_path, media_type="image/jpeg")


class SpotifyToggleRequest(BaseModel):
    enabled: bool


@app.post("/api/stories/{story_id}/spotify")
async def toggle_spotify(story_id: str, body: SpotifyToggleRequest, current_user: User = Depends(get_current_active_user)):
    """Toggle whether a story is included in the Spotify RSS feed. Restricted to admins."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
        
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
async def get_rss_feed():
    """Serve the global podcast RSS feed (all public/spotify stories)."""
    # Only include stories that have is_on_spotify=True
    stories = store.get_all(only_spotify=True)
    
    logger.info(f"Generating global RSS feed with {len(stories)} stories.")
    
    # Get version for cache busting based on file modification time
    cover_path = Path(__file__).parent / "static" / "podcast-cover.png"
    version = "1.0"
    if cover_path.exists():
        version = str(int(cover_path.stat().st_mtime))
        
    image_url = f"{settings.BASE_URL}/api/podcast-cover.png?v={version}"
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
