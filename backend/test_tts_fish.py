import asyncio
from pathlib import Path
import sys
import os

# Add the app directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.tts_service import generate_tts_chunk
from app.config import settings

async def test_fish_audio():
    print("--- Fish Audio TTS Test ---")
    
    # Ensure API Key is set
    if not settings.FISH_API_KEY:
        print("ERROR: FISH_API_KEY is not set in .env or config.py")
        return

    output_path = Path("test_fish_output.mp3")
    text = "Hallo Dirk! Dies ist ein Test der Fish Audio Integration in deiner Bedtime Stories App. Wenn du das hörst, funktioniert alles perfekt."
    
    print(f"Generating audio for: '{text}'")
    print("Using voice: 'dirk'")
    
    try:
        # We use 'dirk' as the voice_key which we defined in tts_service.py
        path, voice = await generate_tts_chunk(
            text=text,
            output_path=output_path,
            voice_key="dirk"
        )
        print(f"SUCCESS! Audio saved to: {path}")
        print(f"Realized voice: {voice}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_fish_audio())
