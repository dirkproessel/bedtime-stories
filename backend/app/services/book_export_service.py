import re
import io
import json
import logging
import httpx
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from ebooklib import epub
from PIL import Image
from app.config import settings
from app.models import BookProject, BookChapter
from app.services.text_generator import generate_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Roman numeral helper
# ---------------------------------------------------------------------------

def to_roman(num: int) -> str:
    """Convert integer to Roman numeral string (e.g. 3 -> 'III')."""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
    result = ''
    for i in range(len(val)):
        while num >= val[i]:
            result += syms[i]
            num -= val[i]
    return result


# ---------------------------------------------------------------------------
# Text → HTML conversion
# ---------------------------------------------------------------------------

def text_to_html_paragraphs(text: str) -> str:
    """
    Convert raw prose text to clean semantic HTML paragraphs.

    Rules:
    - Two or more newlines  →  paragraph boundary
    - Lines that are only dashes / asterisks / tildes  →  scene-break div
    - Single newlines inside a paragraph  →  joined (no <br/> in prose)
    - The very first paragraph of each call gets class="chapter-start"
      (used for the Drop-Cap CSS rule).
    - After a scene-break the next paragraph also loses its indent.
    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    raw_blocks = re.split(r'\n{2,}', text)

    scene_break_re = re.compile(r'^\s*([-*~=#]{3,}|\*\s+\*\s+\*)\s*$')

    html_parts: list[str] = []
    next_no_indent = True   # first paragraph always no-indent

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        if scene_break_re.match(block):
            html_parts.append('<div class="scene-break">* * *</div>')
            next_no_indent = True   # paragraph after break: no indent
            continue

        # Join internal single newlines
        para_text = ' '.join(line.strip() for line in block.split('\n') if line.strip())
        if not para_text:
            continue

        if next_no_indent:
            html_parts.append(f'<p class="chapter-start">{para_text}</p>')
            next_no_indent = False
        else:
            html_parts.append(f'<p>{para_text}</p>')

    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Professional CSS
# ---------------------------------------------------------------------------

EPUB_CSS = """\
@namespace epub "http://www.idpf.org/2007/ops";

/* ========= Base ========= */
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.75;
    margin: 5% 8%;
    text-align: justify;
    -webkit-hyphens: auto;
    -epub-hyphens: auto;
    hyphens: auto;
    orphans: 2;
    widows: 2;
    color: #1a1a1a;
}

/* ========= Half-Title Page ========= */
.half-title-page {
    text-align: center;
    margin-top: 35%;
}

.half-title-page h1 {
    font-size: 2.2em;
    font-weight: bold;
    letter-spacing: 0.03em;
    margin: 0;
}

/* ========= Full Title Page ========= */
.title-page {
    text-align: center;
    margin-top: 15%;
}

.title-page .book-title {
    font-size: 2.6em;
    font-weight: bold;
    margin-bottom: 0.3em;
    letter-spacing: 0.02em;
}

.title-page .book-subtitle {
    font-size: 1.1em;
    color: #555;
    font-style: italic;
    margin-bottom: 2em;
}

.title-page .ornament {
    font-size: 1.4em;
    color: #999;
    margin: 1.5em 0;
}

.title-page .author {
    font-size: 1.2em;
    font-weight: bold;
    margin-top: 3em;
}

.title-page .publisher {
    font-size: 0.85em;
    color: #777;
    margin-top: 5em;
}

/* ========= Imprint Page ========= */
.imprint-page {
    font-size: 0.8em;
    color: #555;
    margin-top: 10%;
    line-height: 1.65;
}

.imprint-page p {
    margin: 0.5em 0;
    text-indent: 0;
}

.imprint-page hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 1.5em 0;
}

/* ========= Dedication Page ========= */
.dedication-page {
    text-align: center;
    margin-top: 25%;
    font-style: italic;
    font-size: 1.05em;
    color: #444;
    line-height: 2;
}

.dedication-page p {
    text-indent: 0;
}

