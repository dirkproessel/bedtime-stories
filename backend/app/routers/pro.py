import logging
from jose import jwt, JWTError
import asyncio
import httpx
import uuid
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Header
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import Session, select
from google import genai
from google.genai import types

from app.database import engine
from app.config import settings
from app.auth_utils import get_current_active_user, SECRET_KEY, ALGORITHM
from app.models import (
    User,
    BookProject,
    BookChapter,
    BookProjectCreate,
    BookProjectUpdate,
    BookOutlineImport,
    BookChapterUpdate,
    BookProjectResponse,
    BookProjectDetailResponse,
    BookChapterResponse,
    KindleExportRequest
)
from app.services.book_generator import (
    suggest_characters,
    generate_outline,
    improve_chapter_outline,
    generate_chapter_content,
    generate_chapter_summary,
    proofread_chapter,
    proofread_book_globally,
    suggest_cover_prompt,
    parse_imported_outline,
    expand_chapter_outline,
    apply_global_feedback_to_outline,
    proofread_outline_globally
)
from app.services.book_export_service import (
    generate_book_epub,
    generate_book_txt,
    generate_book_pdf,
    generate_kdp_metadata
)
from app.services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pro", tags=["pro"])


def _get_kids_flag(genre_config_str: Optional[str]) -> bool:
    """Extract is_kids_book from a genre_config JSON string."""
    if not genre_config_str:
        return False
    try:
        return json.loads(genre_config_str).get("is_kids_book", False)
    except (json.JSONDecodeError, TypeError):
        return False

async def get_admin_user_from_request(
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
) -> User:
    jwt_token = None
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization.split(" ")[1]
    elif token:
        jwt_token = token
        
    if not jwt_token:
        raise HTTPException(status_code=401, detail="Authentication token required")
        
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        return user



def parse_chapter_selection(selection_str: str, max_chapters: int) -> List[int]:
    """
    Parses a string like '4-8', '9;11;13;14', '1,3,5' or combinations and returns a list of chapter numbers.
    Supports comma, semicolon, space as separators.
    """
    if not selection_str or not selection_str.strip():
        return []
        
    # Standardize separators to commas
    s = selection_str.replace(";", ",").replace(" ", ",")
    parts = s.split(",")
    
    selected = set()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-")
                start = int(start_str.strip())
                end = int(end_str.strip())
                if start > end:
                    start, end = end, start
                for num in range(start, end + 1):
                    if 1 <= num <= max_chapters:
                        selected.add(num)
            except ValueError:
                continue
        else:
            try:
                num = int(part)
                if 1 <= num <= max_chapters:
                    selected.add(num)
            except ValueError:
                continue
                
    return sorted(list(selected))


# Re-use Safety settings for Image Gen from image_generator
from app.services.image_generator import SAFETY_SETTINGS_CONFIG

# --- Background Task Helpers ---

async def bg_generate_chapter(project_id: str, chapter_id: str, model: str, feedback: Optional[str] = None, target_words: int = 2000):
    """Generates the chapter prose in the background."""
    with Session(engine) as session:
        project = session.get(BookProject, project_id)
        chapter = session.get(BookChapter, chapter_id)
        if not (project and chapter):
            return
        
        # Capture needed properties immediately to avoid DetachedInstanceError later
        chapter_number = chapter.chapter_number
        chapter_title = chapter.title
        
        project.status = "generating"
        project.progress = f"Schreibe Kapitel {chapter_number}: {chapter_title}..."
        project.progress_pct = 10 + chapter_number * 10
        chapter.status = "generating"
        session.add(project)
        session.add(chapter)
        session.commit()

    try:
        # Load previous chapters that are completed
        with Session(engine) as session:
            db_project = session.get(BookProject, project_id)
            db_chapter = session.get(BookChapter, chapter_id)
            if not (db_project and db_chapter):
                return
                
            prev_chapters = session.exec(
                select(BookChapter)
                .where(BookChapter.book_project_id == project_id)
                .where(BookChapter.chapter_number < chapter_number)
                .order_by(BookChapter.chapter_number)
            ).all()
            
            # De-reference/validate models for background safety while session is active
            prev_chapters_list = [BookChapter.model_validate(c) for c in prev_chapters]
            project_validated = BookProject.model_validate(db_project)
            chapter_validated = BookChapter.model_validate(db_chapter)

        # Generate the chapter text
        content = await generate_chapter_content(
            project=project_validated,
            chapter=chapter_validated,
            previous_chapters=prev_chapters_list,
            model=model,
            feedback=feedback,
            target_words=target_words
        )

        # Generate a summary
        summary = await generate_chapter_summary(content)

        # Save to DB
        with Session(engine) as session:
            db_chapter = session.get(BookChapter, chapter_id)
            db_project = session.get(BookProject, project_id)
            db_chapter.content = content
            db_chapter.running_summary = summary
            db_chapter.status = "done"
            db_project.status = "draft"
            db_project.progress = None
            db_project.progress_pct = 0
            
            if chapter_number == 1 and content:
                from app.services.book_generator import extract_style_samples
                try:
                    samples = await extract_style_samples(content)
                    if samples:
                        existing = db_project.style_bible or ""
                        if "Stilproben aus Kapitel 1" not in existing:
                            db_project.style_bible = (existing + "\n\n--- Stilproben aus Kapitel 1 ---\n" + samples).strip()
                except Exception as ex_style:
                    logger.error(f"Failed to extract style samples in background: {ex_style}")
            
            session.add(db_chapter)
            session.add(db_project)
            session.commit()
            logger.info(f"Background: Chapter {chapter_number} written successfully.")
            
    except Exception as e:
        logger.error(f"Background: Chapter {chapter_number} failed: {e}", exc_info=True)
        with Session(engine) as session:
            db_chapter = session.get(BookChapter, chapter_id)
            db_project = session.get(BookProject, project_id)
            if db_chapter:
                db_chapter.status = "error"
                session.add(db_chapter)
            if db_project:
                db_project.status = "error"
                db_project.progress = f"Fehler bei Kapitel {chapter_number}: {str(e)}"
                session.add(db_project)
            session.commit()


