import asyncio
import os
from pathlib import Path
import sys

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.tts_service import generate_tts_chunk
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    text = "Dies ist ein Test für die Google Flash TTS. Wir überprüfen, ob der Prozess hängen bleibt. " * 5
    out_path = Path("test_output.mp3")
    if out_path.exists():
        out_path.unlink()
    
    print("Starting generation...")
    try:
        await asyncio.wait_for(
            generate_tts_chunk(text, out_path, voice_key="aoede", rate="-5%"),
            timeout=60
        )
        print("Generation finished successfully.")
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
