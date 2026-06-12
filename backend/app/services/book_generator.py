import logging
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from app.database import engine
from app.models import BookProject, BookChapter
from app.services.text_generator import generate_text

logger = logging.getLogger(__name__)

def clean_json_string(s: str) -> str:
    """Strip markdown code blocks around JSON if present."""
    s = s.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()

def get_author_names_improved(style_string: str) -> str:
    if not style_string:
        return "Neutraler Autor"
    selected_ids = [s.strip() for s in style_string.split(",")]
    try:
        from app.services.story_generator import STANZWERK_BIBLIOTHEK
        id_to_name = {a['id']: a['name'] for category in STANZWERK_BIBLIOTHEK.values() for a in category}
    except Exception as e:
        logger.error(f"Failed to import STANZWERK_BIBLIOTHEK: {e}")
        return style_string
        
    resolved_names = []
    for s in selected_ids:
        if s in id_to_name:
            resolved_names.append(id_to_name[s])
        elif s.lower() in [name.lower() for name in id_to_name.values()]:
            matched = [name for name in id_to_name.values() if name.lower() == s.lower()][0]
            resolved_names.append(matched)
        else:
            resolved_names.append(s)
            
    return ", ".join(resolved_names)

async def suggest_characters(prompt: str, genre: str, style: str, model: str = "gemini-3.1-flash-lite") -> List[Dict[str, Any]]:
    """Generate 3-5 character suggestions based on a book idea."""
    style_resolved = get_author_names_improved(style)
    system_instruction = (
        "Du bist ein erfahrener Romanautor und Charakter-Designer. "
        "Erstelle 3 bis 5 vielschichtige Charaktere für ein neues Buchprojekt. "
        "Antworte ausschließlich im JSON-Format."
    )
    
    prompt_content = f"""
    Buchidee: {prompt}
    Genre: {genre}
    Autorenstil: {style_resolved}
    
    Gib eine Liste von Charakteren zurück. Jeder Charakter muss folgende Felder haben:
    - name (Name des Charakters)
    - role (z. B. Protagonist, Antagonist, Mentor, Begleiter)
    - description (Beschreibung von Aussehen, Hintergrund und Motivation)
    - traits (eine Liste von 3-4 Charaktereigenschaften als Strings)
    
    Format:
    [
      {{
        "name": "...",
        "role": "...",
        "description": "...",
        "traits": ["...", "..."]
      }}
    ]
    """
    
    try:
        response = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in suggest_characters: {e}")
        # Return empty list or basic structure on error
        return []

async def generate_outline(
    prompt: str, 
    genre: str, 
    style: str, 
    characters_bible: str, 
    num_chapters: int = 8, 
    model: str = "gemini-3.1-flash-lite"
) -> Dict[str, Any]:
    """Generate a chapter outline for the book."""
    style_resolved = get_author_names_improved(style)
    system_instruction = (
        "Du bist ein Bestseller-Autor. Entwerfe eine spannende, kapitelweise Gliederung (Outline) "
        "für eine Novelle. Antworte ausschließlich im JSON-Format."
    )
    
    prompt_content = f"""
    Buchidee: {prompt}
    Genre: {genre}
    Autorenstil: {style_resolved}
    Charaktere: {characters_bible}
    Anzahl Kapitel: {num_chapters}
    
    Entwerfe eine Gliederung mit genau {num_chapters} Kapiteln.
    Gib ein JSON-Objekt mit folgenden Feldern zurück:
    - title (Ein passender Buchtitel)
    - chapters (Liste von Kapiteln, jedes mit 'chapter_number', 'title', 'plot_outline' [ausführliche Beschreibung des Inhalts des Kapitels, ca. 100-150 Wörter])
    
    Format:
    {{
      "title": "...",
      "chapters": [
        {{
          "chapter_number": 1,
          "title": "...",
          "plot_outline": "..."
        }}
      ]
    }}
    """
    
    try:
        response = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in generate_outline: {e}")
        # Minimal fallback outline
        fallback = {
            "title": "Unbenanntes Werk",
            "chapters": [
                {
                    "chapter_number": i,
                    "title": f"Kapitel {i}",
                    "plot_outline": "Kapitel-Outline konnte nicht generiert werden."
                } for i in range(1, num_chapters + 1)
            ]
        }
        return fallback