async def bg_generate_all_chapters(
    project_id: str, 
    model: str = "deepseek-v4-pro", 
    target_words: int = 2000,
    chapter_numbers: Optional[List[int]] = None
):
    """Generates chapters sequentially in the background."""
    with Session(engine) as session:
        project = session.get(BookProject, project_id)
        if not project:
            return
        project.status = "generating"
        project.progress = "Starte automatische Generierung..."
        project.progress_pct = 10
        session.add(project)
        session.commit()
        
    try:
        while True:
            # 1. Fetch next draft/error chapter
            with Session(engine) as session:
                project = session.get(BookProject, project_id)
                if not project or project.status != "generating":
                    # Cancelled by user or deleted
                    logger.info("Background: Generation cancelled or project modified.")
                    return
                
                query = select(BookChapter).where(BookChapter.book_project_id == project_id)
                if chapter_numbers is not None:
                    query = query.where(BookChapter.chapter_number.in_(chapter_numbers))
                    
                query = query.where(BookChapter.status.in_(["draft", "error"])).order_by(BookChapter.chapter_number)
                next_chapter = session.exec(query).first()
                
                if not next_chapter:
                    # All target chapters written!
                    break
                
                # Pre-load/verify status
                num = next_chapter.chapter_number
                all_chaps = session.exec(
                    select(BookChapter)
                    .where(BookChapter.book_project_id == project_id)
                ).all()
                total_count = len(all_chaps)
                
                project.progress = f"Schreibe Kapitel {num} von {total_count}: {next_chapter.title}..."
                project.progress_pct = int(10 + (num / max(1, total_count)) * 80)
                next_chapter.status = "generating"
                session.add(project)
                session.add(next_chapter)
                
                # Fetch completed chapters before this one
                prev_chapters = session.exec(
                    select(BookChapter)
                    .where(BookChapter.book_project_id == project_id)
                    .where(BookChapter.chapter_number < num)
                    .order_by(BookChapter.chapter_number)
                ).all()
                prev_chapters_list = [BookChapter.model_validate(c) for c in prev_chapters]
                project_validated = BookProject.model_validate(project)
                chapter_validated = BookChapter.model_validate(next_chapter)
                chapter_id = next_chapter.id
                
                session.commit()

            # 2. Write the chapter
            content = await generate_chapter_content(
                project=project_validated,
                chapter=chapter_validated,
                previous_chapters=prev_chapters_list,
                model=model,
                feedback=None,
                target_words=target_words
            )
            
            # 3. Generate summary
            summary = await generate_chapter_summary(content)
            
            # 4. Save to DB
            with Session(engine) as session:
                db_chapter = session.get(BookChapter, chapter_id)
                db_project = session.get(BookProject, project_id)
                if not db_project or db_project.status != "generating":
                    # Interrupted during generation
                    return
                
                db_chapter.content = content
                db_chapter.running_summary = summary
                db_chapter.status = "done"
                
                if num == 1 and content:
                    from app.services.book_generator import extract_style_samples
                    try:
                        samples = await extract_style_samples(content)
                        if samples:
                            existing = db_project.style_bible or ""
                            if "Stilproben aus Kapitel 1" not in existing:
                                db_project.style_bible = (existing + "\n\n--- Stilproben aus Kapitel 1 ---\n" + samples).strip()
                    except Exception as ex_style:
                        logger.error(f"Failed to extract style samples in bulk background: {ex_style}")
                
                session.add(db_chapter)
                session.add(db_project)
                session.commit()
                logger.info(f"Background: Chapter {num} written sequentially.")
        
        # All chapters generated!
        with Session(engine) as session:
            db_project = session.get(BookProject, project_id)
            if db_project and db_project.status == "generating":
                db_project.status = "draft"
                db_project.progress = None
                db_project.progress_pct = 0
                session.add(db_project)
                session.commit()
                
    except Exception as e:
        logger.error(f"Background sequential write failed: {e}", exc_info=True)
        with Session(engine) as session:
            db_project = session.get(BookProject, project_id)
            if db_project:
                db_project.status = "error"
                db_project.progress = f"Fehler bei automatischer Generierung: {str(e)}"
                session.add(db_project)
            session.commit()



def resize_and_crop_cover(image_bytes: bytes) -> bytes:
    """
    Crops the image from the center to a standard 5:8 book cover aspect ratio (0.625)
    and ensures the minimum height is 1000px and width is 625px.
    """
    from PIL import Image
    import io
    
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    w, h = img.size
    
    target_ratio = 0.625
    current_ratio = w / h
    
    if current_ratio > target_ratio:
        # Image is too wide, crop horizontally
        new_w = int(h * target_ratio)
        offset = (w - new_w) // 2
        img = img.crop((offset, 0, offset + new_w, h))
    else:
        # Image is too tall, crop vertically
        new_h = int(w / target_ratio)
        offset = (h - new_h) // 2
        img = img.crop((0, offset, w, offset + new_h))
        
    new_w, new_h = img.size
    if new_w < 625 or new_h < 1000:
        # Scale up to exactly 625x1000
        img = img.resize((625, 1000), Image.Resampling.LANCZOS)
        
    out_buf = io.BytesIO()
    img.save(out_buf, format='JPEG', quality=95)
    return out_buf.getvalue()


