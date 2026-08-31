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
    """
    is_en = (getattr(project, "language", "de") == "en")
    book = epub.EpubBook()

    # --- Dublin Core Metadata ---
    book.set_identifier(f"urn:uuid:pro-{project.id}")
    book.set_title(project.title)
    book.set_language('en' if is_en else 'de')
    author_name = (project.epub_author or "").strip() or "Stanzwerk Pro"
    book.add_author(author_name)
    book.add_metadata('DC', 'publisher', 'storyja.com')
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
        page = epub.EpubHtml(title=title, file_name=filename, lang='en' if is_en else 'de')
        page.content = body_html
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

    # Check for series info
    series_title = None
    if project.series_id:
        try:
            from sqlmodel import Session
            from app.database import engine
            from app.models import BookSeries
            with Session(engine) as session:
                series = session.get(BookSeries, project.series_id)
                if series:
                    series_title = series.title
        except Exception as e:
            logger.error(f"Failed to fetch series info for EPUB: {e}")

    # -------------------------------------------------------
    # PAGE 1 – Titelblatt (Full Title)
    # -------------------------------------------------------
    vol_lbl = "Volume" if is_en else "Band"
    series_line = f'<div class="book-subtitle">{series_title} &bull; {project.series_subtitle or f"{vol_lbl} {project.series_order}"}</div>' if series_title else ''
    title_lbl = "Title Page" if is_en else "Titelblatt"
    title_page = make_page(
        "title", "title.xhtml", title_lbl,
        f'''<div class="title-page">
  <div class="book-title">{project.title}</div>
  {series_line}
  <div class="ornament">&#10022;</div>
  <div class="author">{author_name}</div>
  <div class="publisher">storyja.com &bull; {year}</div>
</div>'''
    )
    book.add_item(title_page)

    # -------------------------------------------------------
    # PAGE 2 – Impressum / Imprint
    # -------------------------------------------------------
    custom_imprint = (project.epub_imprint or "").strip()
    imprint_extra = f'<hr/><p>{custom_imprint}</p>' if custom_imprint else ''
    
    if is_en:
        series_notice = f'<hr/><p><em>This work is {project.series_subtitle or f"Volume {project.series_order}"} of the series &ldquo;{series_title}&rdquo;.</em></p>' if series_title else ''
        imprint_lbl = "Imprint"
        imprint_body = f'''<div class="imprint-page">
  <p><strong>{project.title}</strong></p>
  <p>First edition {year}</p>
  <hr/>
  <p>&copy; {year} {author_name}</p>
  <p>All rights reserved. No part of this publication may be reproduced, distributed, or transmitted in any form or by any means without the prior written permission of the author.</p>
  {series_notice}
  {imprint_extra}
</div>'''
    else:
        series_notice = f'<hr/><p><em>Dieses Werk ist {project.series_subtitle or f"Band {project.series_order}"} der Buchreihe &bdquo;{series_title}&ldquo;.</em></p>' if series_title else ''
        imprint_lbl = "Impressum"
        imprint_body = f'''<div class="imprint-page">
  <p><strong>{project.title}</strong></p>
  <p>Erstauflage {year}</p>
  <hr/>
  <p>&copy; {year} {author_name}</p>
  <p>Alle Rechte vorbehalten. Kein Teil dieses Werkes darf ohne schriftliche
  Genehmigung des Autors reproduziert, verbreitet oder in irgendeiner Form
  &uuml;bertragen werden.</p>
  {series_notice}
  {imprint_extra}
</div>'''

    imprint_page = make_page("imprint", "imprint.xhtml", imprint_lbl, imprint_body)
    book.add_item(imprint_page)

    # -------------------------------------------------------
    # PAGE 3 – Widmung / Dedication (optional)
    # -------------------------------------------------------
    dedication_page = None
    dedication_text = (project.epub_dedication or "").strip()
    if dedication_text:
        ded_lbl = "Dedication" if is_en else "Widmung"
        dedication_page = make_page(
            "dedication", "dedication.xhtml", ded_lbl,
            f'<div class="dedication-page"><p>{dedication_text}</p></div>'
        )
        book.add_item(dedication_page)

    # -------------------------------------------------------
    # PAGE 3.5 – Was bisher geschah / The Story So Far (optional for sequels)
    # -------------------------------------------------------
    previous_page = None
    if project.previous_summary and project.series_order and project.series_order > 1:
        prev_paras = text_to_html_paragraphs(project.previous_summary)
        prev_lbl = "The Story So Far" if is_en else "Was bisher geschah"
        previous_page = make_page(
            "previous_summary", "previous_summary.xhtml", prev_lbl,
            f'''<div class="previous-summary-page">
  <h2>{prev_lbl}</h2>
  {prev_paras}
</div>'''
        )
        book.add_item(previous_page)

    # -------------------------------------------------------
    # CHAPTERS
    # -------------------------------------------------------
    ch_lbl = "Chapter" if is_en else "Kapitel"
    fallback_content = "Content is being generated." if is_en else "Inhalt wird noch generiert."
    epub_chapters: list[epub.EpubHtml] = []
    for c in chapters:
        roman = to_roman(c.chapter_number)
        ch_body = text_to_html_paragraphs(c.content or fallback_content)
        chapter_page = make_page(
            f"chap_{c.chapter_number}",
            f"chap_{c.chapter_number}.xhtml",
            c.title,
            f'''<div class="chapter-header">
  <span class="chapter-num-label">{ch_lbl}</span>
  <span class="chapter-roman">{roman}</span>
  <span class="chapter-title-text">{c.title}</span>
  <hr class="chapter-rule"/>
</div>
{ch_body}'''
        )
        book.add_item(chapter_page)
        epub_chapters.append(chapter_page)

    # -------------------------------------------------------
    # LAST PAGE – Nachwort / Afterword (optional)
    # -------------------------------------------------------
    afterword_page = None
    afterword_text = (project.epub_afterword or "").strip()
    if afterword_text:
        after_lbl = "Afterword" if is_en else "Nachwort"
        after_paras = text_to_html_paragraphs(afterword_text)
        afterword_page = make_page(
            "afterword", "afterword.xhtml", after_lbl,
            f'<div class="afterword-page">\n  <h2>{after_lbl}</h2>\n  {after_paras}\n</div>'
        )
        book.add_item(afterword_page)

    # -------------------------------------------------------
    # TOC (NCX + EPUB3 nav) and Spine
    # -------------------------------------------------------
    toc_entries: list = [
        epub.Link('title.xhtml', title_lbl, 'title_page'),
        epub.Link('imprint.xhtml', imprint_lbl, 'imprint'),
    ]
    if dedication_page:
        toc_entries.append(epub.Link('dedication.xhtml', "Dedication" if is_en else "Widmung", 'dedication'))
    if previous_page:
        toc_entries.append(epub.Link('previous_summary.xhtml', "The Story So Far" if is_en else "Was bisher geschah", 'previous_summary'))
    toc_entries.extend(epub_chapters)
    if afterword_page:
        toc_entries.append(epub.Link('afterword.xhtml', "Afterword" if is_en else "Nachwort", 'afterword'))

    book.toc = tuple(toc_entries)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    spine: list = [title_page, imprint_page]
    if dedication_page:
        spine.append(dedication_page)
    if previous_page:
        spine.append(previous_page)
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

async def generate_kdp_metadata(
    project: BookProject, 
    chapters: List[BookChapter], 
    model: str = "gemini-3.1-flash-lite",
    marketplace: str = "amazon.de"
) -> Dict[str, Any]:
    """
    Generate official Amazon KDP compatible copy-paste metadata sheet,
    aligned with Amazon's 3-category hierarchy system, backend keywords,
    HTML blurb, and marketplace-specific taxonomies.
    """
    marketplace = (marketplace or "amazon.de").lower().strip()
    is_en_market = marketplace in ["amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au"]
    is_en_project = (getattr(project, "language", "de") == "en")
    is_en = is_en_market or is_en_project

    word_count = sum(len(c.content.split()) for c in chapters if c.content)
    page_est = max(1, round(word_count / 250))
    ch_lbl = "Chapter" if is_en else "Kapitel"

    chapter_titles = ", ".join([f"{ch_lbl} {c.chapter_number}: {c.title}" for c in chapters])

    series_clause = ""
    if project.series_id:
        try:
            from sqlmodel import Session
            from app.database import engine
            from app.models import BookSeries
            with Session(engine) as session:
                series = session.get(BookSeries, project.series_id)
                if series:
                    vol_lbl = "Volume" if is_en else "Band"
                    series_clause = f"- Series: '{series.title}', {project.series_subtitle or f'{vol_lbl} {project.series_order}'}\n"
        except Exception:
            pass

    # Marketplace-specific taxonomy guidance
    if is_en:
        taxonomy_guide = """
