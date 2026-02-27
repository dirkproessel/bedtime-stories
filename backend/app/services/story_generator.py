"""
Story generation service using Google Gemini Flash.
Two-step process: 1) Generate outline  2) Write detailed chapters
"""

import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """Du bist ein kreativer Geschichtenerzähler für Gute-Nacht-Geschichten.
Deine Geschichten sind:
- Beruhigend und positiv
- Altersgerecht und fantasievoll
- Mit klarer Struktur (Einleitung, Hauptteil, Ende)
- In einfacher, bildreicher Sprache geschrieben
- Geeignet zum Vorlesen / Anhören vor dem Schlafen

Schreibe immer auf Deutsch, es sei denn anders angegeben."""


async def generate_outline(
    prompt: str,
    style: str = "märchenhaft",
    characters: list[str] | None = None,
    target_minutes: int = 20,
) -> dict:
    """Generate a story outline with chapter structure."""

    # ~150 words per minute spoken → target word count
    target_words = target_minutes * 150
    num_chapters = max(3, target_minutes // 5)

    char_text = ""
    if characters:
        char_text = f"\nHauptcharaktere: {', '.join(characters)}"

    user_prompt = f"""Erstelle eine Gliederung für eine Gute-Nacht-Geschichte.

Thema/Plot: {prompt}
Stil: {style}{char_text}
Ziel-Länge: ~{target_words} Wörter ({target_minutes} Minuten Hörzeit)
Anzahl Kapitel: {num_chapters}

Antworte NUR im folgenden JSON-Format (keine Markdown-Codeblöcke):
{{
    "title": "Titel der Geschichte",
    "chapters": [
        {{
            "number": 1,
            "title": "Kapiteltitel",
            "summary": "2-3 Sätze was in diesem Kapitel passiert",
            "target_words": 500
        }}
    ]
}}"""

    model = genai.GenerativeModel(
        MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.9,
        ),
    )

    response = await model.generate_content_async(user_prompt)

    import json
    outline = json.loads(response.text)
    return outline


async def generate_chapter(
    story_title: str,
    chapter_info: dict,
    previous_summary: str = "",
    style: str = "märchenhaft",
) -> str:
    """Generate the full text for a single chapter."""

    prev_text = ""
    if previous_summary:
        prev_text = f"\nBisherige Handlung: {previous_summary}"

    user_prompt = f"""Schreibe Kapitel {chapter_info['number']} der Geschichte "{story_title}".

Kapiteltitel: {chapter_info['title']}
Kapitel-Inhalt: {chapter_info['summary']}
Stil: {style}
Ziel-Wortanzahl: ~{chapter_info.get('target_words', 500)} Wörter{prev_text}

Wichtig:
- Schreibe NUR den Fließtext des Kapitels (kein Titel, keine Überschriften)
- Verwende bildreiche, beruhigende Sprache
- Baue natürliche Pausen ein (Absätze)
- Wenn es das letzte Kapitel ist, beende die Geschichte sanft und friedlich"""

    model = genai.GenerativeModel(
        MODEL,
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.types.GenerationConfig(
            temperature=0.85,
            max_output_tokens=4096,
        ),
    )

    response = await model.generate_content_async(user_prompt)
    return response.text


async def generate_full_story(
    prompt: str,
    style: str = "märchenhaft",
    characters: list[str] | None = None,
    target_minutes: int = 20,
    on_progress: callable = None,
) -> dict:
    """
    Generate a complete story: outline first, then chapter by chapter.
    Returns {"title": str, "chapters": [{"title": str, "text": str}]}
    """

    # Step 1: Generate outline
    if on_progress:
        await on_progress("outline", "Erstelle Gliederung...")
    outline = await generate_outline(prompt, style, characters, target_minutes)

    # Step 2: Generate each chapter
    chapters_text = []
    running_summary = ""

    for i, chapter in enumerate(outline["chapters"]):
        if on_progress:
            total = len(outline["chapters"])
            await on_progress(
                "chapter",
                f"Schreibe Kapitel {i + 1}/{total}: {chapter['title']}",
            )

        text = await generate_chapter(
            outline["title"], chapter, running_summary, style
        )
        chapters_text.append({"title": chapter["title"], "text": text})
        running_summary += f" Kapitel {i + 1}: {chapter['summary']}"

    return {
        "title": outline["title"],
        "chapters": chapters_text,
    }
