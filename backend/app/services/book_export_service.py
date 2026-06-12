import os
import re
import io
import json
import logging
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from ebooklib import epub
from PIL import Image
from app.config import settings
from app.models import BookProject, BookChapter
from app.services.text_generator import generate_text

logger = logging.getLogger(__name__)

def text_to_html_paragraphs(text: str) -> str:
    """Convert raw text to clean HTML paragraph tags."""
    if not text:
        return ""
    # Standardize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    # Split by double newline (paragraphs)
    paragraphs = text.split("\n\n")
    html_paras = []
    for p in paragraphs:
        p_clean = p.strip()
        if p_clean:
            # Replace single newlines within a paragraph with breaks
            p_clean = p_clean.replace("\n", "<br/>")
            html_paras.append(f"<p>{p_clean}</p>")
    return "\n".join(html_paras)

async def generate_book_epub(project: BookProject, chapters: List[BookChapter], output_path: Path):
    """
    Generate a high-quality EPUB file for the book project.
    """
    book = epub.EpubBook()
    
    # Metadata
    book.set_identifier(f"urn:uuid:pro-{project.id}")
    book.set_title(project.title)
    book.set_language('de')
    book.add_author("Stanzwerk Pro - Buch-Labor")
    
    # Add Cover
    cover_loaded = False
    if project.cover_image_url:
        filename = Path(project.cover_image_url).name
        cover_path = settings.AUDIO_OUTPUT_DIR / "books" / filename
        if cover_path.exists():
            try:
                with Image.open(cover_path) as img:
                    img = img.convert("RGB")
                    # Keep aspect ratio but limit size for EPUB efficiency
                    img.thumbnail((800, 1200))
                    
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG', quality=85)
                    
                    book.set_cover("cover.jpg", img_byte_arr.getvalue())
                    cover_loaded = True
                    logger.info("Cover added to EPUB.")
            except Exception as e:
                logger.error(f"Failed to load local cover file: {e}")
                
        # If it's a web URL
        elif project.cover_image_url.startswith("http"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(project.cover_image_url)
                    if resp.status_code == 200:
                        with Image.open(io.BytesIO(resp.content)) as img:
                            img = img.convert("RGB")
                            img.thumbnail((800, 1200))
                            
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='JPEG', quality=85)
                            
                            book.set_cover("cover.jpg", img_byte_arr.getvalue())
                            cover_loaded = True
                            logger.info("Cover downloaded and added to EPUB.")
            except Exception as e:
                logger.error(f"Failed to fetch cover from URL for EPUB: {e}")

    # Styles
    style = """
    @namespace epub "http://www.idpf.org/2007/ops";
    body {
        font-family: Cambria, Georgia, serif;
        margin: 5%;
        text-align: justify;
        line-height: 1.5;
    }
    h1 {
        text-align: center;
        margin-top: 25%;
        font-size: 2em;
        font-weight: bold;
    }
    h2 {
        text-align: center;
        margin-top: 15%;
        margin-bottom: 2em;
        font-size: 1.5em;
        border-bottom: 1px solid #ccc;
        padding-bottom: 0.5em;
    }
    p {
        text-indent: 1.5em;
        margin-bottom: 0;
        margin-top: 0;
    }
    p:first-of-type {
        text-indent: 0;
        margin-top: 1.5em;
    }
    .preface {
        font-style: italic;
        text-align: center;
        margin-bottom: 2em;
    }
    """
    default_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(default_css)

    # Intro Page / Title
    intro_page = epub.EpubHtml(title='Titelblatt', file_name='intro.xhtml', lang='de')
    intro_page.content = f"""
    <div style="text-align: center; margin-top: 20%;">
        <h1>{project.title}</h1>
        <p style="margin-top: 2em; font-weight: bold;">Stanzwerk Pro</p>
        <p style="margin-top: 4em; font-size: 0.9em; color: #666;">Genre: {project.genre} | Stil: {project.style}</p>
        <div style="margin-top: 5em; padding: 20px; border: 1px solid #eee; background-color: #fafafa; text-align: left; font-style: italic;">
            <p><strong>Exzerpt:</strong></p>
            <p>{project.prompt}</p>
        </div>
    </div>
    """
    intro_page.add_item(default_css)
    book.add_item(intro_page)

    # Chapters
    epub_chapters = []
    for c in chapters:
        ch_title = f"Kapitel {c.chapter_number}: {c.title}"
        ch_html = text_to_html_paragraphs(c.content or "Inhalt wird noch generiert.")
        
        epub_ch = epub.EpubHtml(title=c.title, file_name=f'chap_{c.chapter_number}.xhtml', lang='de')
        epub_ch.content = f"""
        <h2>{ch_title}</h2>
        {ch_html}
        """
        epub_ch.add_item(default_css)
        book.add_item(epub_ch)
        epub_chapters.append(epub_ch)

    # Setup Navigation / TOC
    book.toc = (
        epub.Link('intro.xhtml', 'Titelblatt', 'intro'),
        *epub_chapters
    )

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set Spine
    book.spine = ['nav', intro_page] + epub_chapters

    # Write out EPUB
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(output_path, book, {})
    logger.info(f"Pro EPUB successfully written to {output_path}")