Amazon KDP Category Taxonomy (English / Amazon.com & Amazon.co.uk):
Select EXACTLY 3 categories using the hierarchical path 'Main Category > Subcategory > Specific Subcategory'.
Amazon KDP Main Branches:
1. 'Children's Books' (or 'Juvenile Fiction' / 'Juvenile Nonfiction'):
   - Bedtime & Dreams
   - Animals (Farm Animals, Dogs, Cats, Wildlife, Dinosaurs, Dragons & Mythical Creatures)
   - Early Learning & Picture Books (Basic Concepts, Stories in Verse, Interactive)
   - Growing Up & Facts of Life (Friendship, Family & Siblings, Emotions & Feelings, School & Kindergarten)
   - Fantasy & Magic (Fairies, Wizards, Mythical Creatures, Fairy Tales & Folklore)
   - Action & Adventure (Exploration, Pirates, Mysteries & Detectives)
   - Humorous Stories (Funny Animal Tales, Silly Stories)
   - Science, Nature & How It Works (Space & Astronomy, Nature & Wildlife)
   - Holidays & Celebrations (Christmas, Halloween, Easter, Birthdays)
   - Activities, Crafts & Games (Coloring Books, Puzzles & Mazes)
2. 'Fiction':
   - Fantasy (Epic / High Fantasy, Dark Fantasy, Urban Fantasy, Romantic Fantasy / Romantasy, Magical Realism, Time Travel)
   - Science Fiction (Space Opera, Dystopian, Hard Sci-Fi & AI, Cyberpunk, Time Travel, Post-Apocalyptic & Survival, Alien Invasion)
   - Mystery, Thriller & Suspense (Psychological Thrillers, Cozy Mystery, Crime & Detective, Serial Killers, Legal & Political Thrillers, Espionage)
   - Romance (Contemporary Romance, Romantic Comedy, New Adult & College, Fantasy Romance, Historical Romance, Billionaires & Boss, Romantic Suspense)
   - Historical Fiction (Ancient World, Medieval & Renaissance, 19th Century, 20th Century & World Wars, Biographical Fiction)
   - Horror (Psychological Horror, Supernatural & Ghosts, Dark Fantasy & Monsters, Occult)
   - Humor & Satire (Romantic & Contemporary Comedy, Parody & Satire, Dark Humor)
   - Literary Fiction (Family Sagas, Contemporary & Social, Philosophical)
   - Action & Adventure (Treasure Hunting, Wilderness & Survival, Military)
   - Short Stories & Anthologies
3. 'Young Adult Fiction' (YA):
   - Fantasy & Romantasy (Magic Academies, Paranormal, Dark Fantasy)
   - Romance & Coming of Age (First Love, High School & College, Romantic Comedy)
   - Dystopian & Science Fiction
   - Mystery & Thriller
   - Social Issues & Identity
4. 'Nonfiction':
   - Self-Help & Personal Development (Mindfulness & Meditation, Habits & Motivation, Time Management, Stress Management)
   - Health, Fitness & Dieting (Mental Health, Nutrition, Exercise, Holistic Medicine)
   - Parenting & Relationships (Babies & Toddlers, Parenting, Family)
   - Business & Money (Personal Finance, Investing, Entrepreneurship, Leadership)
   - Cookbooks, Food & Wine
   - Science, Tech & Math (AI & Technology, Astronomy, Nature)
   - Biographies & Memoirs
