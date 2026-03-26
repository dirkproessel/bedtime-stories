import sys
import os
import json
from pathlib import Path

# Add the current directory and its parent to sys.path to ensure imports work
# The script is intended to be run from the 'backend' directory.
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from app.database import engine
from app.models import StoryMeta
from app.config import settings
from sqlmodel import Session, select

def fix_metadata():
    print(f"Starting retroactive metadata fix (DB: {settings.AUDIO_OUTPUT_DIR}/bedtime_stories.db)...")
    
    with Session(engine) as session:
        statement = select(StoryMeta)
        stories = session.exec(statement).all()
        print(f"Found {len(stories)} stories in database.")
        
        fixed_count = 0
        for story in stories:
            print(f"Checking story {story.id}: '{story.title}' (Words: {story.word_count}, Status: {story.status})")
            story_dir = settings.AUDIO_OUTPUT_DIR / story.id
            text_path = story_dir / "story.json"
            
            print(f"  Looking for json at: {text_path.absolute()}")
            
            needs_update = False
            
            if text_path.exists():
                print(f"  Found story.json for {story.id}")
                try:
                    data = json.loads(text_path.read_text(encoding="utf-8"))
                    chapters = data.get("chapters", [])
                    
                    # Calculate word count if missing
                    if story.word_count is None or story.word_count == 0:
                        full_text = "\n".join([c.get("text", "") for c in chapters])
                        words = len(full_text.split())
                        if words > 0:
                            story.word_count = words
                            needs_update = True
                        
                    # Calculate chapter count if missing
                    if story.chapter_count is None or story.chapter_count == 0:
                        if len(chapters) > 0:
                            story.chapter_count = len(chapters)
                            needs_update = True
                        
                    # Fix status if audio exists but status is stuck in 'generating'
                    if story.status == "generating" and (len(chapters) > 0 or story.voice_key == "none"):
                        audio_path = story_dir / "story.mp3"
                        if audio_path.exists() or story.voice_key == "none":
                            story.status = "done"
                            story.progress = "Fertig!"
                            story.progress_pct = 100
                            needs_update = True
                            
                except Exception as e:
                    print(f"Error processing story {story.id}: {e}")
            
            if needs_update:
                session.add(story)
                fixed_count += 1
                print(f"Fixed metadata for story: {story.id} ({story.title}) -> {story.word_count} words")
        
        session.commit()
        print(f"Finished. Successfully fixed {fixed_count} stories.")

if __name__ == "__main__":
    fix_metadata()
