import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from ebooklib import epub
from PIL import Image
import io
import logging
from app.config import settings

logger = logging.getLogger(__name__)

async def generate_epub(story_data: dict, cover_image_path: Path | None, output_path: Path):
    """
    Generate a Kindle-friendly EPUB file with story content and title image.
    """
    book = epub.EpubBook()

    # Metadata
    book.set_identifier(f"story-{os.urandom(4).hex()}")
    book.set_title(story_data["title"])
    book.set_language('de')
    book.add_author("Bedtime Story Labor")

    # Cover Image (Optimized for Kindle)
    if cover_image_path and cover_image_path.exists():
        try:
            with Image.open(cover_image_path) as img:
                # Resize and compress cover for space efficiency (Kindle doesn't need 1024x1024 high def)
                img = img.convert("RGB")
                img.thumbnail((600, 600))
                
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=75)
                
                book.set_cover("cover.jpg", img_byte_arr.getvalue())
        except Exception as e:
            logger.error(f"Failed to process cover image for EPUB: {e}")

    # Intro Page / Title
    c1 = epub.EpubHtml(title='Titel', file_name='intro.xhtml', lang='de')
    c1.content = f'<h1>{story_data["title"]}</h1><p><i>{story_data.get("synopsis", "")}</i></p>'
    book.add_item(c1)

    # Chapters
    chapters = []
    for i, chapter in enumerate(story_data.get("chapters", [])):
        ch_title = chapter.get("title", f"Kapitel {i+1}")
        ch_text = chapter.get("text", "").replace("\n", "<br/>")
        
        epub_ch = epub.EpubHtml(title=ch_title, file_name=f'chap_{i+1}.xhtml', lang='de')
        epub_ch.content = f'<h2>{ch_title}</h2><p>{ch_text}</p>'
        book.add_item(epub_ch)
        chapters.append(epub_ch)

    # Table of Contents
    book.toc = (epub.Section('Inhalt'), (epub.Link('intro.xhtml', 'Titel', 'intro'), tuple(chapters)))

    # Basic spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    book.spine = ['nav', c1] + chapters

    # Save
    epub.write_epub(output_path, book, {})
    logger.info(f"EPUB generated at {output_path}")

async def send_to_kindle(epub_path: Path, kindle_email: str):
    """
    Send the EPUB file to Kindle via SMTP.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise ValueError("SMTP_USER or SMTP_PASSWORD not configured.")

    msg = EmailMessage()
    msg['Subject'] = f"Story Export: {epub_path.stem}"
    msg['From'] = settings.SMTP_USER
    msg['To'] = kindle_email
    msg.set_content("Hier ist deine Geschichte aus dem Bedtime Story Labor.")

    with open(epub_path, 'rb') as f:
        file_data = f.read()
        msg.add_attachment(
            file_data,
            maintype='application',
            subtype='epub+zip',
            filename=epub_path.name
        )

    # Connect to SMTP
    try:
        # Use TLS for Gmail/587
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {kindle_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise e
