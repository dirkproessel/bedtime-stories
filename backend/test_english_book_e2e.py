import os
import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.models import BookProject, BookSeries, BookChapter, BookProjectCreate, BookSeriesCreate
from app.services.book_generator import (
    format_scene_beats_as_text,
    clean_chapter_prose,
    get_kids_book_prompt
)
from app.services.book_export_service import generate_book_epub, generate_book_txt, generate_book_pdf

def test_models_language_default():
    bp_de = BookProject(user_id="test", title="Deutsches Buch", prompt="Eine Geschichte", genre="Fantasy", style="adams")
    assert bp_de.language == "de", f"Expected default language 'de', got {bp_de.language}"
    
    bp_en = BookProject(user_id="test", title="English Book", prompt="A story", genre="Fantasy", style="adams", language="en")
    assert bp_en.language == "en", f"Expected language 'en', got {bp_en.language}"
    
    bs_de = BookSeries(user_id="test", title="Deutsche Serie", description="Reihe", genre="Sci-Fi", style="king")
    assert bs_de.language == "de", f"Expected default series language 'de', got {bs_de.language}"
    
    bs_en = BookSeries(user_id="test", title="English Series", description="Series", genre="Sci-Fi", style="king", language="en")
    assert bs_en.language == "en", f"Expected series language 'en', got {bs_en.language}"
    print("[PASS] Model & default language tests passed!")

def test_scene_beats_formatting():
    # Test German formatting
    beats_de = [
        {"scene_number": 1, "pov_character": "Max", "setting": "Berlin", "goal": "Finde den Schlüssel", "conflict": "Wächter blockiert", "outcome": "Schlüssel gefunden", "emotional_arc": "Hoffnungsvoll", "estimated_words": "1500"}
    ]
    formatted_de = format_scene_beats_as_text(beats_de, language="de")
    assert "--- Szene 1 ---" in formatted_de
    assert "Ort: Berlin" in formatted_de
    assert "Ziel: Finde den Schlüssel" in formatted_de
    
    # Test English formatting
    beats_en = [
        {"scene_number": 1, "pov_character": "John", "setting": "London", "goal": "Find the key", "conflict": "Guard is blocking", "outcome": "Key found", "emotional_arc": "Hopeful", "estimated_words": "1500"}
    ]
    formatted_en = format_scene_beats_as_text(beats_en, language="en")
    assert "--- Scene 1 ---" in formatted_en
    assert "Setting: London" in formatted_en
    assert "Goal: Find the key" in formatted_en
    assert "Conflict: Guard is blocking" in formatted_en
    assert "Outcome: Key found" in formatted_en
    assert "Words: ~1500" in formatted_en
    print("[PASS] Scene beats formatting (DE & EN) tests passed!")

def test_kids_book_prompt():
    prompt_de = get_kids_book_prompt(is_kids_book=True, language="de")
    assert "KINDERBUCH" in prompt_de
    
    prompt_en = get_kids_book_prompt(is_kids_book=True, language="en")
    assert "KIDS BOOK" in prompt_en
    print("[PASS] Kids book prompt localization tests passed!")

async def test_exports_localization_async():
    mock_project_en = MagicMock()
    mock_project_en.id = "proj-en-123"
    mock_project_en.title = "The Nebula Prophecy"
    mock_project_en.prompt = "An epic space opera across galaxies."
    mock_project_en.genre = "Sci-Fi"
    mock_project_en.style = "asimov"
    mock_project_en.language = "en"
    mock_project_en.epub_author = "Arthur Sterling"
    mock_project_en.epub_dedication = "To all starry dreamers"
    mock_project_en.epub_afterword = "Thank you for reading."
    mock_project_en.epub_imprint = "Published by Storyja Studio"
    mock_project_en.cover_image_url = None
    mock_project_en.previous_summary = None
    mock_project_en.series_id = None
    mock_project_en.series_subtitle = None
    mock_project_en.series_order = None
    
    chapters = [
        MagicMock(chapter_number=1, title="The Signal", content="The deep space antenna blinked into life at 03:00 GMT.")
    ]

    out_dir = Path("backend/scratch")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    txt_path = out_dir / "test_book.txt"
    epub_path = out_dir / "test_book.epub"
    pdf_path = out_dir / "test_book.pdf"

    # Test TXT Export
    generate_book_txt(mock_project_en, chapters, txt_path)
    txt_content = txt_path.read_text(encoding="utf-8")
    assert "THE NEBULA PROPHECY" in txt_content
    assert "by Arthur Sterling" in txt_content
    assert "TABLE OF CONTENTS" in txt_content
    assert "Chapter I" in txt_content
    assert "The Signal" in txt_content
    assert "To all starry dreamers" in txt_content
    assert "AFTERWORD" in txt_content

    # Test EPUB Export
    await generate_book_epub(mock_project_en, chapters, epub_path)
    assert epub_path.exists() and epub_path.stat().st_size > 500, "EPUB file should exist and not be empty"

    # Test PDF Export
    generate_book_pdf(mock_project_en, chapters, pdf_path)
    assert pdf_path.exists() and pdf_path.stat().st_size > 500, "PDF file should exist and not be empty"
    print("[PASS] TXT, EPUB and PDF English export tests passed!")

async def test_kdp_metadata_async():
    from unittest.mock import AsyncMock
    from app.services.book_export_service import generate_kdp_metadata
    
    mock_project_en = MagicMock()
    mock_project_en.id = "proj-en-123"
    mock_project_en.title = "The Nebula Prophecy"
    mock_project_en.prompt = "An epic space opera."
    mock_project_en.genre = "Sci-Fi"
    mock_project_en.style = "asimov"
    mock_project_en.language = "en"
    mock_project_en.series_id = None
    
    chapters = [
        MagicMock(chapter_number=1, title="The Signal", content="The deep space antenna blinked into life at 03:00 GMT.")
    ]

    mock_response = json.dumps({
        "suggested_subtitle": "An Epic Space Opera Odyssey",
        "description_kdp": "<p>When the signal arrives, humanity must choose.</p>",
        "search_keywords": ["space opera", "alien signal", "hard sci fi", "galactic empire", "first contact", "deep space", "space exploration"],
        "recommended_bisac_categories": ["FICTION / Science Fiction / Space Opera", "FICTION / Science Fiction / Hard Science Fiction", "FICTION / Science Fiction / Alien Contact"],
        "pricing_recommendation": {
            "price": "$3.99 USD",
            "reason": "Optimal 70% royalty threshold on Amazon.com"
        }
    })

    with patch("app.services.text_generator.generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_response
        meta = await generate_kdp_metadata(mock_project_en, chapters)
        assert meta["suggested_subtitle"] == "An Epic Space Opera Odyssey"
        assert "$3.99 USD" in meta["pricing_recommendation"]["price"]
        assert len(meta["search_keywords"]) == 7
    print("[PASS] KDP English metadata generator test passed!")

if __name__ == "__main__":
    print("Running English Book & Series E2E Test Suite...")
    test_models_language_default()
    test_scene_beats_formatting()
    test_kids_book_prompt()
    asyncio.run(test_exports_localization_async())
    asyncio.run(test_kdp_metadata_async())
    print("\n[SUCCESS] ALL TESTS PASSED SUCCESSFULLY!")

