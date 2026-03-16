import asyncio
import os
import json
from dotenv import load_dotenv

async def main():
    load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
    
    import logging
    logging.basicConfig(level=logging.INFO)
    
    from app.services.story_generator import generate_full_story
    
    # Define a simple story to improve
    parent_story = {
        "title": "Der mutige kleine Toaster",
        "synopsis": "Ein Toaster namens Toasty rettet die Küche.",
        "chapters": [
            {"title": "Der Anfang", "text": "Es war einmal ein Toaster namens Toasty. Er lebte in einer gemütlichen Küche in Berlin. Toasty war klein, aber sehr mutig. Eines Tages gab es einen Kurzschluss."}
        ]
    }
    
    print("Testing story improvement (Anpassen)...")
    try:
        # Instruction to change name and location
        further_instructions = "Ändere den Namen von Toasty in 'Bernd' und den Ort von Berlin in 'Hamburg'."
        
        result = await generate_full_story(
            prompt="Der mutige kleine Toaster",
            genre="Realismus",
            style="Neutraler Autor",
            characters=["Toasty"],
            target_minutes=5,
            remix_type="improvement",
            further_instructions=further_instructions,
            parent_text=parent_story,
            on_progress=lambda status, msg, pct: print(f"[{status}] {msg} ({pct}%)")
        )
        
        print("\n=== SUCCESS ===")
        print(f"Original Title: {parent_story['title']}")
        print(f"New Title: {result['title']}")
        print("\n--- Original Text ---")
        print(parent_story['chapters'][0]['text'])
        print("\n--- Improved Text ---")
        print(result['chapters'][0]['text'])
        
        # Verify changes
        improved_text = result['chapters'][0]['text']
        if "Bernd" in improved_text and "Hamburg" in improved_text:
            print("\n✅ Verification passed: Name and location changed.")
        else:
            print("\n❌ Verification failed: Changes not found in improved text.")
            
        if "Toasty" not in improved_text and "Berlin" not in improved_text:
             print("✅ Verification passed: Old name and location removed.")
        else:
             print("⚠️ Warning: Old name or location still present (might be okay if context requires it, but ideally replaced).")

    except Exception as e:
        print(f"\n=== CRASH ===")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
