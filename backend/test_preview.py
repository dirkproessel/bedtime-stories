import asyncio
import os
from pathlib import Path
from app.services.tts_service import generate_voice_preview
from dotenv import load_dotenv

async def main():
    load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
    out = Path("c:/tmp/preview_aoede.mp3")
    print("Testing Aoede preview...")
    await generate_voice_preview("aoede", out)
    print(f"Success! Preview size: {out.stat().st_size} bytes")

if __name__ == "__main__":
    asyncio.run(main())