async def bg_generate_cover(project_id: str, cover_prompt: str, model: Optional[str] = None):
    """Generates the book cover image in the background using Fal.ai or Imagen."""
    with Session(engine) as session:
        project = session.get(BookProject, project_id)
        if not project:
            return
        project.status = "generating"
        project.progress = "Cover wird erstellt..."
        project.progress_pct = 85
        session.add(project)
        session.commit()

    try:
        output_filename = f"book_{project_id}_cover.jpg"
        output_path = settings.AUDIO_OUTPUT_DIR / "books" / output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_id = model or store.get_system_setting("gemini_image_model", settings.GEMINI_IMAGE_MODEL)
        
        # Enhanced prompt instructions (KDP spec)
        enhanced_prompt = (
            f"{cover_prompt}. Beautiful high-quality book cover design layout. "
            f"Portrait orientation (2:3 aspect ratio). Edge-to-edge full-bleed composition."
        )

        image_path = None
        # Call Fal.ai if active and key is present
        if ("fal-ai" in model_id.lower() or "flux" in model_id.lower()) and settings.FAL_KEY:
            import fal_client
            result = await fal_client.run_async(
                "fal-ai/flux/schnell",
                arguments={
                    "prompt": enhanced_prompt,
                    "image_size": {"width": 800, "height": 1200}
                }
            )
            if result and "images" in result and len(result["images"]) > 0:
                image_url = result["images"][0]["url"]
                async with httpx.AsyncClient() as client:
                    resp = await client.get(image_url)
                    if resp.status_code == 200:
                        processed_bytes = resize_and_crop_cover(resp.content)
                        output_path.write_bytes(processed_bytes)
                        image_path = output_path
        
        # Fallback to Imagen (GenAI client)
        if not image_path and settings.GEMINI_API_KEY:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            # In Pro Mode, do not limit image size to 512px. Always use aspect_ratio="3:4" to get high-resolution portrait.
            image_cfg = types.ImageConfig(aspect_ratio="3:4")
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model_id,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=image_cfg,
                    safety_settings=SAFETY_SETTINGS_CONFIG,
                )
            )
            
            image_bytes = None
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.inline_data and part.inline_data.data:
                                image_bytes = part.inline_data.data
                                break
                                
            if image_bytes:
                processed_bytes = resize_and_crop_cover(image_bytes)
                output_path.write_bytes(processed_bytes)
                image_path = output_path

        if image_path:
            with Session(engine) as session:
                db_project = session.get(BookProject, project_id)
                db_project.cover_image_url = str(output_path)
                db_project.cover_prompt = cover_prompt
                db_project.status = "draft"
                db_project.progress = None
                db_project.progress_pct = 0
                session.add(db_project)
                session.commit()
                logger.info("Background: Cover generated successfully.")
        else:
            raise ValueError("No image returned from generation APIs.")
            
    except Exception as e:
        logger.error(f"Background: Cover generation failed: {e}", exc_info=True)
        with Session(engine) as session:
            db_project = session.get(BookProject, project_id)
            if db_project:
                db_project.status = "error"
                db_project.progress = f"Cover-Generierungsfehler: {str(e)}"
                session.add(db_project)
                session.commit()


# --- CRUD Endpoints ---