/* ========= TOC Page ========= */
.toc-page h2 {
    font-size: 1.4em;
    font-weight: bold;
    text-align: center;
    margin-bottom: 2em;
    padding-bottom: 0.5em;
    border-bottom: 1px solid #ccc;
    color: #111;
}

.toc-page ol {
    list-style: none;
    padding: 0;
    margin: 0;
}

.toc-page li {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin: 0.6em 0;
    padding-bottom: 0.35em;
    border-bottom: 1px dotted #ddd;
}

.toc-page li a {
    text-decoration: none;
    color: #222;
    font-size: 0.95em;
}

.toc-page li .roman {
    font-size: 0.75em;
    color: #888;
    letter-spacing: 0.1em;
    font-style: italic;
    margin-left: 1em;
    flex-shrink: 0;
}

/* ========= Chapter Pages ========= */
.chapter-header {
    text-align: center;
    margin-top: 4em;
    margin-bottom: 3em;
}

.chapter-num-label {
    display: block;
    font-size: 0.7em;
    letter-spacing: 0.45em;
    text-transform: uppercase;
    color: #aaa;
    margin-bottom: 0.5em;
}

.chapter-roman {
    display: block;
    font-size: 2em;
    font-weight: bold;
    color: #222;
    margin-bottom: 0.4em;
}

.chapter-title-text {
    display: block;
    font-size: 1.15em;
    font-style: italic;
    color: #444;
    margin-bottom: 1.5em;
}

.chapter-rule {
    border: none;
    border-top: 1px solid #ccc;
    width: 40%;
    margin: 0 auto 2.5em;
}

/* ========= Paragraphs ========= */
p {
    text-indent: 1.5em;
    margin: 0;
}

/* No indent after chapter header / scene break */
.chapter-start {
    text-indent: 0 !important;
}

/* Drop-Cap on first paragraph of each chapter */
.chapter-start::first-letter {
    font-size: 3.2em;
    float: left;
    line-height: 0.82;
    margin: 0.06em 0.08em 0 0;
    font-weight: bold;
    color: #1a1a1a;
    font-family: Georgia, serif;
}

/* ========= Scene Break ========= */
.scene-break {
    text-align: center;
    margin: 2em 0;
    letter-spacing: 0.6em;
    color: #888;
    font-size: 0.9em;
}

/* ========= Afterword ========= */
.afterword-page h2 {
    font-size: 1.4em;
    font-weight: bold;
    text-align: center;
    margin-bottom: 1.5em;
    padding-bottom: 0.5em;
    border-bottom: 1px solid #ddd;
    color: #111;
}

