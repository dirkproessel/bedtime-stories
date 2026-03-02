import asyncio
import os
from dotenv import load_dotenv

async def main():
    load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
    
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from app.services.story_generator import _generate_multi_pass
    
    print("Testing multi-pass chapter generator for 20 minutes (4 chapters)...")
    try:
        result = await _generate_multi_pass(
            prompt="Ein kleiner Toaster, der die Welt retten will.",
            genre="Realismus",
            style="Douglas Adams",
            characters=["Toasty"],
            target_minutes=20,
            on_progress=lambda status, msg, pct: asyncio.sleep(0)  # Dummy progress
        )
        print("\n=== SUCCESS ===")
        print(f"Title: {result['title']}")
        print(f"Chapters generated: {len(result['chapters'])}")
        
        total_words = sum(len(c["text"].split()) for c in result['chapters'])
        print(f"Total Words: {total_words}")
        
    except Exception as e:
        print(f"\n=== CRASH ===")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