@router.get("/genres/{genre}/profile")
async def api_get_genre_profile(genre: str, current_user: User = Depends(get_current_active_user)):
    """Returns the genre profile configuration for a specific genre."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
    from app.services.genre_profiles import get_genre_profile
    profile = get_genre_profile(genre)
    return profile.model_dump()


@router.post("/books", response_model=BookProjectResponse)
async def create_book_project(req: BookProjectCreate, current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Pro-Buchprojekte erstellen.")
        
    from app.services.story_generator import generate_modular_prompt
    initial_style = generate_modular_prompt(req.style)
    
    project_id = str(uuid.uuid4())[:8]
    project = BookProject(
        id=project_id,
        user_id=current_user.id,
        title=req.title,
        prompt=req.prompt,
        genre=req.genre,
        style=req.style,
        genre_config=req.genre_config,
        style_bible=initial_style,
        status="draft"
    )
    
    with Session(engine) as session:
        session.add(project)
        session.commit()
        session.refresh(project)
        return project


@router.get("/books", response_model=List[BookProjectResponse])
async def list_book_projects(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        projects = session.exec(select(BookProject).order_by(BookProject.created_at.desc())).all()
        return projects


@router.get("/books/{id}", response_model=BookProjectDetailResponse)
async def get_book_project(id: str, current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.put("/books/{id}", response_model=BookProjectResponse)
async def update_book_project(id: str, req: BookProjectUpdate, current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        data = req.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(project, k, v)
            
        project.updated_at = datetime.now(timezone.utc)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project


@router.delete("/books/{id}")
async def delete_book_project(id: str, current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        # Clean up cover if exists
        if project.cover_image_url:
            cover_path = Path(project.cover_image_url)
            if cover_path.exists():
                try:
                    cover_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete cover file {cover_path}: {e}")
                    
        session.delete(project)
        session.commit()
        return {"status": "success", "message": "Buchprojekt und alle Kapitel gelöscht."}


# --- Generation & Interactive Endpoints ---

@router.post("/books/{id}/characters/suggest")
async def api_suggest_characters(
    id: str, 
    model: str = "gemini-3.1-flash-lite", 
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
    suggestions = await suggest_characters(
        prompt=project.prompt,
        genre=project.genre,
        style=project.style,
        model=model,
        is_kids_book=_get_kids_flag(project.genre_config)
    )
    return {"suggestions": suggestions}


@router.post("/books/{id}/outline", response_model=BookProjectDetailResponse)
async def api_generate_outline(
    id: str, 
    num_chapters: int = 8, 
    model: str = "gemini-3.1-flash-lite", 
    instruction: Optional[str] = Query(None, description="Nutzer-Anweisung zur Anpassung der gesamten Gliederung"),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        # Generate outline
        bible = project.characters_bible or "Keine Angabe"
        g_config = json.loads(project.genre_config) if project.genre_config else None
        
        outline_res = await generate_outline(
            prompt=project.prompt,
            genre=project.genre,
            style=project.style,
            characters_bible=bible,
            num_chapters=num_chapters,
            model=model,
            instruction=instruction,
            genre_config=g_config
        )
        
        # Save outline structure to project
        project.title = outline_res.get("title", project.title)
        project.outline = json.dumps(outline_res)
        project.status = "draft"
        session.add(project)
        
        # Remove any existing chapters
        existing_chaps = session.exec(select(BookChapter).where(BookChapter.book_project_id == id)).all()
        for ch in existing_chaps:
            session.delete(ch)
            
        # Create new chapters in draft state
        for ch_data in outline_res.get("chapters", []):
            pov_char = None
            if g_config and g_config.get("pov") == "dual_alternating":
                pov_char = "weiblicher Hauptcharakter" if ch_data.get("chapter_number", 1) % 2 == 1 else "männlicher Hauptcharakter"
            elif g_config and g_config.get("pov") == "single_female":
                pov_char = "weiblicher Hauptcharakter"
            elif g_config and g_config.get("pov") == "single_male":
                pov_char = "männlicher Hauptcharakter"
            elif g_config and g_config.get("pov") == "omniscient":
                pov_char = "Erzähler"
                
            chapter = BookChapter(
                id=str(uuid.uuid4())[:8],
                book_project_id=id,
                chapter_number=ch_data.get("chapter_number"),
                title=ch_data.get("title", f"Kapitel {ch_data.get('chapter_number')}"),
                plot_outline=ch_data.get("plot_outline", ""),
                status="draft",
                pov_character=pov_char
            )
            session.add(chapter)
            
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.post("/books/{id}/outline/import", response_model=BookProjectDetailResponse)
async def api_import_outline(
    id: str,
    req: BookOutlineImport,
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        try:
            outline_res = await parse_imported_outline(req.text, req.model)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        project.title = outline_res.get("title", project.title)
        project.outline = json.dumps(outline_res)
        project.status = "draft"
        project.updated_at = datetime.now(timezone.utc)
        session.add(project)
        
        # Remove any existing chapters
        existing_chaps = session.exec(select(BookChapter).where(BookChapter.book_project_id == id)).all()
        for ch in existing_chaps:
            session.delete(ch)
            
        # Create new chapters in draft state
        for ch_data in outline_res.get("chapters", []):
            chapter = BookChapter(
                id=str(uuid.uuid4())[:8],
                book_project_id=id,
                chapter_number=ch_data.get("chapter_number"),
                title=ch_data.get("title", f"Kapitel {ch_data.get('chapter_number')}"),
                plot_outline=ch_data.get("plot_outline", ""),
                status="draft"
            )
            session.add(chapter)
            
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.put("/books/{id}/outline", response_model=BookProjectDetailResponse)
async def api_update_outline_manually(
    id: str, 
    req_chapters: List[Dict[str, Any]], 
    current_user: User = Depends(get_current_active_user)
):
    """Allows manual editing of outlines for each chapter. Synchronizes outline in project metadata and database chapters."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        # 1. Update project outline JSON
        outline_data = json.loads(project.outline) if project.outline else {"title": project.title}
        outline_data["chapters"] = req_chapters
        project.outline = json.dumps(outline_data)
        session.add(project)
        
        # 2. Synchronize chapters in DB
        active_ids = []
        for ch_data in req_chapters:
            ch_id = ch_data.get("id")
            chapter = None
            if ch_id:
                chapter = session.get(BookChapter, ch_id)
            
            if chapter:
                chapter.chapter_number = ch_data.get("chapter_number")
                chapter.title = ch_data.get("title", chapter.title)
                chapter.plot_outline = ch_data.get("plot_outline", chapter.plot_outline)
                session.add(chapter)
                active_ids.append(chapter.id)
            else:
                new_id = ch_data.get("id") or str(uuid.uuid4())[:8]
                new_ch = BookChapter(
                    id=new_id,
                    book_project_id=id,
                    chapter_number=ch_data.get("chapter_number"),
                    title=ch_data.get("title", f"Kapitel {ch_data.get('chapter_number')}"),
                    plot_outline=ch_data.get("plot_outline", ""),
                    status="draft"
                )
                session.add(new_ch)
                active_ids.append(new_id)

        # 3. Clean up database: delete any chapters that are NOT in active_ids
        db_chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
        ).all()
        for db_ch in db_chapters:
            if db_ch.id not in active_ids:
                session.delete(db_ch)
                
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.post("/books/{id}/chapters/{num}/generate")
async def api_generate_chapter_prose(
    id: str, 
    num: int, 
    bg_tasks: BackgroundTasks,
    model: str = "deepseek-v4-pro",
    feedback: Optional[str] = None,
    target_words: int = Query(2000, description="Zielwortzahl für das Kapitel"),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        chapter = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .where(BookChapter.chapter_number == num)
        ).first()
        
        if not (project and chapter):
            raise HTTPException(status_code=404, detail="Projekt oder Kapitel nicht gefunden.")
            
        if project.status == "generating":
            raise HTTPException(status_code=400, detail="Das Projekt generiert bereits einen Inhalt.")
            
    # Trigger background task
    bg_tasks.add_task(bg_generate_chapter, id, chapter.id, model, feedback, target_words)
    return {"status": "started", "message": f"Kapitel {num} Generierung gestartet."}


