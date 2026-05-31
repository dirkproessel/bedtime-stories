import asyncio
import os
import sys
from pathlib import Path
from google import genai
from google.genai import types

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def analyze_audio(filename: str):
    file_path = Path(__file__).parent / filename
    if not file_path.exists():
        print(f"File {filename} not found.")
        return

    print(f"Uploading {filename} to Gemini...")
    audio_file = client.files.upload(file=file_path)
    print(f"Uploaded. Analyzing...")

    prompt = (
        "Analysiere diese Audiodatei. Sag mir:\n"
        "1. Hörst du nur eine einzige Stimme (z.B. nur einen Mann oder nur eine Frau)?\n"
        "2. Oder wechselt die Stimme (z.B. zwischen einer Frau und einem Mann)?\n"
        "Antworte kurz und präzise."
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[audio_file, prompt]
    )
    print(f"--- Analysis for {filename} ---")
    print(response.text)
    print()

    # Clean up uploaded file from Gemini
    client.files.delete(name=audio_file.name)

async def main():
    await analyze_audio("test_no_newline.mp3")
    await analyze_audio("test_with_newline.mp3")

if __name__ == "__main__":
    asyncio.run(main())
