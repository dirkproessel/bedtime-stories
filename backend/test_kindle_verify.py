import asyncio
import json
from pathlib import Path
from app.services.kindle_service import generate_epub, send_to_kindle
from app.config import settings

# Sample story data for testing
test_story_data = {
    "title": "Abenteuer im Code-Dschungel",
    "synopsis": "Ein kleiner Programmierer entdeckt die Geheimnisse der EPUB-Erstellung.",
    "chapters": [
        {
            "title": "Kapitel 1: Der erste Import",
            "text": "Es war einmal eine Bibliothek namens ebooklib. Sie war mächtig, aber eigenwillig.\nDer Programmierer tippte mutig in sein Terminal."
        },
        {
            "title": "Kapitel 2: Das Kindle-Format",
            "text": "EPUB ist cool, aber Kindle mag es besonders gern, wenn es per E-Mail kommt. 'Send to Kindle' ist die Zauberformel."
        }
    ]
}

async def verify_kindle_export():
    print("--- Verifying Kindle Export Logic ---")
    
    # Use a dummy ID for testing
    test_id = "test-export"
    test_dir = settings.AUDIO_OUTPUT_DIR / test_id
    test_dir.mkdir(parents=True, exist_ok=True)
    
    epub_path = test_dir / "test_story.epub"
    
    # 1. Test EPUB Generation
    print("Step 1: Generating EPUB...")
    try:
        # Check if we have a podcast cover or something to test image optimization
        cover_src = Path("backend/app/static/podcast-cover.png")
        await generate_epub(test_story_data, cover_src if cover_src.exists() else None, epub_path)
        print(f"EPUB generated at: {epub_path} (Size: {epub_path.stat().st_size} bytes)")
    except Exception as e:
        print(f"EPUB Generation FAILED: {e}")
        return

    # 2. Test Email Logic (Requires PASSWORD to be set in .env)
    if not settings.SMTP_PASSWORD:
        print("\nStep 2: SMTP Test SKIPPED (SMTP_PASSWORD not set in config)")
        print("Set SMTP_PASSWORD in backend/.env to test actual email delivery.")
    else:
        print("\nStep 2: Sending Email to Kindle...")
        try:
            await send_to_kindle(epub_path, settings.KINDLE_EMAIL)
            print("Email sent successfully!")
        except Exception as e:
            print(f"Email sending FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(verify_kindle_export())
