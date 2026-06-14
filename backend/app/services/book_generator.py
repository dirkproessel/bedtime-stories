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

from pydantic import BaseModel, Field

# --- Pydantic Schemas for Structured Output ---

class CharacterSchema(BaseModel):
    name: str = Field(description="Name des Charakters")
    role: str = Field(description="Rolle im Buch (z. B. Protagonist, Antagonist, Mentor, Begleiter)")
    description: str = Field(description="Beschreibung von Aussehen, Hintergrund und Motivation")
    traits: List[str] = Field(description="Eine Liste von 3-4 Charaktereigenschaften")

class CharacterSuggestionsSchema(BaseModel):
    suggestions: List[CharacterSchema] = Field(description="Liste der vorgeschlagenen Charaktere")

class ChapterOutlineSchema(BaseModel):
    chapter_number: int = Field(description="Die fortlaufende Nummer des Kapitels (1-basiert)")
    title: str = Field(description="Der Titel des Kapitels")
    plot_outline: str = Field(description="Ausführliche Beschreibung des Inhalts des Kapitels (ca. 100-150 Wörter)")

class BookOutlineSchema(BaseModel):
    title: str = Field(description="Ein passender, kreativer Buchtitel")
    chapters: List[ChapterOutlineSchema] = Field(description="Die Gliederung aller Kapitel")

class ImprovedChapterOutlineSchema(BaseModel):
    title: str = Field(description="Der neue oder beibehaltene Kapitel-Titel")
    plot_outline: str = Field(description="Der überarbeitete Inhalt des Kapitels (ca. 100-150 Wörter)")

class ProofreadChapterFindingSchema(BaseModel):
    category: str = Field(description="Die Kategorie des Fehlers ('consistency', 'style' oder 'grammar')")
    description: str = Field(description="Beschreibung des Fehlers auf Deutsch")
    original_snippet: str = Field(description="Der genaue fehlerhafte Satz/Absatz aus dem Kapiteltext")
    suggested_rewrite: str = Field(description="Konkreter Vorschlag für die Korrektur auf Deutsch, passend zum Kontext")

class ProofreadChapterResponseSchema(BaseModel):
    findings: List[ProofreadChapterFindingSchema] = Field(description="Die Liste aller gefundenen Fehler und Korrekturen")

class ProofreadGlobalFindingSchema(BaseModel):
    category: str = Field(description="Die Kategorie des Fehlers ('consistency', 'style' oder 'pacing')")
    description: str = Field(description="Beschreibung des Fehlers auf Deutsch")
    chapters_involved: List[int] = Field(description="Eine Liste der Kapitelnummern, die von diesem Problem betroffen sind")
    suggested_fix: str = Field(description="Konkreter Vorschlag für die Korrektur auf Deutsch")

class ProofreadGlobalResponseSchema(BaseModel):
    findings: List[ProofreadGlobalFindingSchema] = Field(description="Die Liste aller globalen Fehler und Widersprüche im gesamten Manuskript")

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
            system_instruction=system_instruction,
            response_schema=CharacterSuggestionsSchema
        )
        cleaned = clean_json_string(response)
        data = json.loads(cleaned)
        # Handle dict or list root fallback
        if isinstance(data, dict):
            return data.get("suggestions", [])
        return data
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
    model: str = "gemini-3.1-flash-lite",
    instruction: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a chapter outline for the book."""
    style_resolved = get_author_names_improved(style)
    system_instruction = (
        "Du bist ein Bestseller-Autor. Entwerfe eine spannende, kapitelweise Gliederung (Outline) "
        "für eine Novelle. Antworte ausschließlich im JSON-Format."
    )
    
    instruction_str = f"\nNutzer-Anweisung/Kritik zur Berücksichtigung für diese Gliederung:\n\"{instruction}\"\n" if instruction else ""
    
    prompt_content = f"""
    Buchidee: {prompt}
    Genre: {genre}
    Autorenstil: {style_resolved}
    Charaktere: {characters_bible}
    Anzahl Kapitel: {num_chapters}
    {instruction_str}
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
            system_instruction=system_instruction,
            response_schema=BookOutlineSchema
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
        "Benutze unter keinen Umständen Markdown-Sternchen (*) oder Unterstriche (_), um Gedanken, Durchsagen oder wörtliche Rede hervorzuheben. "
        "Nutze für wörtliche Rede und Durchsagen stattdessen klassische deutsche Anführungszeichen (z. B. „...“ oder »...«). "
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
        return response.strip().replace("*", "")
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
            system_instruction=system_instruction,
            response_schema=ProofreadChapterResponseSchema
        )
        cleaned = clean_json_string(response)
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data.get("findings", [])
        return data
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
            system_instruction=system_instruction,
            response_schema=ProofreadGlobalResponseSchema
        )
        cleaned = clean_json_string(response)
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data.get("findings", [])
        return data
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


