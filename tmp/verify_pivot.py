import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path.cwd() / "backend"))

from app.services.story_generator import generate_full_story

async def test_generation():
    print("Testing Story Generation with Gemini 3 Flash...")
    try:
        story = await generate_full_story(
            prompt="Ein Toaster gewinnt das Bewusstsein und versucht, die Welt zu verstehen.",
            genre="Sci-Fi",
            style="Douglas Adams",
            target_minutes=5
        )
        print("\n--- RESULTS ---")
        print(f"TITLE: {story['title']}")
        print(f"SYNOPSIS: {story['synopsis']}")
        print(f"TEXT LENGTH: {len(story['chapters'][0]['text'])} characters")
        print("\nPREVIEW:")
        print(story['chapters'][0]['text'][:500] + "...")
        print("---------------")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_generation())