.afterword-page p {
    text-indent: 0;
    margin: 0.8em 0;
}
"""


# ---------------------------------------------------------------------------
# EPUB Generator
# ---------------------------------------------------------------------------

async def generate_book_epub(project: BookProject, chapters: List[BookChapter], output_path: Path):
    """
    Generate a professional, print-ready EPUB for the book project.

    Page order (standard German Belletristik):
      1. Cover image
      2. Schmutzblatt (Half-Title)
      3. Titelblatt (Full Title Page)
      4. Impressum
      5. Widmung (optional – only when epub_dedication is set)
      6. Inhaltsverzeichnis (HTML TOC page)
      7. Kapitel 1 … N
      8. Nachwort (optional – only when epub_afterword is set)
    """
    book = epub.EpubBook()

    # --- Dublin Core Metadata ---
    book.set_identifier(f"urn:uuid:pro-{project.id}")
    book.set_title(project.title)
    book.set_language('de')
    author_name = (project.epub_author or "").strip() or "Stanzwerk Pro"
    book.add_author(author_name)
    book.add_metadata('DC', 'publisher', 'Stanzwerk Pro – Buch-Labor')
    book.add_metadata('DC', 'rights', f'© {datetime.date.today().year} {author_name}')

    # --- CSS item ---
    css_item = epub.EpubItem(
        uid="main_css",
        file_name="style/main.css",
        media_type="text/css",
        content=EPUB_CSS
    )
    book.add_item(css_item)

    # --- Helper: create a well-formed XHTML page ---
    def make_page(uid: str, filename: str, title: str, body_html: str) -> epub.EpubHtml:
        page = epub.EpubHtml(title=title, file_name=filename, lang='de')
        page.content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" lang="de">\n'
            '<head>\n'
            '  <meta charset="UTF-8"/>\n'
            f'  <title>{title}</title>\n'
            '  <link rel="stylesheet" type="text/css" href="../style/main.css"/>\n'
            '</head>\n'
            '<body>\n'
            f'{body_html}\n'
            '</body>\n'
            '</html>'
        )
        page.add_item(css_item)
        return page

    # -------------------------------------------------------
    # Cover image
    # -------------------------------------------------------
    if project.cover_image_url:
        filename = Path(project.cover_image_url).name
        cover_path = settings.AUDIO_OUTPUT_DIR / "books" / filename
        if cover_path.exists():
            try:
                with Image.open(cover_path) as img:
                    img = img.convert("RGB")
                    img.thumbnail((800, 1200))
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=88)
                    book.set_cover("cover.jpg", buf.getvalue())
                    logger.info("Cover image added to EPUB.")
            except Exception as e:
                logger.error(f"Failed to load local cover: {e}")
        elif project.cover_image_url.startswith("http"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(project.cover_image_url)
                    if resp.status_code == 200:
                        with Image.open(io.BytesIO(resp.content)) as img:
                            img = img.convert("RGB")
                            img.thumbnail((800, 1200))
                            buf = io.BytesIO()
                            img.save(buf, format='JPEG', quality=88)
                            book.set_cover("cover.jpg", buf.getvalue())
            except Exception as e:
                logger.error(f"Failed to fetch cover from URL: {e}")

    year = datetime.date.today().year

    # -------------------------------------------------------
    # PAGE 1 – Schmutzblatt (Half-Title)
    # -------------------------------------------------------
    half_title_page = make_page(
        "half_title", "half_title.xhtml", "Titelseite",
        f'<div class="half-title-page"><h1>{project.title}</h1></div>'
    )
    book.add_item(half_title_page)

    # -------------------------------------------------------
    # PAGE 2 – Titelblatt (Full Title)
    # -------------------------------------------------------
    title_page = make_page(
        "title", "title.xhtml", "Titelblatt",
        f'''<div class="title-page">
  <div class="book-title">{project.title}</div>
  <div class="book-subtitle">Eine Novelle</div>
  <div class="ornament">&#10022;</div>
  <div class="author">{author_name}</div>
  <div class="publisher">Stanzwerk Pro &mdash; Buch-Labor &bull; {year}</div>
</div>'''
    )
    book.add_item(title_page)

    # -------------------------------------------------------
    # PAGE 3 – Impressum
    # -------------------------------------------------------
    custom_imprint = (project.epub_imprint or "").strip()
    imprint_extra = f'<hr/><p>{custom_imprint}</p>' if custom_imprint else ''
    imprint_page = make_page(
        "imprint", "imprint.xhtml", "Impressum",
        f'''<div class="imprint-page">
  <p><strong>{project.title}</strong></p>
  <p>Erstauflage {year}</p>
  <hr/>
  <p>&copy; {year} {author_name}</p>
  <p>Alle Rechte vorbehalten. Kein Teil dieses Werkes darf ohne schriftliche
  Genehmigung des Autors reproduziert, verbreitet oder in irgendeiner Form
  &uuml;bertragen werden.</p>
  <hr/>
  <p><em>Dieses Buch wurde mit Unterst&uuml;tzung k&uuml;nstlicher Intelligenz
  (Stanzwerk Pro &ndash; Buch-Labor) verfasst und von {author_name} kuratiert,
  redigiert und ver&ouml;ffentlicht.</em></p>
  {imprint_extra}
  <hr/>
  <p>Genre: {project.genre} &bull; Stil: {project.style}</p>
</div>'''
    )
    book.add_item(imprint_page)

    # -------------------------------------------------------
    # PAGE 4 – Widmung (optional)
    # -------------------------------------------------------
    dedication_page = None
    dedication_text = (project.epub_dedication or "").strip()
    if dedication_text:
        dedication_page = make_page(
            "dedication", "dedication.xhtml", "Widmung",
            f'<div class="dedication-page"><p>{dedication_text}</p></div>'
        )
        book.add_item(dedication_page)

    # -------------------------------------------------------
    # PAGE 5 – HTML Inhaltsverzeichnis
    # -------------------------------------------------------
    toc_items_html = ""
    for c in chapters:
        roman = to_roman(c.chapter_number)
        toc_items_html += (
            f'  <li>\n'
            f'    <a href="chap_{c.chapter_number}.xhtml">{c.title}</a>\n'
            f'    <span class="roman">{roman}</span>\n'
            f'  </li>\n'
        )
    toc_page = make_page(
        "toc_html", "toc_page.xhtml", "Inhaltsverzeichnis",
        f'<div class="toc-page">\n  <h2>Inhaltsverzeichnis</h2>\n  <ol>\n{toc_items_html}  </ol>\n</div>'
    )
    book.add_item(toc_page)

    # -------------------------------------------------------
    # CHAPTERS
    # -------------------------------------------------------
    epub_chapters: list[epub.EpubHtml] = []
    for c in chapters:
        roman = to_roman(c.chapter_number)
        ch_body = text_to_html_paragraphs(c.content or "Inhalt wird noch generiert.")
        chapter_page = make_page(
            f"chap_{c.chapter_number}",
            f"chap_{c.chapter_number}.xhtml",
            c.title,
            f'''<div class="chapter-header">
  <span class="chapter-num-label">Kapitel</span>
  <span class="chapter-roman">{roman}</span>
  <span class="chapter-title-text">{c.title}</span>
  <hr class="chapter-rule"/>
</div>
{ch_body}'''
        )
        book.add_item(chapter_page)
        epub_chapters.append(chapter_page)

    # -------------------------------------------------------
    # LAST PAGE – Nachwort (optional)
    # -------------------------------------------------------
    afterword_page = None
    afterword_text = (project.epub_afterword or "").strip()
    if afterword_text:
        after_paras = text_to_html_paragraphs(afterword_text)
        afterword_page = make_page(
            "afterword", "afterword.xhtml", "Nachwort",
            f'<div class="afterword-page">\n  <h2>Nachwort</h2>\n  {after_paras}\n</div>'
        )
        book.add_item(afterword_page)

    # -------------------------------------------------------
    # TOC (NCX + EPUB3 nav) and Spine
    # -------------------------------------------------------
    toc_entries: list = [
        epub.Link('half_title.xhtml', 'Schmutzblatt', 'half_title'),
        epub.Link('title.xhtml', 'Titelblatt', 'title_page'),
        epub.Link('imprint.xhtml', 'Impressum', 'imprint'),
    ]
    if dedication_page:
        toc_entries.append(epub.Link('dedication.xhtml', 'Widmung', 'dedication'))
    toc_entries.append(epub.Link('toc_page.xhtml', 'Inhaltsverzeichnis', 'toc_html'))
    toc_entries.extend(epub_chapters)
    if afterword_page:
        toc_entries.append(epub.Link('afterword.xhtml', 'Nachwort', 'afterword'))

    book.toc = tuple(toc_entries)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    spine: list = ['nav', half_title_page, title_page, imprint_page]
    if dedication_page:
        spine.append(dedication_page)
    spine.append(toc_page)
    spine.extend(epub_chapters)
    if afterword_page:
        spine.append(afterword_page)
    book.spine = spine

    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(output_path, book, {})
    logger.info(f"Professional EPUB written to {output_path}")


# ---------------------------------------------------------------------------
# KDP Metadata Generator
# ---------------------------------------------------------------------------

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