@router.post("/books/{id}/generate-all")
async def api_generate_all_chapters_prose(
    id: str,
    bg_tasks: BackgroundTasks,
    mode: str = Query("missing", description="Modus: 'all' (alles neu), 'missing' (nur ungeschriebene), 'custom' (spezifische Kapitel)"),
    custom_chapters: Optional[str] = Query(None, description="Kapitelliste für custom Modus, z.B. '4-8' oder '9;11'"),
    model: str = "deepseek-v4-pro",
    target_words: int = Query(2000, description="Zielwortzahl pro Kapitel"),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
            
        if project.status == "generating":
            raise HTTPException(status_code=400, detail="Das Projekt generiert bereits einen Inhalt.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        total_count = len(chapters)
        
        if total_count == 0:
            raise HTTPException(status_code=400, detail="Keine Kapitel im Projekt vorhanden.")
            
        target_nums = []
        if mode == "all":
            target_nums = [c.chapter_number for c in chapters]
            # Reset all chapters to draft
            for c in chapters:
                c.status = "draft"
                c.content = None
                c.running_summary = None
                session.add(c)
        elif mode == "missing":
            target_nums = [c.chapter_number for c in chapters if c.status != "done"]
            if not target_nums:
                raise HTTPException(status_code=400, detail="Alle Kapitel sind bereits generiert.")
        elif mode == "custom":
            if not custom_chapters:
                raise HTTPException(status_code=400, detail="Bitte gib die gewünschten Kapitel an.")
            target_nums = parse_chapter_selection(custom_chapters, total_count)
            if not target_nums:
                raise HTTPException(status_code=400, detail=f"Ungültige Kapitel-Auswahl. Erlaubt sind Werte von 1 bis {total_count}.")
            # Reset specified chapters to draft
            for c in chapters:
                if c.chapter_number in target_nums:
                    c.status = "draft"
                    c.content = None
                    c.running_summary = None
                    session.add(c)
        else:
            raise HTTPException(status_code=400, detail="Ungültiger Modus.")
            
        session.commit()

    bg_tasks.add_task(bg_generate_all_chapters, id, model, target_words, target_nums)
    return {"status": "started", "message": f"Automatische Generierung gestartet für Kapitel: {target_nums}."}




@router.put("/books/{id}/chapters/{num}", response_model=BookChapterResponse)
async def api_update_chapter_manually(
    id: str, 
    num: int, 
    req: BookChapterUpdate, 
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        chapter = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .where(BookChapter.chapter_number == num)
        ).first()
        
        if not chapter:
            raise HTTPException(status_code=404, detail="Kapitel nicht gefunden.")
            
        data = req.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(chapter, k, v)
            
        chapter.updated_at = datetime.now(timezone.utc)
        session.add(chapter)
        session.commit()
        session.refresh(chapter)
        return chapter


@router.post("/books/{id}/chapters/{num}/outline/improve", response_model=BookProjectDetailResponse)
async def api_improve_chapter_outline(
    id: str,
    num: int,
    instruction: str = Query(..., description="Anweisung zur Verbesserung des Kapitels"),
    model: str = "gemini-3.1-flash-lite",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        chapter = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .where(BookChapter.chapter_number == num)
        ).first()
        
        if not (project and chapter):
            raise HTTPException(status_code=404, detail="Projekt oder Kapitel nicht gefunden.")
            
        bible = project.characters_bible or "Keine Angabe"
        full_outline = project.outline or "{}"
        
        # Improve single chapter outline
        improved = await improve_chapter_outline(
            project_prompt=project.prompt,
            genre=project.genre,
            style=project.style,
            characters_bible=bible,
            full_outline=full_outline,
            chapter_number=num,
            current_title=chapter.title,
            current_plot_outline=chapter.plot_outline,
            instruction=instruction,
            model=model,
            is_kids_book=_get_kids_flag(project.genre_config)
        )
        
        # Save back to database chapter
        chapter.title = improved.get("title", chapter.title)
        chapter.plot_outline = improved.get("plot_outline", chapter.plot_outline)
        chapter.updated_at = datetime.now(timezone.utc)
        session.add(chapter)
        
        # Synchronize project outline JSON
        try:
            outline_data = json.loads(project.outline) if project.outline else {"title": project.title}
            chaps = outline_data.get("chapters", [])
            for c_data in chaps:
                if c_data.get("chapter_number") == num:
                    c_data["title"] = chapter.title
                    c_data["plot_outline"] = chapter.plot_outline
                    break
            outline_data["chapters"] = chaps
            project.outline = json.dumps(outline_data)
            project.updated_at = datetime.now(timezone.utc)
            session.add(project)
        except Exception as e:
            logger.error(f"Error syncing project outline during single chapter improvement: {e}")
            
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.post("/books/{id}/chapters/{num}/outline/expand", response_model=BookProjectDetailResponse)
async def api_expand_chapter_outline(
    id: str,
    num: int,
    model: str = "gemini-3.1-flash-lite",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        chapter = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .where(BookChapter.chapter_number == num)
        ).first()
        
        if not (project and chapter):
            raise HTTPException(status_code=404, detail="Projekt oder Kapitel nicht gefunden.")
            
        bible = project.characters_bible or "Keine Angabe"
        full_outline = project.outline or "{}"
        g_config = json.loads(project.genre_config) if project.genre_config else None
        
        # Expand single chapter outline
        expanded = await expand_chapter_outline(
            project_prompt=project.prompt,
            genre=project.genre,
            style=project.style,
            characters_bible=bible,
            full_outline=full_outline,
            chapter_number=num,
            current_title=chapter.title,
            current_plot_outline=chapter.plot_outline,
            model=model,
            genre_config=g_config
        )
        
        chapter.title = expanded.get("title", chapter.title)
        chapter.plot_outline = expanded.get("plot_outline", chapter.plot_outline)
        if "pov_character" in expanded and expanded["pov_character"]:
            chapter.pov_character = expanded["pov_character"]
        chapter.updated_at = datetime.now(timezone.utc)
        session.add(chapter)
        
        # Sync to project.outline
        try:
            outline_data = json.loads(project.outline) if project.outline else {"title": project.title}
            chaps = outline_data.get("chapters", [])
            for c_data in chaps:
                if c_data.get("chapter_number") == num:
                    c_data["title"] = chapter.title
                    c_data["plot_outline"] = chapter.plot_outline
                    c_data["pov_character"] = chapter.pov_character
                    break
            outline_data["chapters"] = chaps
            project.outline = json.dumps(outline_data)
            project.updated_at = datetime.now(timezone.utc)
            session.add(project)
        except Exception as e:
            logger.error(f"Error syncing project outline: {e}")
            
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.post("/books/{id}/outline/expand", response_model=BookProjectDetailResponse)
async def api_expand_all_outlines(
    id: str,
    model: str = "gemini-3.1-flash-lite",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
        if not project:
            raise HTTPException(status_code=404, detail="Projekt nicht gefunden.")
            
        if not chapters:
            raise HTTPException(status_code=400, detail="Keine Kapitel vorhanden, die erweitert werden können.")
            
        bible = project.characters_bible or "Keine Angabe"
        full_outline = project.outline or "{}"
        g_config = json.loads(project.genre_config) if project.genre_config else None
        
        # Build concurrent tasks for each chapter
        tasks = []
        for ch in chapters:
            tasks.append(
                expand_chapter_outline(
                    project_prompt=project.prompt,
                    genre=project.genre,
                    style=project.style,
                    characters_bible=bible,
                    full_outline=full_outline,
                    chapter_number=ch.chapter_number,
                    current_title=ch.title,
                    current_plot_outline=ch.plot_outline,
                    model=model,
                    genre_config=g_config
                )
            )
            
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update database with results
        outline_chaps = []
        for ch, res in zip(chapters, results):
            if isinstance(res, Exception):
                logger.error(f"Failed to expand chapter {ch.chapter_number}: {res}")
                # Keep original on failure
                outline_chaps.append({
                    "chapter_number": ch.chapter_number,
                    "title": ch.title,
                    "plot_outline": ch.plot_outline,
                    "pov_character": ch.pov_character
                })
                continue
                
            ch.title = res.get("title", ch.title)
            ch.plot_outline = res.get("plot_outline", ch.plot_outline)
            if "pov_character" in res and res["pov_character"]:
                ch.pov_character = res["pov_character"]
            ch.updated_at = datetime.now(timezone.utc)
            session.add(ch)
            
            outline_chaps.append({
                "chapter_number": ch.chapter_number,
                "title": ch.title,
                "plot_outline": ch.plot_outline,
                "pov_character": ch.pov_character
            })
            
        # Update project outline JSON
        try:
            outline_data = json.loads(project.outline) if project.outline else {"title": project.title}
            outline_data["chapters"] = outline_chaps
            project.outline = json.dumps(outline_data)
            project.updated_at = datetime.now(timezone.utc)
            session.add(project)
        except Exception as e:
            logger.error(f"Error syncing project outline during bulk expand: {e}")
            
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)



@router.post("/books/{id}/chapters/{num}/proofread")
async def api_proofread_chapter(
    id: str, 
    num: int, 
    model: str = "gemini-3.5-flash",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        chapter = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .where(BookChapter.chapter_number == num)
        ).first()
        
        if not (project and chapter):
            raise HTTPException(status_code=404, detail="Projekt oder Kapitel nicht gefunden.")
            
        if not chapter.content:
            raise HTTPException(status_code=400, detail="Kapitel hat keinen Inhalt zum Lektorieren.")
            
        bible = project.characters_bible or "Keine Angabe"
        outline = project.outline or "{}"
        
    findings = await proofread_chapter(
        chapter_content=chapter.content,
        characters_bible=bible,
        outline=outline,
        chapter_num=num,
        model=model
    )
    return {"findings": findings}


@router.post("/books/{id}/proofread/global")
async def api_proofread_book_globally(
    id: str, 
    model: str = "gemini-3.5-flash",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
        bible = project.characters_bible or "Keine Angabe"
        outline = project.outline or "{}"
        
        # Snapshot chapters to avoid DetachedInstanceError outside the session block
        chapters_snapshot = []
        for c in chapters:
            chapters_snapshot.append(BookChapter(
                chapter_number=c.chapter_number,
                title=c.title,
                content=c.content or ""
            ))
            
    findings = await proofread_book_globally(
        chapters=chapters_snapshot,
        characters_bible=bible,
        outline=outline,
        model=model
    )
    return {"findings": findings}


class ApplyGlobalFeedbackRequest(BaseModel):
    findings: List[Dict[str, Any]]


@router.post("/books/{id}/outline/apply-global-feedback", response_model=BookProjectDetailResponse)
async def api_apply_global_feedback_to_outline(
    id: str,
    req: ApplyGlobalFeedbackRequest,
    model: str = "gemini-3.5-flash",
    current_user: User = Depends(get_current_active_user)
):
    """
    Applies the global proofreading findings to the project's detailed outlines (blueprints)
    and synchronizes them in the database.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        bible = project.characters_bible or "Keine Angabe"
        outline = project.outline or "{}"
        
    # Run the correction LLM task
    updated_outline_str = await apply_global_feedback_to_outline(
        characters_bible=bible,
        current_outline=outline,
        findings=req.findings,
        model=model
    )
    
    # Save the updated outline back to project and sync DB chapters
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        try:
            outline_data = json.loads(updated_outline_str)
            req_chapters = outline_data.get("chapters", [])
        except Exception as e:
            logger.error(f"Error parsing corrected outline JSON: {e}. Raw: {updated_outline_str}")
            raise HTTPException(
                status_code=500, 
                detail=f"Die KI hat keine gültige JSON-Gliederung geliefert. Details: {str(e)}"
            )
            
        project.outline = updated_outline_str
        session.add(project)
        
        # Synchronize chapter details in DB
        for ch_data in req_chapters:
            chapter_number = ch_data.get("chapter_number")
            if chapter_number is None:
                continue
                
            chapter = session.exec(
                select(BookChapter)
                .where(BookChapter.book_project_id == id)
                .where(BookChapter.chapter_number == chapter_number)
            ).first()
            
            if chapter:
                chapter.plot_outline = ch_data.get("plot_outline", chapter.plot_outline)
                chapter.title = ch_data.get("title", chapter.title)
                session.add(chapter)
                
        session.commit()
        session.refresh(project)
        return BookProjectDetailResponse.model_validate(project, from_attributes=True)


@router.post("/books/{id}/outline/proofread")
async def api_proofread_outline_globally(
    id: str, 
    model: str = "gemini-3.5-flash",
    current_user: User = Depends(get_current_active_user)
):
    """
    Checks the consistency and logic of the chapter outlines (blueprints) in Step 2.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
        bible = project.characters_bible or "Keine Angabe"
        
        # Snapshot chapters to avoid DetachedInstanceError outside session block
        chapters_snapshot = []
        for c in chapters:
            chapters_snapshot.append(BookChapter(
                chapter_number=c.chapter_number,
                title=c.title,
                plot_outline=c.plot_outline or ""
            ))
            
    findings = await proofread_outline_globally(
        chapters=chapters_snapshot,
        characters_bible=bible,
        model=model
    )
    return {"findings": findings}


@router.post("/books/{id}/cover/suggest")
async def api_suggest_book_cover_prompt(
    id: str,
    model: str = "gemini-3.1-flash-lite",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        title = project.title
        prompt = project.prompt
        genre = project.genre
        style = project.style
        
    suggested = await suggest_cover_prompt(
        title=title,
        prompt=prompt,
        genre=genre,
        style=style,
        model=model
    )
    return {"suggested_prompt": suggested}


@router.post("/books/{id}/cover")
async def api_generate_book_cover(
    id: str,
    bg_tasks: BackgroundTasks,
    cover_prompt: str = Query(..., description="Prompt für das Cover-Bild"),
    model: Optional[str] = Query(None, description="Modell für die Cover-Generierung"),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        if project.status == "generating":
            raise HTTPException(status_code=400, detail="Das Projekt generiert bereits einen Inhalt.")
            
    # Trigger background cover generation
    bg_tasks.add_task(bg_generate_cover, id, cover_prompt, model)
    return {"status": "started", "message": "Cover-Generierung im Hintergrund gestartet."}


@router.get("/books/{id}/cover.jpg")
async def get_book_cover_image(id: str, current_user: User = Depends(get_admin_user_from_request)):
    """Serves the generated book cover image."""
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project or not project.cover_image_url:
            raise HTTPException(status_code=404, detail="Cover nicht vorhanden.")
            
        # Robust path resolution to handle Windows vs Linux path differences in database
        filename = Path(project.cover_image_url).name
        cover_path = settings.AUDIO_OUTPUT_DIR / "books" / filename
        
        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="Cover-Datei existiert nicht lokal.")
            
        return FileResponse(cover_path, media_type="image/jpeg")


# --- Export Endpoints ---

@router.get("/books/{id}/export/epub")
async def export_book_epub_download(id: str, current_user: User = Depends(get_admin_user_from_request)):
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
    # Generate temporary EPUB inside settings.AUDIO_OUTPUT_DIR/books
    epub_filename = f"book_{id}_{uuid.uuid4().hex[:6]}.epub"
    epub_path = settings.AUDIO_OUTPUT_DIR / "books" / epub_filename
    
    await generate_book_epub(project, chapters, epub_path)
    
    # Return as download response
    safe_title = re.sub(r'[^\w\s-]', '', project.title).strip().replace(' ', '_')
    return FileResponse(
        epub_path,
        media_type="application/epub+zip",
        filename=f"{safe_title}.epub"
    )


@router.post("/books/{id}/export/kindle")
async def export_book_kindle(
    id: str,
    req: KindleExportRequest,
    current_user: User = Depends(get_admin_user_from_request)
):
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
    # Generate temporary EPUB inside settings.AUDIO_OUTPUT_DIR/books
    epub_filename = f"book_{id}_{uuid.uuid4().hex[:6]}.epub"
    epub_path = settings.AUDIO_OUTPUT_DIR / "books" / epub_filename
    
    await generate_book_epub(project, chapters, epub_path)
    
    # Send via SMTP
    from app.services.kindle_service import send_to_kindle
    await send_to_kindle(epub_path, req.email, project.title)
    
    return {"status": "success", "message": f"Buch an {req.email} gesendet"}


@router.get("/books/{id}/export/txt")
async def export_book_txt_download(id: str, current_user: User = Depends(get_admin_user_from_request)):
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
    txt_filename = f"book_{id}_{uuid.uuid4().hex[:6]}.txt"
    txt_path = settings.AUDIO_OUTPUT_DIR / "books" / txt_filename
    
    generate_book_txt(project, chapters, txt_path)
    
    safe_title = re.sub(r'[^\w\s-]', '', project.title).strip().replace(' ', '_')
    return FileResponse(
        txt_path,
        media_type="text/plain; charset=utf-8",
        filename=f"{safe_title}.txt"
    )


@router.get("/books/{id}/export/pdf")
async def export_book_pdf_download(id: str, current_user: User = Depends(get_admin_user_from_request)):
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
    pdf_filename = f"book_{id}_{uuid.uuid4().hex[:6]}.pdf"
    pdf_path = settings.AUDIO_OUTPUT_DIR / "books" / pdf_filename
    
    generate_book_pdf(project, chapters, pdf_path)
    
    safe_title = re.sub(r'[^\w\s-]', '', project.title).strip().replace(' ', '_')
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{safe_title}.pdf"
    )


@router.get("/books/{id}/export/metadata")
async def export_book_kdp_metadata(
    id: str, 
    model: str = "gemini-3.1-flash-lite", 
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .order_by(BookChapter.chapter_number)
        ).all()
        
    metadata = await generate_kdp_metadata(project, chapters, model=model)
    return metadata


@router.post("/books/{id}/style/suggest")
async def api_suggest_style_refinement(
    id: str,
    model: str = "gemini-3.1-flash-lite",
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
            
        current_style = project.style_bible
        if not current_style:
            from app.services.story_generator import generate_modular_prompt
            current_style = generate_modular_prompt(project.style)
            
        genre = project.genre
        prompt = project.prompt
        
    # Ask the LLM to refine the style guidelines into more detailed, professional instructions
    system_instruction = (
        "Du bist ein erfahrener Schreibcoach und Lektor. "
        "Optimiere und verfeinere die Stil-Vorgaben für ein Buchprojekt. "
        "Füge konkrete, professionelle Schreibtipps hinzu, die zum gewünschten Autorenstil passen."
    )
    
    prompt_content = f"""
    Hier sind die aktuellen Stil-Vorgaben für das Buch:
    \"\"\"
    {current_style}
    \"\"\"
    
    Das Buch hat das Genre: {genre}
    Ursprungsidee: {prompt}
    
    Aufgabe:
    Erweitere diese Stil-Vorgaben um konkrete, umsetzbare Tipps (z.B. Satzbau, Atmosphäre, Wortwahl, Dialoge).
    Halte die Struktur übersichtlich (z.B. mit Stichpunkten). 
    Schreibe auf Deutsch. Antworte direkt mit den neuen Stil-Vorgaben. Verwende keine einleitenden Floskeln.
    """
    
    try:
        from app.services.text_generator import generate_text
        refined = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.7,
            system_instruction=system_instruction
        )
        return {"suggested_style": refined.strip()}
    except Exception as e:
        logger.error(f"Failed to suggest style refinement: {e}")
        raise HTTPException(status_code=500, detail=f"Fehler bei KI-Generierung: {str(e)}")


@router.post("/books/{id}/cancel")
async def api_cancel_project_generation(
    id: str,
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
        project.status = "draft"
        project.progress = None
        project.progress_pct = 0
        
        # Reset any chapter in generating status back to draft
        generating_chapters = session.exec(
            select(BookChapter)
            .where(BookChapter.book_project_id == id)
            .where(BookChapter.status == "generating")
        ).all()
        for ch in generating_chapters:
            ch.status = "draft"
            session.add(ch)
            
        session.add(project)
        session.commit()
        return {"status": "success", "message": "Generierung abgebrochen und Status zurückgesetzt."}


from pydantic import BaseModel, Field

class EpubMetadataSuggestionSchema(BaseModel):
    epub_author: str = Field(description="Ein Autorenname / Pseudonym für das Buch (Vorschlag: 'Stanzwerk Pro' oder ein passender Künstlername, max 30 Zeichen)")
    epub_dedication: str = Field(description="Eine kurze, poetische Widmung (2-4 Zeilen)")
    epub_afterword: str = Field(description="Ein kurzes Nachwort (100-150 Wörter)")
    epub_imprint: str = Field(description="Ein optionaler Impressums-Zusatz (z. B. Datenschutzhinweis oder Haftungsausschluss, oder leer lassen)")


@router.post("/books/{id}/epub/suggest")
async def api_suggest_epub_metadata(
    id: str,
    model: str = "gemini-3.1-flash-lite",
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate AI-suggested content for EPUB front/back matter:
    - epub_author: default author display name
    - epub_dedication: poetic dedication text
    - epub_afterword: short afterword / Nachwort
    - epub_imprint: optional extra imprint paragraph
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")

    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project:
            raise HTTPException(status_code=404, detail="Buchprojekt nicht gefunden.")
        title = project.title
        genre = project.genre
        style = project.style
        prompt_idea = project.prompt

    from app.services.text_generator import generate_text

    system_instruction = (
        "Du bist ein erfahrener Buchautor und Verlags-Lektor. "
        "Erstelle kurze, professionelle Texte für ein Buchprojekt. "
        "Antworte ausschließlich im JSON-Format."
    )

    ai_prompt = f"""
Hier sind die Daten des Buchprojekts:
- Titel: {title}
- Genre: {genre}
- Stil: {style}
- Buchidee / Prämisse: {prompt_idea}

Erstelle ein JSON-Objekt mit folgenden Feldern auf Deutsch:

1. "epub_author": Ein Autorenname / Pseudonym für das Buch (Vorschlag: "Stanzwerk Pro" oder ein passender Künstlername, max 30 Zeichen)
2. "epub_dedication": Eine kurze, poetische Widmung (2–4 Zeilen, passend zum Genre/Thema)  
3. "epub_afterword": Ein kurzes Nachwort (100–150 Wörter), das das Thema und die Entstehungsgeschichte des Buches reflektiert
4. "epub_imprint": Ein optionaler Impressums-Zusatz (z.B. ein Datenschutzhinweis oder Haftungsausschluss, 1–2 Sätze, oder leer lassen)

Format:
{{
  "epub_author": "...",
  "epub_dedication": "...",
  "epub_afterword": "...",
  "epub_imprint": "..."
}}
"""

    try:
        from app.services.book_generator import clean_json_string
        raw = await generate_text(
            prompt=ai_prompt,
            model=model,
            temperature=0.8,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=EpubMetadataSuggestionSchema
        )
        cleaned = clean_json_string(raw)
        result = json.loads(cleaned)
        return result
    except Exception as e:
        logger.error(f"Failed to suggest EPUB metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"KI-Generierung fehlgeschlagen: {str(e)}")