async def generate_chapter_content(
    project: BookProject, 
    chapter: BookChapter, 
    previous_chapters: List[BookChapter], 
    model: str = "deepseek-v4-pro",
    feedback: Optional[str] = None,
    target_words: int = 2000
) -> str:
    """Generate prose for a chapter utilizing compressed running summaries of past chapters."""
    # Build character bible string
    chars_str = project.characters_bible or "Keine Angabe"
    style_resolved = getattr(project, "style_bible", None) or None
    if not style_resolved:
        from app.services.story_generator import generate_modular_prompt
        style_resolved = generate_modular_prompt(project.style)
    
    # Build outline context
    outline_data = json.loads(project.outline) if project.outline else {}
    outline_chapters = outline_data.get("chapters", [])
    outline_str = "\n".join([f"Kapitel {c.get('chapter_number')}: {c.get('title')} - {c.get('plot_outline')}" for c in outline_chapters])
    
    # Build running summaries of past chapters
    past_summaries = []
    for c in previous_chapters:
        past_summaries.append(f"Kapitel {c.chapter_number} ({c.title}): {c.running_summary or 'Inhalt geschrieben.'}")
    past_summaries_str = "\n".join(past_summaries) if past_summaries else "Erstes Kapitel. Keine vorherigen Ereignisse."
    
    # Build exact content of IMMEDIATELY PRECEDING chapter
    prev_chapter_text = ""
    if previous_chapters:
        last_chap = previous_chapters[-1]
        prev_chapter_text = f"VOLLTEXT KAPITEL {last_chap.chapter_number} (Zuletzt geschrieben):\n{last_chap.content or 'Kein Inhalt vorhanden.'}"
    else:
        prev_chapter_text = "Dies ist das erste Kapitel des Buches. Es gibt keinen vorherigen Kapitel-Text."
        
    feedback_clause = ""
    if feedback:
        feedback_clause = f"\n**WICHTIGE ÄNDERUNGSANWEISUNG VOM USER (Für diesen Rewrite):**\n\"{feedback}\"\nBitte überarbeite das Kapitel und beachte diese Anweisung unbedingt!"
 
    system_instruction = (
        f"Du bist ein preisgekrönter Romanautor. Dein Schreibstil folgt diesen Vorgaben:\n{style_resolved}\n\n"
        f"Du schreibst im Genre: {project.genre}.\n"
        "Schreibe ausschließlich die Romanprosa für das angeforderte Kapitel. Schreib flüssig, "
        "atmosphärisch und detailreich. Benutze KEINE Meta-Kommentare, Überschriften oder Einleitungen wie 'Kapitel 1'. "
        "Beginne sofort mit der Geschichte."
    )
    
    prompt = f"""
    Hier sind die Rahmendaten für das Buchprojekt:
    - Buchtitel: {project.title}
    - Ursprungsidee: {project.prompt}
    - Charakter-Übersicht: {chars_str}
    - Gesamte Gliederung des Buches:
    {outline_str}
    
    ---
    
    Bisheriger Handlungsverlauf (Zusammenfassungen):
    {past_summaries_str}
    
    ---
    
    {prev_chapter_text}
    
    ---
    
    Aufgabe:
    Schreibe jetzt das gesamte Kapitel {chapter.chapter_number} mit dem Titel: \"{chapter.title}\"
    Kapitel-Plot (Was passieren soll): {chapter.plot_outline}
    {feedback_clause}
    
    Schreibe ein langes, literarisch hochwertiges Kapitel (Ziel-Wortanzahl: ca. {target_words} Wörter). 
    Achte auf lebendige Dialoge, tiefe Charaktereinblicke und ein angemessenes Pacing passend zum gewählten Stil.
    Gib ausschließlich die Kapitelprosa zurück.
    """
    
    try:
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.8,
            max_tokens=8192,
            system_instruction=system_instruction
        )
        return response.strip()
    except Exception as e:
        logger.error(f"Error generating chapter {chapter.chapter_number}: {e}")
        raise e