"""
        system_instruction = (
            "You are a leading Amazon Kindle Direct Publishing (KDP) marketing strategist and metadata architect. "
            "Your task is to generate perfectly matching, high-converting metadata for Amazon KDP according to Amazon's official category tree and search algorithms. "
            "Follow the 3-category strategy: Slot 1 = Primary Core Category (Highest Relevance), Slot 2 = High-Traffic Subgenre (High Browse Demand), Slot 3 = Niche Subcategory (Low Competition for #1 Bestseller Badge). "
            "Respond strictly with valid JSON."
        )
        prompt = f"""
Book Details:
- Title: {project.title}
{series_clause}
- Genre: {project.genre}
- Style: {project.style}
- Word Count: {word_count} (~{page_est} book pages)
- Chapters Overview: {chapter_titles}
- Core Concept / Description: {project.prompt}
- Target Marketplace: {marketplace.upper()}

{taxonomy_guide}

Provide the metadata in English as a single valid JSON object with the following fields:
1. 'marketplace': '{marketplace}'
2. 'target_audience': High-level audience definition (e.g., 'Children (Ages 3–6, Bedtime Picture Book)', 'Young Adult (Ages 14–18)', 'Adult Fiction')
3. 'age_range': An object with:
   - 'min_age': integer or null (e.g. 3)
   - 'max_age': integer or null (e.g. 6)
   - 'label': string (e.g. 'Ages 3–6' or 'Adult / All Ages')
4. 'suggested_subtitle': High-converting Amazon subtitle (max 180 characters, crisp and engaging)
5. 'description_kdp': Compelling Amazon HTML blurb using <b>, <i>, <p>, <ul>, <li>, <h3> (max 2000 chars, structured with a catchy hook, bullet points of key themes, and a call to action)
6. 'search_keywords': Array of EXACTLY 7 high-intent KDP search phrases (each under 50 characters, without repeating words from the title)
7. 'kdp_categories': Array of EXACTLY 3 category objects matching the KDP taxonomy:
   - Slot 1: 'slot': 1, 'role': 'Primary Core Category (High Relevance)', 'path': 'Main Category > Subcategory > Branch', 'breadcrumbs': ['Main Category', 'Subcategory', 'Branch'], 'strategy_note': '...'
   - Slot 2: 'slot': 2, 'role': 'High-Traffic Subgenre (High Browse Demand)', 'path': 'Main Category > Subcategory > Branch', 'breadcrumbs': ['Main Category', 'Subcategory', 'Branch'], 'strategy_note': '...'
   - Slot 3: 'slot': 3, 'role': 'Niche Opportunity (Bestseller Badge Potential)', 'path': 'Main Category > Subcategory > Branch', 'breadcrumbs': ['Main Category', 'Subcategory', 'Branch'], 'strategy_note': '...'
8. 'recommended_bisac_categories': Array of 3 string paths (identical to kdp_categories path for backward compatibility)
9. 'pricing_recommendation': Object with:
   - 'price': Recommended price (e.g., '$2.99 USD' or '$3.99 USD' for 70% royalty tier, or '$0.99 USD' for promo launch)
   - 'reason': Strategic pricing rationale
   - 'royalty_rate': '70% KDP Royalty' or '35% KDP Royalty'
10. 'kdp_checklist': Array of 5 concise step-by-step instructions for pasting these fields into KDP.

Format:
{{
  "marketplace": "{marketplace}",
  "target_audience": "...",
  "age_range": {{
    "min_age": 3,
    "max_age": 6,
    "label": "Ages 3–6"
  }},
  "suggested_subtitle": "...",
  "description_kdp": "...",
  "search_keywords": ["...", "...", "...", "...", "...", "...", "..."],
  "kdp_categories": [
    {{
      "slot": 1,
      "role": "Primary Core Category (High Relevance)",
      "path": "Children's Books > Bedtime & Dreams",
      "breadcrumbs": ["Children's Books", "Bedtime & Dreams"],
      "strategy_note": "Direct match for bedtime story queries."
    }},
    {{
      "slot": 2,
      "role": "High-Traffic Subgenre (High Browse Demand)",
      "path": "Children's Books > Animals > Farm Animals",
      "breadcrumbs": ["Children's Books", "Animals", "Farm Animals"],
      "strategy_note": "High-volume browse node on Amazon."
    }},
    {{
      "slot": 3,
      "role": "Niche Opportunity (Bestseller Badge Potential)",
      "path": "Children's Books > Growing Up & Facts of Life > Emotions & Feelings",
      "breadcrumbs": ["Children's Books", "Growing Up & Facts of Life", "Emotions & Feelings"],
      "strategy_note": "Lower competition niche ideal for #1 category ranking."
    }}
  ],
  "recommended_bisac_categories": [
    "Children's Books > Bedtime & Dreams",
    "Children's Books > Animals > Farm Animals",
    "Children's Books > Growing Up & Facts of Life > Emotions & Feelings"
  ],
  "pricing_recommendation": {{
    "price": "$2.99 USD",
    "reason": "Optimal 70% royalty threshold on Amazon KDP.",
    "royalty_rate": "70% KDP Royalty"
  }},
  "kdp_checklist": [
    "Paste Book Title & Subtitle in KDP Step 1",
    "Paste HTML Description into the Description field",
    "Add the 7 search keywords in the 7 backend keyword boxes",
    "Select the 3 exact category paths via the KDP category picker",
    "Set the recommended Age Range (min/max age) to unlock juvenile categories"
  ]
}}
"""
    else:
        taxonomy_guide = """
