"""
Story generation service using Google Gemini Flash.
Two-step process: 1) Generate outline  2) Write detailed chapters
"""

from google import genai
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """Du bist ein erstklassiger, kreativer Geschichtenerzähler für Kinderhörbücher.
Deine Geschichten sind:
- Beruhigend, positiv und fantasievoll.
- Absolut frei von Emojis oder Icons in Titeln und Beschreibungen.
- Kreativ betitelt: Vermeide Standard-Titel wie "Das Geheimnis von..." oder "Der magische...". Sei originell und poetisch.
- Sprachlich hochwertig: Vermeide typische "KI-Floskeln". Erzähle lebendig und bildhaft.
- Strukturiert: Einleitung, spannender Mittelteil, sanftes Ende.
- KEINE Markdown-Formatierung: Nutze NIEMALS Asterisks (*), Unterstriche (_) oder andere Sonderzeichen zur Hervorhebung (z.B. *sehr*), da diese vom Vorlese-System (TTS) wörtlich als "Stern" vorgelesen werden.

WICHTIG: Nutze NIEMALS Emojis (wie 🌙, ✨, 🧸) oder Sonderzeichen zur Textauszeichnung in Titeln oder Beschreibungen. 
Schreibe den Text so, wie er direkt vorgelesen werden soll. Luft zum Atmen lässt du durch Absätze, nicht durch Sonderzeichen.
"""


async def generate_outline(
    prompt: str,
    style: str = "märchenhaft",
    characters: list[str] | None = None,
    target_minutes: int = 20,
) -> dict:
    """Generate a story outline with chapter structure and synopsis."""

    # ~150 words per minute spoken → target word count
    target_words = target_minutes * 150
    num_chapters = max(3, target_minutes // 5)

    char_text = ""
    if characters:
        char_text = f"\nHauptcharaktere: {', '.join(characters)}"

    user_prompt = f"""Erstelle eine Gliederung für eine neue Geschichte.
Thema/Plot: {prompt}
Stil: {style}{char_text}
Ziel-Länge: ~{target_words} Wörter ({target_minutes} Minuten Hörzeit)

Aufgaben:
1. Erfinde einen kreativen, packenden Titel (KEINE Emojis, KEINE Standard-Phrasen).
2. Schreibe eine spannende Zusammenfassung (Synopsis) der Geschichte (4-5 Sätze), die Lust aufs Hören macht. Keine Icons verwenden.
3. Erstelle eine Kapitelstruktur ({num_chapters} Kapitel).

Antworte NUR im folgenden JSON-Format:
{{
    "title": "Kreativer Titel ohne Icons",
    "synopsis": "Einladende Zusammenfassung (4-5 Sätze) ohne Icons.",
    "chapters": [
        {{
            "number": 1,
            "title": "Kapiteltitel",
            "summary": "Was passiert hier?",
            "target_words": 500
        }}
    ]
}}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "response_mime_type": "application/json",
            "temperature": 0.9,
        }
    )

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

    response = client.models.generate_content(
        model=MODEL,
        contents=user_prompt,
        config={
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.85,
            "max_output_tokens": 8192,
        }
    )
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
        "synopsis": outline.get("synopsis", ""),
        "chapters": chapters_text,
    }