async def generate_chapter_summary(chapter_content: str, model: str = "gemini-3.1-flash-lite") -> str:
    """Generate a 50-80 word summary of the chapter content."""
    prompt = f"""
    Fasse das folgende Buchkapitel in genau 50 bis 80 Wörtern zusammen.
    Konzentriere dich auf Handlungsfortschritte, wichtige Entscheidungen und Charakterentwicklungen.
    
    Kapitelinhalt:
    {chapter_content}
    
    Gib ausschließlich die Zusammenfassung zurück. Keine Einleitung, kein 'Zusammenfassung:'.
    """
    try:
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.5,
            max_tokens=300
        )
        return response.strip()
    except Exception as e:
        logger.error(f"Error in generate_chapter_summary: {e}")
        return "Kapitel wurde geschrieben."

async def proofread_chapter(
    chapter_content: str, 
    characters_bible: str, 
    outline: str, 
    chapter_num: int, 
    model: str = "gemini-3.5-flash"
) -> List[Dict[str, Any]]:
    """Proofread the chapter content for consistency, style, and grammar, returning structured findings."""
    system_instruction = (
        "Du bist ein professioneller Lektor und Korrektor. "
        "Analysiere das gegebene Buchkapitel auf logische Konsistenz, Stilfehler, Pacing-Schwächen und Grammatik/Rechtschreibung. "
        "Antworte ausschließlich im JSON-Format."
    )
    
    prompt = f"""
    Hier sind die Referenzdaten für das Buch:
    - Charakter-Bible: {characters_bible}
    - Gliederung: {outline}
    
    Analysiere Kapitel {chapter_num} auf Probleme:
    
    Kapitelinhalt:
    \"\"\"
    {chapter_content}
    \"\"\"
    
    Kategorisiere die Probleme in:
    - 'consistency' (Logikfehler, falsche Augenfarben, Plot-Widersprüche)
    - 'style' (Wortwiederholungen, holpriger Satzbau, Pacing-Fehler)
    - 'grammar' (Tippfehler, Grammatikfehler)
    
    Gib eine Liste von Problemen zurück. Jedes Problem muss folgende Felder haben:
    - category (eine der 3 Kategorien oben)
    - description (Beschreibung des Fehlers auf Deutsch)
    - original_snippet (der genaue fehlerhafte Satz/Absatz aus dem Text)
    - suggested_rewrite (Vorschlag für die Korrektur auf Deutsch, passend zum Kontext)
    
    Format:
    [
      {{
        "category": "consistency",
        "description": "...",
        "original_snippet": "...",
        "suggested_rewrite": "..."
      }}
    ]
    """
    
    try:
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.3,
            response_mime_type="application/json",
            system_instruction=system_instruction
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in proofread_chapter: {e}")
        return []