Offizielle Amazon KDP Kategorie-Taxonomie (Amazon.de / Deutschland, Österreich, Schweiz):
Wähle EXAKT 3 Kategorien nach dem hierarchischen Pfad 'Hauptkategorie > Unterkategorie > Spezifischer Zweig'.
Amazon KDP Hauptkategorien und Zweige im deutschen KDP-Dashboard:
1. 'Kinderbücher' (für Bilderbücher, Vorlesebücher, Gute-Nacht-Geschichten & Erstleser):
   - Gutenachtgeschichten & Träume
   - Tiere (Bauernhoftiere, Hunde & Welpen, Katzen, Wildtiere & Waldtiere, Dinosaurier, Fabelwesen & Drachen, Pferde & Ponys)
   - Bilderbücher & Vorlesebücher (Reime & Lieder, Interaktive Bücher, Erstes Lesen & Wortschatz)
   - Alltag, Familie & Gefühle (Freundschaft & Teilen, Geschwister, Kindergarten & Schulstart, Mut & Selbstvertrauen, Ängste überwinden, Wut & Trauer)
   - Fantasy, Magie & Märchen (Zauberer & Hexen, Fabelwesen, Märchen & Volkssagen)
   - Abenteuer & Entdecker (Piraten, Detektive & Rätsel, Weltall & Reisen)
   - Humor & Lustiges (Lustige Tiergeschichten, Witze & Quatsch)
   - Sachwissen für Kinder (Natur & Umwelt, Tiere, Technik & Fahrzeuge, Weltall & Sterne)
   - Feste & Feiertage (Weihnachten, Ostern, Halloween, Geburtstag)
   - Aktivitäten & Beschäftigung (Malbücher, Rätsel & Labyrinthe)
2. 'Belletristik' (für Romane, Novellen & Erzählungen):
   - Fantasy (Epische Fantasy & High Fantasy, Dark Fantasy, Urban Fantasy, Romantasy / Fantasy Romance, Magischer Realismus, Humorvolle Fantasy, Zeitreisen)
   - Science-Fiction (Space Opera, Dystopien, Hard Sci-Fi & KI, Cyberpunk, Zeitreisen, Postapokalypse & Überleben, Alien-Invasion, Steampunk)
   - Krimis & Thriller (Psychothriller, Detektiv- & Ermittlerromane, Cosy Mystery & Landkrimis, Serienmörder, Justiz- & Politthriller, Spionage, Historische Krimis, Skandinavische Krimis)
   - Liebesromane / Romance (Contemporary / Zeitgenössisch, Romantische Komödie, New Adult & College, Romantasy, Historische Liebesromane / Regency, Milliardäre & Boss, Romantic Suspense)
   - Historische Romane (Antike & Rom, Mittelalter & Ritter, Renaissance, 19. Jahrhundert, 20. Jahrhundert & Weltkriege, Biografische Romane)
   - Horror & Grusel (Psychologischer Horror, Übernatürliches & Geister, Monster & Kreaturen, Dunkle Fantasy)
   - Humor & Satire (Zeitgenössische Komödie, Satire & Parodie, Schwarzer Humor)
   - Literarische Belletristik (Familiensagas, Zeitgenössische Gesellschaftsromane, Philosophische Erzählungen)
   - Action & Abenteuer (Schatzsuche, Überlebenskampf, Militär & Expeditionen)
   - Kurzgeschichten & Anthologien (Erzählbände, Anthologien)
   - Märchen, Sagen & Mythen (Neuinterpretationen / Retellings, Deutsche & Keltische Sagen, Griechische Mythologie)
3. 'Jugendbücher' (Young Adult / YA):
   - Fantasy & Romantasy (Magische Akademien, Dystopische Fantasy, Hexen & Paranormal)
   - Romantik & Coming-of-Age (Erste Liebe, Highschool & College, Romantische Komödie)
   - Dystopien & Science-Fiction (Zukünftige Welten, Sci-Fi Abenteuer)
   - Krimis & Thriller (Jugenddetektive, Psychothriller)
   - Alltag, Familie & Emotionen (Freundschaft & Identität, Mentale Gesundheit)
4. 'Sachbuch & Ratgeber':
   - Ratgeber & Lebensführung (Persönlichkeitsentwicklung, Achtsamkeit & Meditation, Motivation & Erfolg, Zeitmanagement, Minimalismus)
   - Gesundheit, Geist & Körper (Mentale Gesundheit & Stress, Ernährung & Darmgesundheit, Fitness & Yoga, Schlaf & Erholung, Naturheilkunde)
   - Eltern & Familie (Babys 1. Jahr, Kleinkind-Erziehung & Trotzphase, Schule & Lernen, Schwangerschaft & Geburt)
   - Wirtschaft, Finanzen & Karriere (Geldanlage, Aktien & ETFs, Immobilien, Unternehmertum & Startups, Führung & Leadership, Karriere)
   - Psychologie & Beziehungen (Kognition, Verhaltenspsychologie, Partnerschaft & Kommunikation)
   - Wissenschaft & Technik (Künstliche Intelligenz, Astronomie & Physik, Ökologie & Natur)
   - Kochen, Backen & Genuss (Schnelle Küche, Vegetarisch & Vegan, Backen & Brot, Gesunde Ernährung)
   - Biografien & Erinnerungen (Historische Persönlichkeiten, Zeitzeugen, Unternehmer & Künstler)
   - Geschichte & Politik (Antike, Mittelalter, Zeitgeschichte & Weltkriege)
   - Kreativität, Kunst & Hobbys (Schreiben & Selfpublishing, Zeichnen & Malen, Garten & Handwerk)
"""
        system_instruction = (
            "Du bist ein führender Experte für Amazon Kindle Direct Publishing (KDP) Marketing und Bestseller-Strategien auf dem deutschen Buchmarkt. "
            "Erstelle exakt passende, verkaufsoptimierte Metadaten für das Buchprojekt basierend auf dem offiziellen KDP-Kategoriebaum von Amazon.de. "
            "Wende die bewährte 3-Kategorien-Strategie an: "
            "Slot 1 = Hauptkategorie (Höchste Relevanz / Kern-Passung), "
            "Slot 2 = Stark frequentiertes Subgenre (Hohes Stöber-Suchvolumen), "
            "Slot 3 = Gezielte Nischenkategorie (Geringer Wettbewerb für das #1 Bestseller-Abzeichen). "
            "Antworte ausschließlich im validen JSON-Format."
        )
        prompt = f"""