async def improve_chapter_outline(
    project_prompt: str,
    genre: str,
    style: str,
    characters_bible: str,
    full_outline: str,
    chapter_number: int,
    current_title: str,
    current_plot_outline: str,
    instruction: str,
    model: str = "gemini-3.1-flash-lite"
) -> Dict[str, Any]:
    """Improve / rewrite a single chapter outline based on feedback/instructions."""
    style_resolved = get_author_names_improved(style)
    system_instruction = (
        "Du bist ein Bestseller-Autor. Du hilfst dabei, ein einzelnes Kapitel einer Buchgliederung (Outline) "
        "zu überarbeiten und zu verbessern. Antworte ausschließlich im JSON-Format."
    )
    
    prompt_content = f"""
    Hier sind die Rahmendaten des Buches:
    - Buchidee/Plot: {project_prompt}
    - Genre: {genre}
    - Autorenstil: {style_resolved}
    - Charaktere: {characters_bible}
    
    Gesamt-Gliederung des Buches:
    {full_outline}
    
    Wir überarbeiten gerade Kapitel {chapter_number}:
    - Aktueller Titel: {current_title}
    - Aktueller Inhalt/Gliederung: {current_plot_outline}
    
    Kritik / Anweisung des Nutzers zur Verbesserung dieses Kapitels:
    "{instruction}"
    
    Bitte überarbeite dieses Kapitel basierend auf der Anweisung und dem Gesamtkontext des Buches. 
    Achte darauf, dass es logisch in die restliche Gliederung passt.
    
    Gib ein JSON-Objekt mit exakt diesen Feldern zurück:
    - title (Der neue oder beibehaltene Kapitel-Titel)
    - plot_outline (Der überarbeitete Inhalt des Kapitels, ca. 100-150 Wörter)
    
    Format:
    {{
      "title": "...",
      "plot_outline": "..."
    }}
    """
    
    try:
        response = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.75,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=ImprovedChapterOutlineSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in improve_chapter_outline: {e}")
        return {
            "title": current_title,
            "plot_outline": current_plot_outline
        }


async def parse_imported_outline(
    import_text: str,
    model: str = "gemini-3.1-flash-lite"
) -> Dict[str, Any]:
    """Parse unstructured user-provided text into a structured book outline JSON."""
    system_instruction = (
        "Du bist ein präziser Daten-Parser und Literatur-Strukturierer. "
        "Deine Aufgabe ist es, einen vom Benutzer bereitgestellten Entwurf, Kapitel-Plots oder "
        "Ideen-Texte zu analysieren und strukturiert im JSON-Format auszugeben. "
        "Falls der Text keinen klaren Buchtitel enthält, erfinde einen passenden, kreativen Titel basierend auf dem Thema. "
        "Identifiziere alle Kapitel, ihre Nummern, Titel und deren Inhaltsbeschreibungen (Plot-Outlines) aus dem Text. "
        "Falls ein Kapitel im Text keinen klaren Titel hat, benenne es passend. "
        "Gib das Ergebnis ausschließlich im JSON-Format zurück."
    )
    
    prompt = f"""
    Hier ist der zu analysierende und zu strukturierende Text:
    \"\"\"
    {import_text}
    \"\"\"
    
    Strukturiere diesen Text in das vorgegebene Schema. Jedes gefundene Kapitel muss 'chapter_number', 'title' und 'plot_outline' haben.
    Falls Beschreibungen zu kurz oder unvollständig sind, übernehme sie so gut wie möglich aus dem Text.
    
    Gib ein JSON-Objekt mit folgenden Feldern zurück:
    - title (Der gefundene oder passende Buchtitel)
    - chapters (Liste von Kapiteln, jedes mit 'chapter_number', 'title', 'plot_outline')
    """
    
    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.2,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=BookOutlineSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in parse_imported_outline: {e}")
        raise ValueError(f"Fehler beim Strukturieren des Imports: {str(e)}")


async def expand_chapter_outline(
    project_prompt: str,
    genre: str,
    style: str,
    characters_bible: str,
    full_outline: str,
    chapter_number: int,
    current_title: str,
    current_plot_outline: str,
    model: str = "gemini-3.1-flash-lite"
) -> Dict[str, Any]:
    """Expands a single chapter outline into a detailed 3-4 paragraph blueprint."""
    style_resolved = get_author_names_improved(style)
    system_instruction = (
        "Du bist ein Bestseller-Autor. Deine Aufgabe ist es, eine kurze Kapitelgliederung (Outline) "
        "zu einem hochdetaillierten, schlüssigen und konsistenten Kapitel-Entwurf (Blueprint) auszuarbeiten. "
        "Dieser Entwurf soll ca. 3 bis 4 Absätze umfassen, die den exakten Handlungsablauf, Schlüsselszenen, "
        "Interaktionen und Emotionen beschreiben, damit das Kapitel danach perfekt geschrieben werden kann. "
        "Antworte ausschließlich im JSON-Format."
    )
    
    prompt_content = f"""
    Hier sind die Rahmendaten des Buches:
    - Buchidee/Plot: {project_prompt}
    - Genre: {genre}
    - Autorenstil: {style_resolved}
    - Charaktere: {characters_bible}
    
    Gesamt-Gliederung des Buches:
    {full_outline}
    
    Wir arbeiten gerade Kapitel {chapter_number} aus:
    - Aktueller Titel: {current_title}
    - Aktuelle Kurz-Gliederung: {current_plot_outline}
    
    Bitte verfeinere und vergrößere diese Kurz-Gliederung zu einem detaillierten Kapitel-Blueprint.
    Der Blueprint muss:
    - Etwa 3 bis 4 Absätze lang sein.
    - Die genaue Szenenfolge, wichtige Gesprächsthemen, Gefühle der Charaktere und den roten Faden des Kapitels beschreiben.
    - Vollkommen konsistent mit den vorherigen und nachfolgenden Kapiteln sein.
    - Keine Platzhalter enthalten.
    
    Gib ein JSON-Objekt mit exakt diesen Feldern zurück:
    - title (Der Kapitel-Titel)
    - plot_outline (Der detaillierte Blueprint, 3-4 Absätze lang)
    
    Format:
    {{
      "title": "...",
      "plot_outline": "..."
    }}
    """
    
    try:
        response = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.75,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=ImprovedChapterOutlineSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in expand_chapter_outline for chapter {chapter_number}: {e}")
        return {
            "title": current_title,
            "plot_outline": current_plot_outline
        }



