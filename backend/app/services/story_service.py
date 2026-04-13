import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models import StoryMeta, User
from app.services.store import store
from app.services.tts_service import get_available_voices, chapters_to_audio
from app.services.story_generator import generate_full_story, get_author_names
from app.services.image_generator import generate_story_image
from app.services.audio_processor import merge_audio_files, get_audio_duration

logger = logging.getLogger(__name__)

# Global state for in-memory status
_generation_status: dict[str, dict] = {}

class StoryService:
    def get_status(self, story_id: str) -> dict | None:
        return _generation_status.get(story_id)

    async def _generate_thumbnail(self, source: Path, dest: Path, size: int = 400):
        def _resize():
            try:
                from PIL import Image
                with Image.open(source) as img:
                    img = img.convert("RGB")
                    img.thumbnail((size, size), Image.LANCZOS)
                    img.save(dest, "JPEG", quality=80, optimize=True)
                return True
            except Exception as e:
                logger.error(f"Thumbnail generation failed: {e}")
                return False
        return await asyncio.to_thread(_resize)

    async def run_pipeline(
        self,
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
        alexa_user_id: str | None = None,
    ):
        """Full pipeline: text → TTS → merge → save."""
        logger.info(f"!!! STARTING PIPELINE for story {story_id} (Alexa: {alexa_user_id}) !!!")
        
        story_dir = settings.AUDIO_OUTPUT_DIR / story_id
        story_dir.mkdir(parents=True, exist_ok=True)

        voice_name = "Unbekannt"
        all_voices = get_available_voices(user_id=user_id)
        for v in all_voices:
            if v["key"] == voice_key:
                voice_name = v["name"]
                break

        clean_prompt = original_prompt or prompt
        if "Kurzgeschichte im Genre" in clean_prompt and "Idee:" in clean_prompt:
            clean_prompt = clean_prompt.split("Idee:", 1)[-1].strip()
        
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
        
        _generation_status[story_id] = {
            "status": "starting",
            "progress": "Starte Generierung...",
            "title": None,
        }

        estimated_chapters = max(2, target_minutes // 5)
        total_points = 5 + (10 * estimated_chapters) + 5
        if voice_key != "none":
            total_points += (20 * estimated_chapters) + 10
            
        completed_points = 0
        image_task = None
        image_url = None

        async def background_image_gen(synopsis_for_image: str):
            nonlocal image_url
            try:
                image_path = story_dir / "cover.png"
                res = await generate_story_image(synopsis_for_image, image_path, genre=genre, style=style)
                if res:
                    image_url = f"/api/stories/{story_id}/image.png"
                    await self._generate_thumbnail(image_path, story_dir / "cover_thumb.jpg")
                    curr = store.get_by_id(story_id)
                    if curr:
                        curr.image_url = image_url
                        store.add_story(curr)
            except Exception as e:
                logger.error(f"Image gen failed: {e}")

        async def on_progress(status_type: str, message: str, points: int | None = None, is_absolute_points: bool = False, **kwargs):
            nonlocal completed_points, image_task
            logger.info(f"PIPELINE PROGRESS [{story_id}]: {status_type} - {message} (Points: {points})")
            if points is not None:
                if is_absolute_points: completed_points = points
                else: completed_points += points
            
            # Use total_points defensively to avoid zero division
            safe_total = max(total_points, 1)
            pct = min(int((completed_points / safe_total) * 100), 99)
            
            label = message
            if status_type == "generating_text": label = "Texterstellung"
            elif status_type in ["generating_image", "image"]: label = "Bilderstellung"
            elif status_type in ["generating_audio", "tts"]: label = "Vertonung"
            elif status_type == "processing": label = "Finalisierung"
            
            # Extract synopsis for image generation if we find it
            synopsis_val = kwargs.get("synopsis")
            if (status_type in ["outline_done", "generating_text"]) and synopsis_val and not image_task:
                logger.info(f"PIPELINE [{story_id}]: Starting background image generation task.")
                image_task = asyncio.create_task(background_image_gen(synopsis_val))
            
            _generation_status[story_id].update({
                "status": status_type,
                "progress": label,
                "progress_pct": pct,
                **kwargs
            })

            try:
                curr = store.get_by_id(story_id)
                if curr:
                    curr.status = "generating" if status_type not in ["done", "error"] else status_type
                    curr.progress = label
                    curr.progress_pct = pct
                    if "title" in kwargs: curr.title = kwargs.get("title")
                    if "synopsis" in kwargs: curr.description = kwargs.get("synopsis")
                    store.add_story(curr)
                else:
                    logger.warning(f"PIPELINE [{story_id}]: Story object not found in store for progress update!")
            except Exception as e:
                logger.error(f"PIPELINE [{story_id}]: Failed to update progress in store: {e}")

        try:
            start_time_total = time.time()
            logger.info(f"PIPELINE [{story_id}]: Pipeline execution started.")
            await on_progress("planning", "Planung", points=5, is_absolute_points=True)

            # Phase 2: Text
            completed_text_chapters = 0
            async def text_progress_wrapper(stype, msg, pct=None, **kwargs):
                nonlocal completed_text_chapters
                if stype == "text_chapter_done":
                    completed_text_chapters += 1
                    await on_progress("generating_text", "Texterstellung", points=5 + (10 * completed_text_chapters), is_absolute_points=True, **kwargs)
                elif stype == "outline_done":
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
            real_num_chapters = len(story_data["chapters"])
            
            # Recalculate total points
            total_points = 5 + (10 * real_num_chapters) + 5
            if voice_key != "none": total_points += (20 * real_num_chapters) + 10
            
            await on_progress("generating_text", "Texterstellung", points=5 + (10 * real_num_chapters), is_absolute_points=True)

            text_path = story_dir / "story.json"
            text_path.write_text(json.dumps(story_data, ensure_ascii=False, indent=2), encoding="utf-8")

            # Phase 4: Audio
            if voice_key == "none":
                if image_task: await image_task
                
                curr = store.get_by_id(story_id)
                if curr:
                    curr.duration_seconds = 0
                    curr.chapter_count = real_num_chapters
                    curr.word_count = len("\n".join([c["text"] for c in story_data["chapters"]]).split())
                    curr.status = "done"
                    curr.progress = "Fertig!"
                    curr.progress_pct = 100
                    store.add_story(curr)
                
                await on_progress("done", "Fertig!", points=total_points, is_absolute_points=True)
                return

            await on_progress("image", "Bilderstellung", points=5)
            
            async def tts_progress_wrapper(stype, msg, extra_data=None):
                if stype == "tts_chunk_done" and extra_data:
                    completed = extra_data["completed"]
                    total = extra_data["total"]
                    chunk_points = int((completed / max(total, 1)) * 20 * real_num_chapters)
                    await on_progress("generating_audio", "Vertonung", points=5 + (10 * real_num_chapters) + 5 + chunk_points, is_absolute_points=True)

            chunks_dir = story_dir / "chunks"
            audio_files, actual_voice = await chapters_to_audio(
                chapters=story_data["chapters"],
                output_dir=chunks_dir,
                voice_key=voice_key,
                rate=speech_rate,
                genre=genre,
                on_progress=tts_progress_wrapper,
                synopsis=story_data.get("synopsis"),
                title=story_data.get("title"),
            )

            await on_progress("processing", "Finalisierung", points=total_points - 10, is_absolute_points=True)
            
            final_audio_path = story_dir / "story.mp3"
            await merge_audio_files(audio_files, final_audio_path, settings.INTRO_MUSIC_PATH, settings.OUTRO_MUSIC_PATH)

            duration = await get_audio_duration(final_audio_path)
            if image_task: await image_task

            curr = store.get_by_id(story_id)
            if curr:
                curr.duration_seconds = duration
                curr.chapter_count = real_num_chapters
                curr.word_count = len("\n".join([c["text"] for c in story_data["chapters"]]).split())
                curr.status = "done"
                curr.progress = "Fertig!"
                curr.progress_pct = 100
                store.add_story(curr)

            await on_progress("done", "Fertig!", points=total_points, is_absolute_points=True)

            # BENCHMARK
            logger.info(f"BENCHMARK [{story_id}]: Total Pipeline Finished in {time.time() - start_time_total:.2f}s")


            logger.info(f"BENCHMARK [{story_id}]: Total Pipeline Finished in {time.time() - start_time_total:.2f}s")

        except Exception as e:
            logger.error(f"Pipeline error for {story_id}: {e}", exc_info=True)
            await on_progress("error", f"Fehler: {str(e)}")

    async def run_revoice_pipeline(self, story_id: str, voice_key: str, speech_rate: str):
        """Revoice pipeline: load text → TTS → merge → save."""
        story_dir = settings.AUDIO_OUTPUT_DIR / story_id
        text_path = story_dir / "story.json"
        
        if not text_path.exists():
            logger.error(f"Cannot revoice: {text_path} missing")
            return

        story_data = json.loads(text_path.read_text(encoding="utf-8"))
        num_chapters = len(story_data["chapters"])
        
        # Recalculate word count from existing story.json
        total_text = "\n".join([c.get("text", "") for c in story_data.get("chapters", [])])
        word_count = len(total_text.split())

        # Vertonung: 10 * num_chapters
        # Finalisierung: 10
        total_points = (10 * num_chapters) + 10
        completed_points = 0

        _generation_status[story_id] = {
            "status": "starting",
            "progress": "Starte Neuvertonung...",
            "title": story_data.get("title"),
        }

        async def on_progress(status_type: str, message: str, points: int | None = None, is_absolute_points: bool = False):
            nonlocal completed_points
            if points is not None:
                if is_absolute_points: completed_points = points
                else: completed_points += points
            
            pct = min(int((completed_points / total_points) * 100), 99)
            label = message
            if status_type in ["generating_audio", "tts"]: label = "Vertonung"
            elif status_type == "processing": label = "Finalisierung"

            _generation_status[story_id].update({
                "status": status_type,
                "progress": label,
                "progress_pct": pct
            })
            
            curr = store.get_by_id(story_id)
            if curr:
                curr.status = "generating" if status_type not in ["done", "error"] else status_type
                curr.progress = label
                curr.progress_pct = pct
                store.add_story(curr)

        async def tts_progress_wrapper(stype, msg, extra_data=None):
            if stype == "tts_chunk_done" and extra_data:
                completed = extra_data["completed"]
                total = extra_data["total"]
                chunk_points = int((completed / max(total, 1)) * 10 * num_chapters)
                await on_progress("generating_audio", "Vertonung", points=chunk_points, is_absolute_points=True)

        try:
            await on_progress("generating_audio", "Vertonung")
            chunks_dir = story_dir / "chunks"
            import shutil
            if chunks_dir.exists():
                shutil.rmtree(chunks_dir)
            chunks_dir.mkdir(parents=True, exist_ok=True)

            story_meta_for_genre = store.get_by_id(story_id)
            audio_files, actual_voice = await chapters_to_audio(
                chapters=story_data["chapters"],
                output_dir=chunks_dir,
                voice_key=voice_key,
                rate=speech_rate,
                genre=story_meta_for_genre.genre if story_meta_for_genre else None,
                on_progress=tts_progress_wrapper,
                synopsis=story_data.get("synopsis"),
                title=story_data.get("title"),
            )

            await on_progress("processing", "Finalisierung", points=10 * num_chapters, is_absolute_points=True)
            
            final_audio_path = story_dir / "story.mp3"
            await merge_audio_files(audio_files, final_audio_path, settings.INTRO_MUSIC_PATH, settings.OUTRO_MUSIC_PATH)

            duration = await get_audio_duration(final_audio_path)
            curr = store.get_by_id(story_id)
            all_voices = get_available_voices(user_id=curr.user_id if curr else None)
            actual_voice_name = next((v["name"] for v in all_voices if v["key"] == actual_voice), "Unbekannt")

            await on_progress("done", "Fertig!", points=total_points, is_absolute_points=True)

            if curr:
                curr.duration_seconds = duration
                curr.voice_key = actual_voice
                curr.voice_name = actual_voice_name
                curr.word_count = word_count
                curr.chapter_count = num_chapters
                curr.status = "done"
                curr.progress = "Fertig!"
                curr.progress_pct = 100
                store.add_story(curr)

        except Exception as e:
            logger.error(f"Revoice error for {story_id}: {e}", exc_info=True)
            await on_progress("error", f"Neuvertonung fehlgeschlagen: {e}")

story_service = StoryService()