Hier sind die Buchdaten des fertiggestellten Werkes:
- Titel: {project.title}
{series_clause}
- Genre: {project.genre}
- Stil: {project.style}
- Wortanzahl: {word_count} (~{page_est} Buchseiten)
- Kapitelübersicht: {chapter_titles}
- Beschreibung / Ausgangsidee: {project.prompt}
- Ziel-Marktplatz: {marketplace.upper()}

{taxonomy_guide}

Erstelle ein JSON-Objekt auf Deutsch mit exakt folgenden Feldern:
1. 'marketplace': '{marketplace}'
2. 'target_audience': Exakte Zielgruppendefinition (z. B. 'Kinder (3–6 Jahre, Gutenacht-Vorlesebuch)', 'Jugendliche (14–18 Jahre)', 'Erwachsene / All Ages')
3. 'age_range': Ein Objekt mit:
   - 'min_age': Zahl oder null (z. B. 3)
   - 'max_age': Zahl oder null (z. B. 6)
   - 'label': String (z. B. '3–6 Jahre' oder 'Für Erwachsene / Ab 18')
4. 'suggested_subtitle': Ein verkaufsstarker Amazon-Untertitel (max 180 Zeichen, prägnant mit emotionalem Mehrwert)
5. 'description_kdp': Ein hochkonvertierender Klappentext in HTML (mit <b>, <i>, <p>, <ul>, <li>, <h3> Tags, max 2000 Zeichen, bestehend aus Catchy Hook, thematischen Aufzählungspunkten und Handlungsaufforderung)
6. 'search_keywords': Array von EXAKT 7 hochrelevanten KDP-Keywords/Suchbegriffen (jeweils max 50 Zeichen, keine Duplikate aus Titel/Untertitel)
7. 'kdp_categories': Array von EXAKT 3 Kategorien nach KDP-Standard:
   - Slot 1: 'slot': 1, 'role': 'Hauptkategorie (Höchste Relevanz)', 'path': 'Hauptkategorie > Unterkategorie > Spezifischer Zweig', 'breadcrumbs': ['Hauptkategorie', 'Unterkategorie', 'Spezifischer Zweig'], 'strategy_note': '...'
   - Slot 2: 'slot': 2, 'role': 'Subgenre (Hohes Stöber-Suchvolumen)', 'path': 'Hauptkategorie > Unterkategorie > Spezifischer Zweig', 'breadcrumbs': ['Hauptkategorie', 'Unterkategorie', 'Spezifischer Zweig'], 'strategy_note': '...'
   - Slot 3: 'slot': 3, 'role': 'Nische (Geringe Konkurrenz / Bestseller-Chance)', 'path': 'Hauptkategorie > Unterkategorie > Spezifischer Zweig', 'breadcrumbs': ['Hauptkategorie', 'Unterkategorie', 'Spezifischer Zweig'], 'strategy_note': '...'
8. 'recommended_bisac_categories': Array mit den 3 Pfad-Strings (identisch zu kdp_categories.path für Abwärtskompatibilität)
9. 'pricing_recommendation': Ein Objekt mit:
   - 'price': '2,99 EUR' (oder 0,99 EUR / 3,99 EUR / 4,99 EUR)
   - 'reason': Begründung mit KDP 70% Tantiemen-Staffel (2,99 € – 9,99 €)
   - 'royalty_rate': '70% KDP Tantieme' oder '35% KDP Tantieme'
10. 'kdp_checklist': Array mit 5 prägnanten Schritten zum Einfügen in das KDP-Dashboard.