async def proofread_book_globally(
    chapters: List[BookChapter], 
    characters_bible: str, 
    outline: str, 
    model: str = "gemini-3.5-flash"
) -> List[Dict[str, Any]]:
    """Analyze the complete book manuscript for plot holes, character inconsistencies, and style breaks."""
    system_instruction = (
        "Du bist ein leitender Bestseller-Lektor. "
        "Analysiere das gesamte Manuskript auf inhaltliche Widersprüche, Logikfehler, "
        "Charakter-Konsistenz und Stilbrüche zwischen den Kapiteln. "
        "Antworte ausschließlich im JSON-Format."
    )
    
    # Concatenate all chapters with clear headers
    manuscript_parts = []
    for c in chapters:
        content_text = c.content or "[Kapitel wurde noch nicht geschrieben]"
        manuscript_parts.append(f"=== Kapitel {c.chapter_number}: {c.title} ===\n{content_text}")
    manuscript_text = "\n\n".join(manuscript_parts)
    
    prompt = f"""
    Hier sind die Referenzdaten für das Buch:
    - Charakter-Bible: {characters_bible}
    - Gliederung (Outline): {outline}
    
    Analysiere das folgende gesamte Manuskript auf übergeordnete Probleme (Logikfehler, Charakter-Inkonsistenzen, Stilbrüche):
    
    MANUSKRIPT:
    \"\"\"
    {manuscript_text}
    \"\"\"
    
    Kategorisiere die Probleme in:
    - 'consistency' (z. B. Augenfarbe ändert sich, Figur taucht auf obwohl tot, Gegenstand wechselt den Besitzer ohne Grund, Zeitachsensprung)
    - 'style' (z. B. Kapitel 3 klingt modern, Kapitel 4 plötzlich altertümlich; Tonwechsel; extreme Wortwiederholungen über Kapitel hinweg)
    - 'pacing' (Pacing-Probleme, sprunghafte Entwicklungen im Plotfluss)
    
    Gib eine Liste von Problemen zurück. Jedes Problem muss folgende Felder haben:
    - category (eine der 3 Kategorien oben)
    - description (Beschreibung des Fehlers auf Deutsch)
    - chapters_involved (eine Liste von Integers der Kapitelnummern, die von diesem Problem betroffen sind, z.B. [2, 5])
    - suggested_fix (Konkreter Vorschlag für die Korrektur auf Deutsch)
    
    Format:
    [
      {{
        "category": "consistency",
        "description": "...",
        "chapters_involved": [2, 5],
        "suggested_fix": "..."
      }}
    ]
    """
    
    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.3,
            response_mime_type="application/json",
            system_instruction=system_instruction
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in proofread_book_globally: {e}")
        return []


async def suggest_cover_prompt(
    title: str,
    prompt: str,
    genre: str,
    style: str,
    model: str = "gemini-3.1-flash-lite"
) -> str:
    """Generate an image generation prompt for the book cover based on project details."""
    system_instruction = (
        "Du bist ein erfahrener Buch-Cover-Designer und Prompt-Engineer. "
        "Erstelle einen detaillierten Prompt für ein professionelles Buchcover auf Englisch, "
        "der für Bildgenerierungsmodelle wie Imagen/Midjourney geeignet ist. "
        "Antworte ausschließlich mit dem reinen Prompt-Text ohne Einleitung, Anführungszeichen oder Erklärung."
    )
    
    prompt_content = f"""
    Erstelle einen professionellen Buch-Cover-Bild-Prompt für folgendes Buch:
    - Titel: {title}
    - Genre: {genre}
    - Stil: {style}
    - Buchidee/Konzept: {prompt}
    
    Anweisungen:
    1. Der Prompt muss auf ENGLISCH sein.
    2. Der Prompt MUSS anweisen, den Buchtitel "{title}" in großer, stylischer Typografie prominent im oberen oder mittleren Drittel zu platzieren. Die Schriftart und Farbe müssen zum Genre ({genre}) und zur Stimmung passen.
    3. Der Prompt MUSS anweisen, den Autorennamen "Dirk Proessel" in einer kleineren, passenden Typografie unten auf dem Cover zu platzieren.
    4. Beschreibe das Hintergrundbild detailreich (Lichtstimmung, Komposition, Motive, Stilmittel), sodass Typografie und Grafik wie bei einem echten Verlagsbuch verschmelzen.
    5. Verwende Begriffe wie 'professional book cover design layout', 'bold typography title', 'author name'.
    """
    
    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.7,
            system_instruction=system_instruction
        )
        return response.strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"Error in suggest_cover_prompt: {e}")
        return "A cinematic, beautifully composed book cover art representing the theme of the book."

