import asyncio
import os
import sys
import json

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.story_generator import inject_speaker_tags_to_story

mock_story = {
    "title": "Kopfsprung Test",
    "synopsis": "Ein Gespräch über Eistee im Garten.",
    "chapters": [
        {
            "title": "Kapitel 1",
            "text": "Anne kam mit einem Glas auf die Terrasse.\n\n„Eistee“, sagte sie. „Selbst gemacht. Mit Minze aus dem Beet, die eigentlich Unkraut ist, aber schmeckt trotzdem.“"
        }
    ]
}

async def main():
    print("--- Running tag injection test ---")
    tagged_story = await inject_speaker_tags_to_story(mock_story, supports_emotions=True)
    for idx, chap in enumerate(tagged_story.get("chapters", [])):
        print(f"\n[Chapter {idx + 1}]:")
        print(repr(chap.get("text")))

if __name__ == "__main__":
    asyncio.run(main())