Format:
{{
  "marketplace": "{marketplace}",
  "target_audience": "...",
  "age_range": {{
    "min_age": 3,
    "max_age": 6,
    "label": "3–6 Jahre"
  }},
  "suggested_subtitle": "...",
  "description_kdp": "...",
  "search_keywords": ["...", "...", "...", "...", "...", "...", "..."],
  "kdp_categories": [
    {{
      "slot": 1,
      "role": "Hauptkategorie (Höchste Relevanz)",
      "path": "Kinderbücher > Gutenachtgeschichten & Träume",
      "breadcrumbs": ["Kinderbücher", "Gutenachtgeschichten & Träume"],
      "strategy_note": "Exakte thematische Passung für abendliche Vorlesegeschichten."
    }},
    {{
      "slot": 2,
      "role": "Subgenre (Hohes Stöber-Suchvolumen)",
      "path": "Kinderbücher > Tiere > Bauernhoftiere",
      "breadcrumbs": ["Kinderbücher", "Tiere", "Bauernhoftiere"],
      "strategy_note": "Sehr gefragter Stöberpfad für Tiergeschichten bei Amazon.de."
    }},
    {{
      "slot": 3,
      "role": "Nische (Geringe Konkurrenz / Bestseller-Chance)",
      "path": "Kinderbücher > Alltag, Familie & Gefühle > Mut & Selbstvertrauen",
      "breadcrumbs": ["Kinderbücher", "Alltag, Familie & Gefühle", "Mut & Selbstvertrauen"],
      "strategy_note": "Geringere Buchtitel-Dichte für schnelle #1 Bestseller Platzierung."
    }}
  ],
  "recommended_bisac_categories": [
    "Kinderbücher > Gutenachtgeschichten & Träume",
    "Kinderbücher > Tiere > Bauernhoftiere",
    "Kinderbücher > Alltag, Familie & Gefühle > Mut & Selbstvertrauen"
  ],
  "pricing_recommendation": {{
    "price": "2,99 EUR",
    "reason": "Optimaler Einstiegspreis im 70%-Tantiemen-Bereich von Amazon KDP.",
    "royalty_rate": "70% KDP Tantieme"
  }},
  "kdp_checklist": [
    "Titel und Untertitel in Schritt 1 bei KDP eingeben",
    "HTML-Klappentext in das Beschreibungsfeld kopieren",
    "Die 7 Suchbegriffe in die 7 Keyword-Felder einfügen",
    "Die 3 Kategorien über den KDP-Kategoriebaum anklicken",
    "Lesealter (Min/Max) einstellen, um Kinderbuch-Kategorien freizuschalten"
  ]
}}
"""

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction
        )
        from app.services.book_generator import clean_json_string
        cleaned = clean_json_string(response)
        data = json.loads(cleaned)
        
        # Ensure backward compatibility if kdp_categories exists
        if "kdp_categories" in data and isinstance(data["kdp_categories"], list):
            data["recommended_bisac_categories"] = [
                c.get("path", "") for c in data["kdp_categories"] if isinstance(c, dict) and "path" in c
            ]
        elif "recommended_bisac_categories" in data and isinstance(data["recommended_bisac_categories"], list):
            data["kdp_categories"] = [
                {
                    "slot": idx + 1,
                    "role": "KDP-Kategorie" if not is_en else "KDP Category",
                    "path": p,
                    "breadcrumbs": [b.strip() for b in p.split(">")],
                    "strategy_note": "Empfohlene Amazon KDP Kategorie" if not is_en else "Recommended Amazon KDP Category"
                }
                for idx, p in enumerate(data["recommended_bisac_categories"])
            ]
            
        data["marketplace"] = marketplace
        return data

    except Exception as e:
        logger.error(f"Error generating KDP metadata: {e}")
        
        # Determine defaults based on genre / prompt
        is_kids = any(k in (project.genre + " " + project.prompt).lower() for k in ["kinder", "child", "gute nacht", "bedtime", "tier", "animal", "märchen", "fairy"])
        
        if is_en:
            default_categories = [
                {
                    "slot": 1,
                    "role": "Primary Core Category (High Relevance)",
                    "path": "Children's Books > Bedtime & Dreams" if is_kids else "Fiction > Fantasy > Epic",
                    "breadcrumbs": ["Children's Books", "Bedtime & Dreams"] if is_kids else ["Fiction", "Fantasy", "Epic"],
                    "strategy_note": "Direct alignment with main genre."
                },
                {
                    "slot": 2,
                    "role": "High-Traffic Subgenre (High Browse Demand)",
                    "path": "Children's Books > Animals > Farm Animals" if is_kids else "Fiction > Science Fiction > Space Opera",
                    "breadcrumbs": ["Children's Books", "Animals", "Farm Animals"] if is_kids else ["Fiction", "Science Fiction", "Space Opera"],
                    "strategy_note": "High search volume on Amazon.com."
                },
                {
                    "slot": 3,
                    "role": "Niche Opportunity (Bestseller Badge Potential)",
                    "path": "Children's Books > Growing Up & Facts of Life > Emotions & Feelings" if is_kids else "Fiction > Fantasy > Urban",
                    "breadcrumbs": ["Children's Books", "Growing Up & Facts of Life", "Emotions & Feelings"] if is_kids else ["Fiction", "Fantasy", "Urban"],
                    "strategy_note": "Low competition niche for bestseller ranking."
                }
            ]
            return {
                "marketplace": marketplace,
                "target_audience": "Children (Ages 3–6)" if is_kids else "Adult Fiction",
                "age_range": {
                    "min_age": 3 if is_kids else None,
                    "max_age": 6 if is_kids else None,
                    "label": "Ages 3–6" if is_kids else "Adult / All Ages"
                },
                "suggested_subtitle": f"A Captivating {project.genre} Adventure",
                "description_kdp": f"<p><b>{project.title}</b></p><p>{project.prompt}</p>",
                "search_keywords": [project.genre, project.style, "Bedtime Story" if is_kids else "Novel", "E-Book", "Fiction", "Bestseller", "Paperback"],
                "kdp_categories": default_categories,
                "recommended_bisac_categories": [c["path"] for c in default_categories],
                "pricing_recommendation": {
                    "price": "$2.99 USD",
                    "reason": "Standard launch price within 70% KDP royalty bracket.",
                    "royalty_rate": "70% KDP Royalty"
                },
                "kdp_checklist": [
                    "Paste Book Title & Subtitle in KDP Step 1",
                    "Paste HTML Description into the Description field",
                    "Add the 7 search keywords in the 7 backend keyword boxes",
                    "Select the 3 exact category paths via the KDP category picker",
                    "Set the recommended Age Range (min/max age) to unlock juvenile categories"
                ]
            }
        else:
            default_categories = [
                {
                    "slot": 1,
                    "role": "Hauptkategorie (Höchste Relevanz)",
                    "path": "Kinderbücher > Gutenachtgeschichten & Träume" if is_kids else f"Belletristik > {project.genre}",
                    "breadcrumbs": ["Kinderbücher", "Gutenachtgeschichten & Träume"] if is_kids else ["Belletristik", project.genre],
                    "strategy_note": "Direkte thematische Übereinstimmung mit dem Kerninhalt."
                },
                {
                    "slot": 2,
                    "role": "Subgenre (Hohes Stöber-Suchvolumen)",
                    "path": "Kinderbücher > Tiere > Bauernhoftiere" if is_kids else "Belletristik > Fantasy > Epische Fantasy",
                    "breadcrumbs": ["Kinderbücher", "Tiere", "Bauernhoftiere"] if is_kids else ["Belletristik", "Fantasy", "Epische Fantasy"],
                    "strategy_note": "Stark frequentierter Stöberpfad auf Amazon.de."
                },
                {
                    "slot": 3,
                    "role": "Nische (Geringe Konkurrenz / Bestseller-Chance)",
                    "path": "Kinderbücher > Alltag, Familie & Gefühle > Mut & Selbstvertrauen" if is_kids else "Belletristik > Kurzgeschichten & Anthologien",
                    "breadcrumbs": ["Kinderbücher", "Alltag, Familie & Gefühle", "Mut & Selbstvertrauen"] if is_kids else ["Belletristik", "Kurzgeschichten & Anthologien"],
                    "strategy_note": "Geringe Konkurrenz für schnellen #1 Bestseller-Status."
                }
            ]
            return {
                "marketplace": marketplace,
                "target_audience": "Kinder (3–6 Jahre, Vorlesebuch)" if is_kids else "Erwachsene / All-Age",
                "age_range": {
                    "min_age": 3 if is_kids else None,
                    "max_age": 6 if is_kids else None,
                    "label": "3–6 Jahre" if is_kids else "Für Erwachsene / Ab 18"
                },
                "suggested_subtitle": f"Eine spannende Geschichte im Genre {project.genre}",
                "description_kdp": f"<p><b>{project.title}</b></p><p>{project.prompt}</p>",
                "search_keywords": [project.genre, project.style, "Gutenachtgeschichte" if is_kids else "Roman", "E-Book", "Novelle", "Bestseller", "Taschenbuch"],
                "kdp_categories": default_categories,
                "recommended_bisac_categories": [c["path"] for c in default_categories],
                "pricing_recommendation": {
                    "price": "2,99 EUR",
                    "reason": "Standard-Einstiegspreis im optimalen 70%-Tantiemen-Bereich.",
                    "royalty_rate": "70% KDP Tantieme"
                },
                "kdp_checklist": [
                    "Titel und Untertitel in Schritt 1 bei KDP eingeben",
                    "HTML-Klappentext in das Beschreibungsfeld kopieren",
                    "Die 7 Suchbegriffe in die 7 Keyword-Felder einfügen",
                    "Die 3 Kategorien über den KDP-Kategoriebaum anklicken",
                    "Lesealter (Min/Max) einstellen, um Kinderbuch-Kategorien freizuschalten"
                ]
            }


# ---------------------------------------------------------------------------
# TXT Generator
# ---------------------------------------------------------------------------

def generate_book_txt(project: BookProject, chapters: List[BookChapter], output_path: Path):
    """
    Generate a clean UTF-8 plain-text export of the book.
    """
    is_en = (getattr(project, "language", "de") == "en")
    year = datetime.date.today().year
    author_name = (project.epub_author or "").strip() or "Stanzwerk Pro"
    lines: list[str] = []

    series_title = None
    if project.series_id:
        try:
            from sqlmodel import Session
            from app.database import engine
            from app.models import BookSeries
            with Session(engine) as session:
                series = session.get(BookSeries, project.series_id)
                if series:
                    series_title = series.title
        except Exception:
            pass

    vol_lbl = "Volume" if is_en else "Band"
    by_lbl = "by" if is_en else "von"

    # Title block
    lines.append(project.title.upper())
    if series_title:
        lines.append(f"{'Series' if is_en else 'Serie'}: {series_title} • {project.series_subtitle or f'{vol_lbl} {project.series_order}'}")
    lines.append("")
    lines.append(f"{by_lbl} {author_name}")
    lines.append(f"© {year} {author_name}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    # Impressum / Imprint
    custom_imprint = (project.epub_imprint or "").strip()
    lines.append("IMPRINT" if is_en else "IMPRESSUM")
    lines.append("")
    lines.append(f"{project.title}")
    if series_title:
        if is_en:
            lines.append(f"This work is {project.series_subtitle or f'Volume {project.series_order}'} of the series '{series_title}'.")
        else:
            lines.append(f"Dieses Werk ist {project.series_subtitle or f'Band {project.series_order}'} der Buchreihe '{series_title}'.")
    lines.append(f"First edition {year}" if is_en else f"Erstauflage {year}")
    lines.append(f"© {year} {author_name}")
    lines.append("All rights reserved." if is_en else "Alle Rechte vorbehalten.")
    if custom_imprint:
        lines.append("")
        lines.append(custom_imprint)
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    # Dedication
    dedication_text = (project.epub_dedication or "").strip()
    if dedication_text:
        lines.append(dedication_text)
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

    # Was bisher geschah / The Story So Far (optional for sequels)
    if project.previous_summary and project.series_order and project.series_order > 1:
        lines.append("THE STORY SO FAR" if is_en else "WAS BISHER GESCHAH")
        lines.append("")
        lines.append(project.previous_summary)
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

    # Table of contents
    lines.append("TABLE OF CONTENTS" if is_en else "INHALTSVERZEICHNIS")
    lines.append("")
    for c in chapters:
        roman = to_roman(c.chapter_number)
        lines.append(f"  {roman}. {c.title}")
    lines.append("")
    lines.append("=" * 60)

    # Chapters
    ch_lbl = "Chapter" if is_en else "Kapitel"
    fallback_content = "Content is being generated." if is_en else "Inhalt wird noch generiert."
    for c in chapters:
        roman = to_roman(c.chapter_number)
        lines.append("")
        lines.append("")
        lines.append(f"{ch_lbl} {roman}")
        lines.append(c.title)
        lines.append("-" * 40)
        lines.append("")
        content = (c.content or fallback_content).strip()
        lines.append(content)

    # Afterword
    afterword_text = (project.epub_afterword or "").strip()
    if afterword_text:
        lines.append("")
        lines.append("")
        lines.append("=" * 60)
        lines.append("AFTERWORD" if is_en else "NACHWORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append(afterword_text)

    # Footer
    lines.append("")
    lines.append("")
    lines.append("=" * 60)
    lines.append(f"{'Generated with' if is_en else 'Generiert mit'} storyja.com • {year}")
    lines.append("=" * 60)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Plain-text book written to {output_path}")


def clean_pdf_text(text: str) -> str:
    """
    Sanitize text to be safe for FPDF Latin-1 encoding (Helvetica).
    Replaces common non-Latin-1 characters with equivalents and encodes/decodes to filter others.
    """
    if not text:
        return ""
    
    # Common Unicode characters mapping to Latin-1/ASCII
    replacements = {
        "\u201c": '"',  # “ (left double quote)
        "\u201d": '"',  # ” (right double quote)
        "\u2018": "'",  # ‘ (left single quote)
        "\u2019": "'",  # ’ (right single quote)
        "\u2014": "--", # — (em dash)
        "\u2013": "-",  # – (en dash)
        "\u2026": "...",# … (ellipsis)
        "\u2022": "-",  # • (bullet)
        "\u2726": "* * *", # ✦ (ornament)
        "\u00a0": " ",  # non-breaking space
        "\u200b": "",   # zero-width space
        "\ufeff": "",   # BOM
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    try:
        return text.encode("latin-1", errors="replace").decode("latin-1")
    except Exception:
        return "".join(c if ord(c) < 256 else "?" for c in text)


# ---------------------------------------------------------------------------
# PDF Generator  (fpdf2)
# ---------------------------------------------------------------------------

def generate_book_pdf(project: BookProject, chapters: List[BookChapter], output_path: Path):
    """
    Generate a professional book-style PDF using fpdf2.
    """
    from fpdf import FPDF

    is_en = (getattr(project, "language", "de") == "en")
    year = datetime.date.today().year
    clean_title = clean_pdf_text(project.title)
    author_name = clean_pdf_text((project.epub_author or "").strip() or "Stanzwerk Pro")

    class BookPDF(FPDF):
        """Custom PDF with header/footer for book pages."""

        def __init__(self):
            super().__init__()
            self._book_title = clean_title
            self._author = author_name
            self._show_header_footer = False

        def header(self):
            if not self._show_header_footer:
                return
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, self._book_title, align="C")
            self.ln(4)

        def footer(self):
            if not self._show_header_footer:
                return
            self.set_y(-15)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, str(self.page_no()), align="C")

    pdf = BookPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(25, 20, 25)

    # ---- Title Page ----
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 14, clean_title, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "* * *", align="C")  # ornament ✦ replacement
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 10, author_name, align="C")
    pdf.ln(40)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 8, f"storyja.com - {year}", align="C")  # bullet replacement

    # ---- Imprint Page ----
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, clean_title, ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"First edition {year}" if is_en else f"Erstauflage {year}", ln=True)
    pdf.ln(4)
    pdf.cell(0, 6, f"\u00a9 {year} {author_name}", ln=True)
    pdf.ln(2)
    if is_en:
        pdf.multi_cell(0, 5,
            "All rights reserved. No part of this publication may be reproduced, "
            "distributed, or transmitted in any form or by any means without the "
            "prior written permission of the author."
        )
    else:
        pdf.multi_cell(0, 5,
            "Alle Rechte vorbehalten. Kein Teil dieses Werkes darf ohne "
            "schriftliche Genehmigung des Autors reproduziert, verbreitet "
            "oder in irgendeiner Form \u00fcbertragen werden."
        )
    custom_imprint = clean_pdf_text((project.epub_imprint or "").strip())
    if custom_imprint:
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, custom_imprint)

    # ---- Dedication Page (optional) ----
    dedication_text = clean_pdf_text((project.epub_dedication or "").strip())
    if dedication_text:
        pdf.add_page()
        pdf.ln(80)
        pdf.set_font("Helvetica", "I", 12)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 8, dedication_text, align="C")

    # ---- Table of Contents ----
    pdf.add_page()
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "Table of Contents" if is_en else "Inhaltsverzeichnis", align="C", ln=True)
    pdf.ln(4)
    # horizontal rule
    pdf.set_draw_color(200, 200, 200)
    x_start = pdf.l_margin + 40
    x_end = pdf.w - pdf.r_margin - 40
    pdf.line(x_start, pdf.get_y(), x_end, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(50, 50, 50)
    for c in chapters:
        roman = to_roman(c.chapter_number)
        pdf.cell(15, 8, roman, align="R")
        pdf.cell(8, 8, "")
        pdf.cell(0, 8, clean_pdf_text(c.title), ln=True)

    # ---- Chapter Pages ----
    pdf._show_header_footer = True
    ch_lbl = "CHAPTER" if is_en else "KAPITEL"
    fallback_content = "Content is being generated." if is_en else "Inhalt wird noch generiert."
    for c in chapters:
        pdf.add_page()
        roman = to_roman(c.chapter_number)

        # Chapter header block
        pdf.ln(20)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(160, 160, 160)
        pdf.cell(0, 6, ch_lbl, align="C", ln=True)

        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 14, roman, align="C", ln=True)

        pdf.set_font("Helvetica", "I", 13)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(0, 8, clean_pdf_text(c.title), align="C")
        pdf.ln(4)

        # horizontal rule
        pdf.set_draw_color(200, 200, 200)
        rule_w = 50
        x_center = pdf.w / 2
        pdf.line(x_center - rule_w / 2, pdf.get_y(), x_center + rule_w / 2, pdf.get_y())
        pdf.ln(12)

        # Chapter body text
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(30, 30, 30)
        content = (c.content or fallback_content).strip()

        # Split content into paragraphs and render
        paragraphs = re.split(r'\n{2,}', content)
        for pi, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            # Check for scene break markers
            if re.match(r'^\s*([-*~=#]{3,}|\*\s+\*\s+\*)\s*$', para):
                pdf.ln(4)
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(0, 8, "* * *", align="C", ln=True)
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(30, 30, 30)
                pdf.ln(4)
                continue
            # Join single newlines within a paragraph
            clean_para = ' '.join(line.strip() for line in para.split('\n') if line.strip())
            if clean_para:
                pdf.multi_cell(0, 6.5, clean_pdf_text(clean_para))
                pdf.ln(3)

    # ---- Afterword (optional) ----
    afterword_text = clean_pdf_text((project.epub_afterword or "").strip())
    if afterword_text:
        pdf.add_page()
        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 12, "Afterword" if is_en else "Nachwort", align="C", ln=True)
        pdf.ln(4)
        pdf.set_draw_color(200, 200, 200)
        x_start = pdf.l_margin + 40
        x_end = pdf.w - pdf.r_margin - 40
        pdf.line(x_start, pdf.get_y(), x_end, pdf.get_y())
        pdf.ln(8)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(50, 50, 50)
        after_paragraphs = re.split(r'\n{2,}', afterword_text)
        for para in after_paragraphs:
            para = para.strip()
            if para:
                clean_para = ' '.join(line.strip() for line in para.split('\n') if line.strip())
                pdf.multi_cell(0, 6.5, clean_pdf_text(clean_para))
                pdf.ln(3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    logger.info(f"Professional PDF written to {output_path}")
