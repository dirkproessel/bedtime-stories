import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# load env before importing app modules
load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")

from app.config import settings
from app.services.tts_service import GEMINI_VOICES, generate_voice_preview

async def main():
    preview_dir = settings.AUDIO_OUTPUT_DIR / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Checking previews in {preview_dir} ...")
    
    for key, v in GEMINI_VOICES.items():
        preview_path = preview_dir / f"{key}.mp3"
        if not preview_path.exists() or preview_path.stat().st_size == 0:
            print(f"Generating missing preview for {key} ...")
            try:
                await generate_voice_preview(key, preview_path)
                print(f"  -> Saved {key}.mp3 ({preview_path.stat().st_size} bytes)")
            except Exception as e:
                print(f"  -> Failed to generate preview for {key}: {e}")
        else:
            print(f"Preview for {key} already exists. ({preview_path.stat().st_size} bytes)")

if __name__ == "__main__":
    # Workaround for Windows asyncio bug with ProactorEventLoop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
