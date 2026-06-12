import logging
import asyncio
import httpx
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, Response
from sqlmodel import Session, select
from google import genai
from google.genai import types

from app.database import engine
from app.config import settings
from app.auth_utils import get_current_active_user
from app.models import (
    User,
    BookProject,
    BookChapter,
    BookProjectCreate,
    BookProjectUpdate,
    BookChapterUpdate,
    BookProjectResponse,
    BookProjectDetailResponse,
    BookChapterResponse
)
from app.services.book_generator import (
    suggest_characters,
    generate_outline,
    generate_chapter_content,
    generate_chapter_summary,
    proofread_chapter
)
from app.services.book_export_service import (
    generate_book_epub,
    generate_kdp_metadata
)
from app.services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pro", tags=["pro"])

# Re-use Safety settings for Image Gen from image_generator
from app.services.image_generator import SAFETY_SETTINGS_CONFIG

# --- Background Task Helpers ---

async def bg_generate_chapter(project_id: str, chapter_id: str, model: str, feedback: Optional[str] = None):
    """Generates the chapter prose in the background."""
    with Session(engine) as session:
        project = session.get(BookProject, project_id)
        chapter = session.get(BookChapter, chapter_id)
        if not (project and chapter):
            return
        project.status = "generating"
        project.progress = f"Schreibe Kapitel {chapter.chapter_number}: {chapter.title}..."
        project.progress_pct = 10 + chapter.chapter_number * 10
        chapter.status = "generating"
        session.add(project)
        session.add(chapter)
        session.commit()

    try:
        # Load previous chapters that are completed
        with Session(engine) as session:
            prev_chapters = session.exec(
                select(BookChapter)
                .where(BookChapter.book_project_id == project_id)
                .where(BookChapter.chapter_number < chapter.chapter_number)
                .order_by(BookChapter.chapter_number)
            ).all()
            # De-reference/validate models for background safety
            prev_chapters_list = [BookChapter.model_validate(c) for c in prev_chapters]
            project_validated = BookProject.model_validate(project)
            chapter_validated = BookChapter.model_validate(chapter)

        # Generate the chapter text
        content = await generate_chapter_content(
            project=project_validated,
            chapter=chapter_validated,
            previous_chapters=prev_chapters_list,
            model=model,
            feedback=feedback
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
            session.add(db_chapter)
            session.add(db_project)
            session.commit()
            logger.info(f"Background: Chapter {chapter.chapter_number} written successfully.")
            
    except Exception as e:
        logger.error(f"Background: Chapter {chapter.chapter_number} failed: {e}", exc_info=True)
        with Session(engine) as session:
            db_chapter = session.get(BookChapter, chapter_id)
            db_project = session.get(BookProject, project_id)
            if db_chapter:
                db_chapter.status = "error"
                session.add(db_chapter)
            if db_project:
                db_project.status = "error"
                db_project.progress = f"Fehler bei Kapitel {chapter.chapter_number}: {str(e)}"
                session.add(db_project)
            session.commit()


async def bg_generate_cover(project_id: str, cover_prompt: str):
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
        
        model_id = store.get_system_setting("gemini_image_model", settings.GEMINI_IMAGE_MODEL)
        
        # Enhanced prompt instructions (no typography, KDP spec)
        enhanced_prompt = (
            f"STRICT RULE: NO TEXT, NO WORDS, NO LETTERS, NO SIGNATURES, NO WATERMARKS. "
            f"{cover_prompt}. Beautiful high-quality book cover art. Portrait orientation (2:3 aspect ratio). "
            f"Edge-to-edge full-bleed composition."
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
                        output_path.write_bytes(resp.content)
                        image_path = output_path
        
        # Fallback to Imagen (GenAI client)
        if not image_path and settings.GEMINI_API_KEY:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            image_cfg = types.ImageConfig(aspect_ratio="3:4") if "pro" in model_id.lower() else types.ImageConfig(image_size="512")
            
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
                output_path.write_bytes(image_bytes)
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

@router.post("/books", response_model=BookProjectResponse)
async def create_book_project(req: BookProjectCreate, current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Nur Administratoren dürfen Pro-Buchprojekte erstellen.")
        
    project_id = str(uuid.uuid4())[:8]
    project = BookProject(
        id=project_id,
        user_id=current_user.id,
        title=req.title,
        prompt=req.prompt,
        genre=req.genre,
        style=req.style,
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
        model=model
    )
    return {"suggestions": suggestions}


@router.post("/books/{id}/outline", response_model=BookProjectDetailResponse)
async def api_generate_outline(
    id: str, 
    num_chapters: int = 8, 
    model: str = "gemini-3.1-flash-lite", 
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
        outline_res = await generate_outline(
            prompt=project.prompt,
            genre=project.genre,
            style=project.style,
            characters_bible=bible,
            num_chapters=num_chapters,
            model=model
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
        for ch_data in req_chapters:
            num = ch_data.get("chapter_number")
            chapter = session.exec(
                select(BookChapter)
                .where(BookChapter.book_project_id == id)
                .where(BookChapter.chapter_number == num)
            ).first()
            
            if chapter:
                chapter.title = ch_data.get("title", chapter.title)
                chapter.plot_outline = ch_data.get("plot_outline", chapter.plot_outline)
                session.add(chapter)
            else:
                # Add new if not existing
                new_ch = BookChapter(
                    id=str(uuid.uuid4())[:8],
                    book_project_id=id,
                    chapter_number=num,
                    title=ch_data.get("title", f"Kapitel {num}"),
                    plot_outline=ch_data.get("plot_outline", ""),
                    status="draft"
                )
                session.add(new_ch)
                
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
    bg_tasks.add_task(bg_generate_chapter, id, chapter.id, model, feedback)
    return {"status": "started", "message": f"Kapitel {num} Generierung gestartet."}


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


@router.post("/books/{id}/cover")
async def api_generate_book_cover(
    id: str,
    bg_tasks: BackgroundTasks,
    cover_prompt: str = Query(..., description="Prompt für das Cover-Bild"),
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
    bg_tasks.add_task(bg_generate_cover, id, cover_prompt)
    return {"status": "started", "message": "Cover-Generierung im Hintergrund gestartet."}


@router.get("/books/{id}/cover.jpg")
async def get_book_cover_image(id: str, current_user: User = Depends(get_current_active_user)):
    """Serves the generated book cover image."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin-Zugang verweigert.")
        
    with Session(engine) as session:
        project = session.get(BookProject, id)
        if not project or not project.cover_image_url:
            raise HTTPException(status_code=404, detail="Cover nicht vorhanden.")
            
        cover_path = Path(project.cover_image_url)
        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="Cover-Datei existiert nicht lokal.")
            
        return FileResponse(cover_path, media_type="image/jpeg")


# --- Export Endpoints ---

@router.get("/books/{id}/export/epub")
async def export_book_epub_download(id: str, current_user: User = Depends(get_current_active_user)):
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