async def generate_kdp_metadata(project: BookProject, chapters: List[BookChapter], model: str = "gemini-3.1-flash-lite") -> Dict[str, Any]:
    """
    Generate Amazon KDP compatible copy-paste metadata sheet.
    """
    word_count = sum(len(c.content.split()) for c in chapters if c.content)
    page_est = max(1, round(word_count / 250))
    
    chapter_titles = ", ".join([f"Kapitel {c.chapter_number}: {c.title}" for c in chapters])
    
    system_instruction = (
        "Du bist ein Experte für Amazon Kindle Direct Publishing (KDP). "
        "Erstelle verkaufsoptimierte Metadaten für das hochgeladene Buchprojekt. "
        "Antworte ausschließlich im JSON-Format."
    )
    
    prompt = f"""
    Hier sind die Daten des fertiggestellten Buches:
    - Titel: {project.title}
    - Genre: {project.genre}
    - Stil: {project.style}
    - Wortanzahl: {word_count} (~{page_est} Buchseiten)
    - Kapitelübersicht: {chapter_titles}
    - Beschreibung / Ausgangsidee: {project.prompt}
    
    Erstelle ein JSON-Objekt mit folgenden Feldern auf Deutsch:
    1. 'suggested_subtitle': Ein verkaufsfördernder Untertitel für Amazon (max 200 Zeichen)
    2. 'description_kdp': Ein attraktiver, verkaufsfördernder Klappentext (KDP Buchbeschreibung) in HTML (mit <b>, <i>, <p> Tags, max 2000 Zeichen)
    3. 'search_keywords': Eine Liste von exakt 7 KDP Keywords/Suchbegriffen, die Leser bei Amazon eingeben würden.
    4. 'recommended_bisac_categories': Eine Liste von 3 empfohlenen KDP/BISAC-Kategorien (z. B. Belletristik / Science Fiction / Humoreske)
    5. 'pricing_recommendation': Empfohlener KDP-Preis (in EUR) für das E-Book (0.99 EUR, 2.99 EUR oder 3.99 EUR) mit kurzer Begründung.
    
    Format:
    {{
      "suggested_subtitle": "...",
      "description_kdp": "...",
      "search_keywords": ["...", "...", "...", "...", "...", "...", "..."],
      "recommended_bisac_categories": ["...", "...", "..."],
      "pricing_recommendation": {{
        "price": "2,99 EUR",
        "reason": "..."
      }}
    }}
    """
    
    try:
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction
        )
        from app.services.book_generator import clean_json_string
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error generating KDP metadata: {e}")
        return {
            "suggested_subtitle": f"Eine spannende Novelle im Genre {project.genre}",
            "description_kdp": f"<p>{project.prompt}</p>",
            "search_keywords": [project.genre, project.style, "Novelle", "E-Book", "Roman", "Stanzwerk", "Literatur"],
            "recommended_bisac_categories": ["Belletristik / Allgemein"],
            "pricing_recommendation": {
                "price": "0,99 EUR",
                "reason": "Standard-Einstiegspreis für Kurzromane."
            }
        }
