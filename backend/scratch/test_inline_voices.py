import asyncio
import os
import sys
import httpx
from pathlib import Path

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.config import settings

VOICE_NARRATOR = "cb55f2fc1a144c74b70ea7fdeb6b9f95" # Jenny (female)
VOICE_CHAR = "3ee58b7440a04e468868eab1a7fff651" # Christoph (male)

async def test_call(text: str, filename: str):
    headers = {
        "Authorization": f"Bearer {settings.FISH_API_KEY.strip()}",
        "Content-Type": "application/json",
        "model": "s2-pro",
    }
    payload = {
        "text": text,
        "reference_id": [VOICE_NARRATOR, VOICE_CHAR],
        "format": "mp3",
        "mp3_bitrate": 128,
    }
    output_path = Path(__file__).parent / filename
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", "https://api.fish.audio/v1/tts", headers=headers, json=payload) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
    print(f"Generated {filename}")

async def main():
    # Test 1: Inline without newlines
    text_no_newline = "<|speaker:1|>„Eistee“, <|speaker:0|> sagte sie. <|speaker:1|>„Selbst gemacht. Mit Minze aus dem Beet, die eigentlich Unkraut ist, aber schmeckt trotzdem.“"
    await test_call(text_no_newline, "test_no_newline.mp3")

    # Test 2: Inline with newlines before tags
    text_newline = "<|speaker:1|>„Eistee“,\n<|speaker:0|> sagte sie.\n<|speaker:1|>„Selbst gemacht. Mit Minze aus dem Beet, die eigentlich Unkraut ist, aber schmeckt trotzdem.“"
    await test_call(text_newline, "test_with_newline.mp3")

if __name__ == "__main__":
    asyncio.run(main())
