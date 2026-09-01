import logging
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from app.database import engine
from app.models import BookProject, BookChapter, BookSeries
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

class SeriesArchitectureSchema(BaseModel):
    world_lore: str = Field(description="Ausführliches Worldbuilding, Schauplätze, Magie/Technikregeln, Fraktionen und Zeitlinie")
    characters: List[CharacterSchema] = Field(description="4-6 archetypische, vielschichtige Stamm-Charaktere für die gesamte Serie")
    cover_style_prompt: str = Field(description="Visuelles Style-Template für die Buchcover (auf Englisch, spezifiziert Art-Style, Farbpalette, Beleuchtung, Schriftplatzierung)")
    series_arc: str = Field(description="Übergeordneter Handlungsbogen und Meilensteine für die Bände der Serie")
    volume_1_title: str = Field(description="Kreativer Titel für Band 1")
    volume_1_subtitle: str = Field(description="Untertitel für Band 1 (z. B. 'Band 1: Der Schatten erwacht')")
    volume_1_prompt: str = Field(description="Konkrete Handlungsidee / Plot-Prämisse für Band 1")

class SeriesExtractedSchema(BaseModel):
    world_lore: str = Field(description="Aus dem Buch abgeleitetes Worldbuilding, Regeln und Schauplätze")
    characters: List[CharacterSchema] = Field(description="Liste der wiederkehrenden Stamm-Charaktere der Serie")
    cover_style_prompt: str = Field(description="Vom bestehenden Cover/Buch abgeleitetes Cover-Style-Template auf Englisch")
    series_arc: str = Field(description="Möglicher übergeordneter Serienbogen für Folgebände")

class SequelPitchSchema(BaseModel):
    title: str = Field(description="Vorgeschlagener Buchtitel für den neuen Band")
    subtitle: str = Field(description="Untertitel mit Bandnummer (z. B. 'Band 2: Das Erwachen der Schatten')")
    pitch: str = Field(description="Ausführlicher Klappentext / Handlungs-Pitch für diesen Band (ca. 80-120 Wörter)")
    core_conflict: str = Field(description="Der zentrale neue Konflikt / die neue Bedrohung")
    tone: str = Field(description="Richtung des Sequels (z. B. 'Direkte Fortsetzung / Cliffhanger-Auflösung', 'Neuer Fall / Neues Abenteuer', 'Eskalation / Größere Einsätze')")

class SequelPitchesResponseSchema(BaseModel):
    pitches: List[SequelPitchSchema] = Field(description="Genau 3 unterschiedliche, spannende Richtungen für die Fortsetzung")

class CharacterEvolutionSchema(BaseModel):
    evolved_characters: List[CharacterSchema] = Field(description="Bestehende Stamm-Charaktere mit aktualisierter Entwicklung, Beziehungen und Status")
    new_characters: List[CharacterSchema] = Field(description="2-3 neue, speziell für diesen Band relevante Figuren (z. B. neuer Antagonist, Verbündeter)")

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
    category: str = Field(description="Die Kategorie des Fehlers ('consistency', 'style', 'grammar' oder 'pacing')")
    description: str = Field(description="Beschreibung des Fehlers auf Deutsch")
    original_snippet: str = Field(description="Der genaue fehlerhafte Satz/Absatz aus dem Kapiteltext")
    suggested_rewrite: str = Field(description="Konkreter Vorschlag für die Korrektur auf Deutsch, passend zum Kontext")

class ProofreadChapterResponseSchema(BaseModel):
    findings: List[ProofreadChapterFindingSchema] = Field(description="Die Liste aller gefundenen Fehler und Korrekturen")

class ProofreadGlobalFindingSchema(BaseModel):
    category: str = Field(description="Die Kategorie des Fehlers ('consistency', 'style', 'pacing' oder 'grammar')")
    description: str = Field(description="Beschreibung des Fehlers auf Deutsch")
    chapters_involved: List[int] = Field(description="Eine Liste der Kapitelnummern, die von diesem Problem betroffen sind")
    suggested_fix: str = Field(description="Konkreter Vorschlag für die Korrektur auf Deutsch")

class ProofreadGlobalResponseSchema(BaseModel):
    findings: List[ProofreadGlobalFindingSchema] = Field(description="Die Liste aller globalen Fehler und Widersprüche im gesamten Manuskript")

class SceneBeatSchema(BaseModel):
    scene_number: int = Field(description="Fortlaufende Nummer der Szene (1-basiert)")
    pov_character: str = Field(description="Name des Charakters, aus dessen Perspektive erzählt wird (oder 'Erzähler', falls die allwissende Erzählperspektive gewählt wurde)")
    setting: str = Field(description="Ort/Setting der Szene (z.B. 'Dunkle Gasse hinter dem Club')")
    goal: str = Field(description="Was will der POV-Charakter in dieser Szene erreichen?")
    conflict: str = Field(description="Was steht ihm/ihr im Weg? Welche Spannung entsteht?")
    outcome: str = Field(description="Wie endet die Szene? (z.B. 'Sie erfährt sein Geheimnis')")
    emotional_arc: str = Field(description="Emotionale Entwicklung in dieser Szene (z.B. 'Misstrauen → Neugier → Angst')")
    estimated_words: int = Field(description="Geschätzte Wortanzahl für diese Szene (z.B. 500)")

class ExpandedChapterOutlineSchema(BaseModel):
    title: str = Field(description="Der Kapitel-Titel")
    scene_beats: List[SceneBeatSchema] = Field(description="Die Szenen des Kapitels als strukturierte Beats")
    chapter_summary: str = Field(description="Kurze Zusammenfassung des gesamten Kapitels (1-2 Sätze)")

def estimate_tokens(text: str) -> int:
    """Grobe Token-Schätzung für deutschen Text (~1.4 Token pro Wort)."""
    if not text:
        return 0
    return int(len(text.split()) * 1.4)

# Kontextlimits pro Modell
MODEL_CONTEXT_LIMITS = {
    "gemini-3.7-flash": 1048576,       # 1M tokens
    "gemini-3.1-flash-lite": 1048576,
    "gemini-3.7-pro": 2097152,  # 2M tokens
    "deepseek-v4-pro": 65536,           # 64K tokens  
    "deepseek-v4-flash": 65536,
}

def truncate_to_budget(text: str, max_tokens: int) -> str:
    """Kürze Text intelligent auf ein Token-Budget."""
    current = estimate_tokens(text)
    if current <= max_tokens:
        return text
    # Berechne Wort-Limit und schneide ab
    max_words = int(max_tokens / 1.4)
    words = text.split()
    truncated = " ".join(words[:max_words])
    return truncated + "\n\n[... Text gekürzt wegen Kontextlimit ...]"

async def extract_style_samples(chapter_content: str, model: str = "gemini-3.1-flash-lite") -> str:
    """Extract 3-5 particularly well-written passages from a chapter as style reference."""
    prompt = f"""
    Analysiere den folgenden Romantext und extrahiere exakt 3 bis 5 besonders gelungene Absätze 
    oder Passagen (je 1-3 Sätze), die den Schreibstil des Autors am besten repräsentieren.
    
    Achte auf:
    - Charakteristische Satzstrukturen
    - Besonders atmosphärische Beschreibungen  
    - Gelungene Dialoge
    - Wiederkehrende stilistische Muster
    
    Text:
    \"\"\"
    {chapter_content[:4000]}
    \"\"\"
    
    Gib die Passagen als nummerierte Liste zurück, OHNE Kommentar oder Einleitung.
    Format: 
    1. "Passage..."
    2. "Passage..."
    """
    try:
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.2,
            max_tokens=1000
        )
        return response.strip()
    except Exception as e:
        logger.error(f"Error extracting style samples: {e}")
        return ""

def format_scene_beats_as_text(beats: list, language: str = "de") -> str:
    """Konvertiert Scene Beats in lesbaren Text für das plot_outline-Feld (zweisprachig)."""
    lines = []
    is_en = (language == "en")
    for beat in beats:
        sn = beat.get("scene_number", "?")
        if is_en:
            lines.append(f"--- Scene {sn} ---")
            lines.append(f"POV: {beat.get('pov_character', '?')}")
            lines.append(f"Setting: {beat.get('setting', '?')}")
            lines.append(f"Goal: {beat.get('goal', '?')}")
            lines.append(f"Conflict: {beat.get('conflict', '?')}")
            lines.append(f"Outcome: {beat.get('outcome', '?')}")
            lines.append(f"Emotional Arc: {beat.get('emotional_arc', '?')}")
            lines.append(f"Words: ~{beat.get('estimated_words', '?')}")
        else:
            lines.append(f"--- Szene {sn} ---")
            lines.append(f"POV: {beat.get('pov_character', '?')}")
            lines.append(f"Ort: {beat.get('setting', '?')}")
            lines.append(f"Ziel: {beat.get('goal', '?')}")
            lines.append(f"Konflikt: {beat.get('conflict', '?')}")
            lines.append(f"Ausgang: {beat.get('outcome', '?')}")
            lines.append(f"Emotion: {beat.get('emotional_arc', '?')}")
            lines.append(f"Wörter: ~{beat.get('estimated_words', '?')}")
        lines.append("")  # Leerzeile
    return "\n".join(lines).strip()

def clean_json_string(s: str) -> str:
    """Strip markdown code blocks around JSON or extract the outermost valid JSON object/array."""
    s = s.strip()
    if "```json" in s:
        start = s.find("```json") + 7
        end = s.rfind("```")
        if end > start:
            s = s[start:end].strip()
    elif "```" in s:
        start = s.find("```") + 3
        end = s.rfind("```")
        if end > start:
            s = s[start:end].strip()
            
    first_brace = s.find("{")
    last_brace = s.rfind("}")
    first_bracket = s.find("[")
    last_bracket = s.rfind("]")

    if first_brace != -1 and last_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        s = s[first_brace:last_brace+1]
    elif first_bracket != -1 and last_bracket != -1:
        s = s[first_bracket:last_bracket+1]

    return s.strip()


def clean_chapter_prose(text: str, chapter_title: str, chapter_number: int) -> str:
    """
    Cleans generated chapter text by removing leading chapter titles, numbers, or markdown headers.
    """
    text = text.strip()
    
    # Remove markdown headers like '#', '##', '###' at the very beginning
    while text.startswith("#"):
        text = text.lstrip("#").strip()
        
    import re
    
    # Pattern for "Kapitel X", "Kapitel X: ...", "Chapter X", "Chapter X: ..."
    prefix_pattern = re.compile(
        r'^(?:kapitel|chapter)\s*' + str(chapter_number) + r'(?:\s*[:\-\.]?\s*(?:' + re.escape(chapter_title) + r')?)?',
        re.IGNORECASE
    )
    
    match = prefix_pattern.match(text)
    if match:
        text = text[match.end():].strip()
        # Strip leading colon, dash or period if left over
        text = re.sub(r'^[:\-\.\s\n]+', '', text).strip()
        
    # Also check if it starts directly with the chapter title
    if chapter_title and text.lower().startswith(chapter_title.lower()):
        text = text[len(chapter_title):].strip()
        text = re.sub(r'^[:\-\.\s\n]+', '', text).strip()
        
    return text


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


def get_kids_book_prompt(is_kids_book: bool, language: str = "de") -> str:
    """Returns the prompt injection clause for Kinderbuch mode, or empty string."""
    if not is_kids_book:
        return ""
    if language == "en":
        return (
            "\n\n🧒 KIDS BOOK MODE ACTIVE:\n"
            "This book is written for middle-grade children. Adhere strictly to the following rules:\n"
            "1. ACTION & HUMOR OVER INTROSPECTION: Avoid dry, overly philosophical reflections and long monologues. "
            "Drive the story through active choices, lively dialogue, vivid sensory scenes, and humor. "
            "Draw inspiration from authors like Jeff Kinney (Diary of a Wimpy Kid) or Roald Dahl.\n"
            "2. LANGUAGE: Use clear, engaging sentence structures (max 1-2 subordinate clauses per sentence). "
            "Avoid dense academic jargon and abstract concepts — explain them naturally through action.\n"
            "3. CONTENT: No explicit violence, gore, weapons, dark despair, drugs, alcohol, or sexual content. "
            "Conflicts should be age-appropriate and resolvable.\n"
            "4. STYLE: Adapt the chosen authorial style into a kid-friendly tone.\n"
            "5. EMOTIONS: Show emotions directly and tangibly (excitement, friendship, fear, bravery) with a reassuring resolution.\n"
            "6. CHARACTER DESIGN: Protagonists should be relatable young heroes who actively drive the plot.\n"
        )
    return (
        "\n\n🧒 KINDERBUCH-MODUS AKTIV:\n"
        "Dieses Buch richtet sich an Kinder. Beachte unbedingt folgende Regeln:\n"
        "1. NICHT VERKOPFT: Vermeide trockene, philosophische oder rein intellektuelle Reflexionen und lange gedankliche Monologe. "
        "Erzähle die Geschichte durch aktives Handeln, Dialoge, bildhafte Szenen und Humor. "
        "Lass dich von Autoren wie Jeff Kinney (Gregs Tagebuch - einfach, witzige Missgeschicke) oder Alice Pantermüller (Lotta-Leben - frech, chaotisch, rotzig) inspirieren.\n"
        "2. SPRACHE: Verwende klare, einfache Satzstrukturen (max. 1-2 Nebensätze pro Satz). "
        "Vermeide Fachvokabular, Fremdwörter und abstrakte Konzepte — erkläre sie ggf. beiläufig.\n"
        "3. INHALT: Keine explizite Gewalt, keine Waffen, kein Blut, keine psychologischen Abgründe, "
        "keine Drogen, kein Alkohol, keine sexuellen Inhalte, keine düstere Hoffnungslosigkeit. "
        "Konflikte sollen altersgerecht und lösbar sein.\n"
        "4. STIL: Behalte die stilistischen Eigenheiten der gewählten Autoren bei (z.B. Stakkato-Sätze, "
        "Markennamen-Referenzen, Dialog-Schleifen), aber übersetze sie in einen kindgerechten Kontext. "
        "Ein 'Stuckrad-Barre für Kids' referenziert Sneakers und Schoko-Müsli statt Kokain und Gucci.\n"
        "5. EMOTIONEN: Zeige Gefühle direkt und greifbar. Kinder verstehen Wut, Freude, Trauer, Angst — "
        "aber vermeide existenzielle Krisen oder moralische Grauzonen ohne Auflösung.\n"
        "6. CHARAKTER-DESIGN: Protagonisten sollten Identifikationsfiguren für Kinder sein. "
        "Erwachsene Figuren können Mentoren/Begleiter sein, aber die Kinder/Jugendlichen treiben die Handlung.\n"
    )

async def suggest_characters(
    prompt: str, 
    genre: str, 
    style: str, 
    model: str = "gemini-3.1-flash-lite", 
    is_kids_book: bool = False,
    language: str = "de"
) -> List[Dict[str, Any]]:
    """Generate 3-5 character suggestions based on a book idea."""
    style_resolved = get_author_names_improved(style)
    from app.services.genre_profiles import get_genre_profile
    profile = get_genre_profile(genre)
    genre_context = ""
    is_en = (language == "en")
    
    if profile.id != "default":
        if is_en:
            genre_context = f"\nGenre requirements: {profile.description}\n"
            if profile.emotional_arc_template:
                genre_context += f"Emotional Arc: {profile.emotional_arc_template}\n"
        else:
            genre_context = f"\nGenre-spezifische Anforderungen: {profile.description}\n"
            if profile.emotional_arc_template:
                genre_context += f"Emotionaler Bogen: {profile.emotional_arc_template}\n"

    if is_en:
        system_instruction = (
            "You are an experienced novelist and character designer. "
            f"{genre_context}"
            "Create 3 to 5 multi-dimensional characters for a new book project in English. "
            "Respond strictly in JSON format."
            f"{get_kids_book_prompt(is_kids_book, language='en')}"
        )
        prompt_content = f"""
        Book concept: {prompt}
        Genre: {genre}
        Author style: {style_resolved}
        
        Return a list of characters in English. Each character must have:
        - name (Character's full name)
        - role (e.g., Protagonist, Antagonist, Mentor, Sidekick)
        - description (Detailed description of appearance, background, and motivation)
        - traits (List of 3-4 personality traits as strings)
        
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
    else:
        system_instruction = (
            "Du bist ein erfahrener Romanautor und Charakter-Designer. "
            f"{genre_context}"
            "Erstelle 3 bis 5 vielschichtige Charaktere für ein neues Buchprojekt. "
            "Antworte ausschließlich im JSON-Format."
            f"{get_kids_book_prompt(is_kids_book, language='de')}"
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
    instruction: Optional[str] = None,
    genre_config: Optional[dict] = None,
    series_context: Optional[dict] = None,
    language: str = "de"
) -> Dict[str, Any]:
    """Generate a chapter outline for the book, optionally within a series context."""
    style_resolved = get_author_names_improved(style)
    is_en = (language == "en")
    
    # Parse genre config and build genre-specific prompt section
    from app.services.genre_profiles import build_genre_prompt_section
    g_config = genre_config or {}
    genre_section = build_genre_prompt_section(
        genre,
        selected_tropes=g_config.get("tropes", []),
        pov=g_config.get("pov"),
        spice_level=g_config.get("spice_level")
    )
    
    kids_prompt = get_kids_book_prompt(g_config.get('is_kids_book', False), language=language)
    
    if is_en:
        system_instruction = (
            "You are a bestselling novelist. Design a compelling, chapter-by-chapter outline "
            "for a novella in English. Respond strictly in JSON format."
            f"{kids_prompt}"
        )
        instruction_str = f"\nUser instruction / revision request:\n\"{instruction}\"\n" if instruction else ""
        
        series_section = ""
        if series_context:
            s_title = series_context.get("series_title") or "Book Series"
            s_order = series_context.get("series_order") or 1
            s_lore = series_context.get("world_lore") or ""
            s_arc = series_context.get("series_arc") or ""
            s_prev = series_context.get("previous_summary") or ""
            
            series_section = f"""
        --- SERIES CONTEXT ---
        This book is Volume {s_order} of the series "{s_title}".
        {f'Worldbuilding & Lore: {s_lore}' if s_lore else ''}
        {f'Series Story Arc: {s_arc}' if s_arc else ''}
        {f'The Story So Far (Preceding Volumes): {s_prev}' if s_prev else ''}
        CRITICAL FOR SEQUEL: Maintain strict continuity with previous volumes. Build on established relationships and events!
        -----------------------
        """
        
        prompt_content = f"""
        Book concept: {prompt}
        
        {genre_section}
        {series_section}
        
        Author style: {style_resolved}
        Characters: {characters_bible}
        Number of chapters: {num_chapters}
        {instruction_str}
        Design an outline with exactly {num_chapters} chapters in English.
        Return a JSON object with:
        - title (A fitting, catchy English book title)
        - chapters (List of chapters, each with 'chapter_number', 'title', 'plot_outline' [detailed description of the chapter events, approx. 100-150 words])
        
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
    else:
        system_instruction = (
            "Du bist ein Bestseller-Autor. Entwerfe eine spannende, kapitelweise Gliederung (Outline) "
            "für eine Novelle. Antworte ausschließlich im JSON-Format."
            f"{kids_prompt}"
        )
        instruction_str = f"\nNutzer-Anweisung/Kritik zur Berücksichtigung für diese Gliederung:\n\"{instruction}\"\n" if instruction else ""
        
        series_section = ""
        if series_context:
            s_title = series_context.get("series_title") or "Buch-Serie"
            s_order = series_context.get("series_order") or 1
            s_lore = series_context.get("world_lore") or ""
            s_arc = series_context.get("series_arc") or ""
            s_prev = series_context.get("previous_summary") or ""
            
            series_section = f"""
        --- SERIEN-KONTEXT ---
        Dieses Buch ist Band {s_order} der Buch-Serie "{s_title}".
        {f'Worldbuilding & Lore: {s_lore}' if s_lore else ''}
        {f'Serien-Handlungsbogen: {s_arc}' if s_arc else ''}
        {f'Was bisher geschah (Vorgängerbände): {s_prev}' if s_prev else ''}
        WICHTIG FÜR FORTSETZUNG: Achte auf strenge Kontinuität mit den Vorgängerbänden. Baue auf den etablierten Beziehungen und Ereignissen auf!
        -----------------------
        """
        
        prompt_content = f"""
        Buchidee: {prompt}
        
        {genre_section}
        {series_section}
        
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
            "title": "Untitled Work" if is_en else "Unbenanntes Werk",
            "chapters": [
                {
                    "chapter_number": i,
                    "title": f"Chapter {i}" if is_en else f"Kapitel {i}",
                    "plot_outline": "Chapter outline could not be generated." if is_en else "Kapitel-Outline konnte nicht generiert werden."
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
    target_words: int = 2000,
    language: Optional[str] = None
) -> str:
    """Generate prose for a chapter utilizing a sliding window context and scene beats if available."""
    lang = language or getattr(project, "language", "de") or "de"
    is_en = (lang == "en")
    
    # Build character bible string
    chars_str = project.characters_bible or ("None provided" if is_en else "Keine Angabe")
    style_resolved = getattr(project, "style_bible", None) or None
    if not style_resolved:
        from app.services.story_generator import generate_modular_prompt
        style_resolved = generate_modular_prompt(project.style)
    
    # Load genre profile configuration
    import json
    g_config = json.loads(project.genre_config) if project.genre_config else {}
    from app.services.genre_profiles import build_genre_prompt_section
    genre_section = build_genre_prompt_section(
        project.genre,
        selected_tropes=g_config.get("tropes", []),
        pov=g_config.get("pov"),
        spice_level=g_config.get("spice_level")
    )
    
    # Build outline context
    outline_data = json.loads(project.outline) if project.outline else {}
    outline_chapters = outline_data.get("chapters", [])
    ch_label = "Chapter" if is_en else "Kapitel"
    outline_str = "\n".join([f"{ch_label} {c.get('chapter_number')}: {c.get('title')} - {c.get('plot_outline')}" for c in outline_chapters])
    
    # Sliding Window context building (Default: 2 preceding full-text chapters)
    FULLTEXT_WINDOW_SIZE = 2
    if len(previous_chapters) > FULLTEXT_WINDOW_SIZE:
        summary_chapters = previous_chapters[:-FULLTEXT_WINDOW_SIZE]
        fulltext_chapters = previous_chapters[-FULLTEXT_WINDOW_SIZE:]
    else:
        summary_chapters = []
        fulltext_chapters = previous_chapters

    # Build summaries for older chapters
    past_summaries = []
    for c in summary_chapters:
        past_summaries.append(f"{ch_label} {c.chapter_number} ({c.title}): {c.running_summary or ('Content written.' if is_en else 'Inhalt geschrieben.')}")
    past_summaries_str = "\n".join(past_summaries) if past_summaries else ""

    # Build full-text sections for recent chapters
    fulltext_sections = []
    for c in fulltext_chapters:
        hdr = f"=== FULL TEXT CHAPTER {c.chapter_number}: {c.title} ===" if is_en else f"=== VOLLTEXT KAPITEL {c.chapter_number}: {c.title} ==="
        fulltext_sections.append(
            f"{hdr}\n"
            f"{c.content or ('No content available.' if is_en else 'Kein Inhalt vorhanden.')}"
        )
    first_ch_msg = "This is the first chapter of the book." if is_en else "Dies ist das erste Kapitel des Buches."
    fulltext_str = "\n\n---\n\n".join(fulltext_sections) if fulltext_sections else first_ch_msg
        
    feedback_clause = ""
    if feedback:
        if is_en:
            feedback_clause = f"\n**CRITICAL USER REVISION INSTRUCTION (For this rewrite):**\n\"{feedback}\"\nPlease revise the chapter and strictly adhere to this instruction!"
        else:
            feedback_clause = f"\n**WICHTIGE ÄNDERUNGSANWEISUNG VOM USER (Für diesen Rewrite):**\n\"{feedback}\"\nBitte überarbeite das Kapitel und beachte diese Anweisung unbedingt!"

    # Detect if plot_outline is scene beats structured (support both German and English headers)
    scenes = []
    if chapter.plot_outline and ("--- Szene" in chapter.plot_outline or "--- Scene" in chapter.plot_outline):
        import re
        sections = re.split(r"---\s*(?:Szene|Scene)\s*\d+\s*---", chapter.plot_outline, flags=re.IGNORECASE)
        for i in range(1, len(sections)):
            text = sections[i].strip()
            scene = {"scene_number": i}
            for line in text.split("\n"):
                line = line.strip()
                low = line.lower()
                if low.startswith("pov:"):
                    scene["pov_character"] = line[4:].strip()
                elif low.startswith("ort:") or low.startswith("setting:"):
                    colon_idx = line.find(":")
                    scene["setting"] = line[colon_idx+1:].strip()
                elif low.startswith("ziel:") or low.startswith("goal:"):
                    colon_idx = line.find(":")
                    scene["goal"] = line[colon_idx+1:].strip()
                elif low.startswith("konflikt:") or low.startswith("conflict:"):
                    colon_idx = line.find(":")
                    scene["conflict"] = line[colon_idx+1:].strip()
                elif low.startswith("ausgang:") or low.startswith("outcome:"):
                    colon_idx = line.find(":")
                    scene["outcome"] = line[colon_idx+1:].strip()
                elif low.startswith("emotion:") or low.startswith("emotional arc:"):
                    colon_idx = line.find(":")
                    scene["emotional_arc"] = line[colon_idx+1:].strip()
                elif low.startswith("wörter:") or low.startswith("words:"):
                    colon_idx = line.find(":")
                    scene["estimated_words"] = line[colon_idx+1:].strip()
            scenes.append(scene)

    if scenes:
        logger.info(f"Generating chapter {chapter.chapter_number} scene-by-scene ({len(scenes)} scenes)")
        chapter_prose = ""
        import re
        
        # Extract chapter summary if present in outline
        current_summary = ""
        if chapter.plot_outline:
            sum_match = re.match(r"^(?:Zusammenfassung|Summary):\s*(.*?)\n\n", chapter.plot_outline, re.DOTALL | re.IGNORECASE)
            if sum_match:
                current_summary = sum_match.group(1).strip()
        
        for scene in scenes:
            words = 500  # Fallback target words per scene
            if "estimated_words" in scene:
                match = re.search(r"\d+", scene["estimated_words"])
                if match:
                    words = int(match.group())
            
            # Clamp target words between reasonable boundaries
            words = max(200, min(words, 1500))
            
            if is_en:
                if chapter_prose:
                    prev_scenes_context = f"\nPreviously written scenes for this chapter (continue seamlessly and fluidly):\n{chapter_prose}\n"
                else:
                    prev_scenes_context = "\nThis is the beginning of this chapter. Start directly with the first sentence.\n"
            else:
                if chapter_prose:
                    prev_scenes_context = f"\nBisher geschriebene Szenen für dieses Kapitel (setze nahtlos und flüssig fort):\n{chapter_prose}\n"
                else:
                    prev_scenes_context = "\nDies ist der Anfang dieses Kapitels. Beginne direkt mit dem ersten Satz.\n"
                
            if chapter_prose:
                all_summaries = []
                for c in previous_chapters:
                    all_summaries.append(f"{ch_label} {c.chapter_number} ({c.title}): {c.running_summary or ('Content written.' if is_en else 'Inhalt geschrieben.')}")
                scene_past_summaries_str = "\n".join(all_summaries)
                scene_fulltext_str = "See previously written scenes below for tone and continuity." if is_en else "Siehe bisher geschriebene Szenen unten für Stil und Kontinuität."
                fulltext_count = 0
            else:
                scene_past_summaries_str = past_summaries_str
                scene_fulltext_str = fulltext_str
                fulltext_count = len(fulltext_chapters)

            pov_val = scene.get('pov_character', chapter.pov_character or ('Narrator' if is_en else 'Erzähler'))
            if (g_config and g_config.get("pov") == "omniscient") or pov_val in ["Erzähler", "allwissend", "Allwissend", "Narrator", "Omniscient"]:
                if is_en:
                    pov_line = "- Narrative POV: Omniscient (Write from the perspective of an omniscient, neutral narrator, NOT from first-person/personal POV of any character!)"
                else:
                    pov_line = "- Erzählperspektive: Allwissend (Schreibe aus der Perspektive des allwissenden, neutralen Erzählers, nicht aus der personalen/Ich-Perspektive einer der Hauptpersonen!)"
            else:
                pov_line = f"- POV: {pov_val} (Write consistently from this perspective!)" if is_en else f"- POV: {pov_val} (Schreibe konsequent aus dieser Perspektive!)"

            if is_en:
                scene_prompt = f"""
    Book project background:
    - Book Title: {project.title}
    - Concept Idea: {project.prompt}
    - Characters: {chars_str}
    - Complete Book Outline:
    {outline_str}
    
    ---
    
    Plot progression so far (Summaries of previous chapters):
    {scene_past_summaries_str or "No previous chapters."}
    
    ---
    
    Full text of the last {fulltext_count} chapters (for style reference & continuity):
    {scene_fulltext_str}
    
    ---
    
    Current Chapter: Chapter {chapter.chapter_number} - \"{chapter.title}\"
    {f"Chapter Summary: {current_summary}" if current_summary else ""}
    
    {prev_scenes_context}
    
    ---
    
    TASK:
    Write the novel prose in English for **Scene {scene['scene_number']}** (of {len(scenes)} scenes in this chapter).
    
    Scene Specifications:
    {pov_line}
    - Setting: {scene.get('setting', 'Unspecified')}
    - Goal: {scene.get('goal', 'Unspecified')}
    - Conflict: {scene.get('conflict', 'Unspecified')}
    - Outcome: {scene.get('outcome', 'Unspecified')}
    - Emotional Arc: {scene.get('emotional_arc', 'Unspecified')}
    - Target Word Count for this scene: approx. {words} words.
    
    {feedback_clause}
    
    CRITICAL WRITING RULES:
    1. Write EXCLUSIVELY this one scene (approx. {words} words). Do NOT write the entire chapter!
    2. Once the state described in 'Outcome' is achieved, end generation immediately.
    3. Do NOT mention or foreshadow future scenes prematurely.
    4. Continue seamlessly from previously written scenes. Do NOT repeat events that already happened.
    5. Do NOT include headings, chapter titles, scene numbers (like 'Scene 1'), or markdown divider lines. Begin directly with the narrative prose.
    """
            else:
                scene_prompt = f"""
    Hier sind die Rahmendaten für das Buchprojekt:
    - Buchtitel: {project.title}
    - Ursprungsidee: {project.prompt}
    - Charakter-Übersicht: {chars_str}
    - Gesamte Gliederung des Buches:
    {outline_str}
    
    ---
    
    Bisheriger Handlungsverlauf (Zusammenfassungen früherer Kapitel):
    {scene_past_summaries_str or "Keine früheren Kapitel."}
    
    ---
    
    Volltext der letzten {fulltext_count} Kapitel (als Stilreferenz und für Kontinuität):
    {scene_fulltext_str}
    
    ---
    
    Aktuelles Kapitel: Kapitel {chapter.chapter_number} - \"{chapter.title}\"
    {f"Zusammenfassung des Kapitels: {current_summary}" if current_summary else ""}
    
    {prev_scenes_context}
    
    ---
    
    AUFGABE:
    Schreibe jetzt die Romanprosa für **Szene {scene['scene_number']}** (von insgesamt {len(scenes)} Szenen in diesem Kapitel).
    
    Szenen-Vorgaben:
    {pov_line}
    - Ort: {scene.get('setting', 'Nicht spezifiziert')}
    - Ziel: {scene.get('goal', 'Nicht spezifiziert')}
    - Konflikt: {scene.get('conflict', 'Nicht spezifiziert')}
    - Ausgang: {scene.get('outcome', 'Nicht spezifiziert')}
    - Emotionaler Verlauf: {scene.get('emotional_arc', 'Nicht spezifiziert')}
    - Ziel-Wortanzahl für diese Szene: ca. {words} Wörter.
    
    {feedback_clause}
    
    WICHTIGE SCHREIBREGELN:
    1. Schreibe AUSSCHLIESSLICH diese eine Szene (ca. {words} Wörter). Schreibe NICHT das gesamte Kapitel!
    2. Sobald der in 'Ausgang' beschriebene Zustand der Szene erreicht ist, beende die Generierung sofort.
    3. Beschreibe oder erwähne KEINE Ereignisse oder Dialoge der darauffolgenden Szenen vorab.
    4. Setze den bisherigen Text nahtlos und stilistisch identisch fort. Wiederhole keine Ereignisse, die bereits im bisherigen Text stattgefunden haben. Wenn diese Szene an einem anderen Ort oder zu einer anderen Zeit spielt als die vorherige Szene, verankere den Leser direkt zu Beginn kurz und elegant in der neuen Umgebung (z. B. durch einen kurzen Übergangssatz, der den Orts- oder Zeitwechsel beschreibt).
    5. Füge keine Überschriften, Kapitel- oder Szenennummern (wie 'Szene 1') oder Trennlinien ein. Beginne direkt mit der Romanprosa.
    """
            
            # Token budget check
            model_limit = MODEL_CONTEXT_LIMITS.get(model, 32000)
            scene_max_tokens = int(words * 1.5 + 1000)
            if "reasoner" in model.lower() or "pro" in model.lower():
                scene_max_tokens = 8192
            input_budget = model_limit - scene_max_tokens - 2000
            
            total_input_tokens = estimate_tokens(scene_prompt)
            if total_input_tokens > input_budget:
                logger.warning(f"Context overflow in scene {scene['scene_number']}: {total_input_tokens} > {input_budget}. Truncating outline.")
                temp_outline_str = truncate_to_budget(outline_str, max(500, input_budget // 4))
                if is_en:
                    scene_prompt = f"""
    Book project background:
    - Book Title: {project.title}
    - Concept Idea: {project.prompt}
    - Characters: {chars_str}
    - Complete Book Outline (Truncated):
    {temp_outline_str}
    
    ---
    
    Plot progression so far:
    {scene_past_summaries_str or "No previous chapters."}
    
    ---
    
    Full text of the last {fulltext_count} chapters:
    {scene_fulltext_str}
    
    ---
    
    Current Chapter: Chapter {chapter.chapter_number} - \"{chapter.title}\"
    {f"Chapter Summary: {current_summary}" if current_summary else ""}
    
    {prev_scenes_context}
    
    ---
    
    TASK:
    Write the novel prose in English for **Scene {scene['scene_number']}** (of {len(scenes)} scenes).
    
    Scene Specifications:
    {pov_line}
    - Setting: {scene.get('setting', 'Unspecified')}
    - Goal: {scene.get('goal', 'Unspecified')}
    - Conflict: {scene.get('conflict', 'Unspecified')}
    - Outcome: {scene.get('outcome', 'Unspecified')}
    - Emotional Arc: {scene.get('emotional_arc', 'Unspecified')}
    - Target Word Count: approx. {words} words.
    
    {feedback_clause}
    
    CRITICAL WRITING RULES:
    1. Write EXCLUSIVELY this one scene (approx. {words} words).
    2. End immediately when outcome is achieved.
    3. Do NOT include headings or scene numbers. Begin directly with prose.
    """
                else:
                    scene_prompt = f"""
    Hier sind die Rahmendaten für das Buchprojekt:
    - Buchtitel: {project.title}
    - Ursprungsidee: {project.prompt}
    - Charakter-Übersicht: {chars_str}
    - Gesamte Gliederung des Buches (Gekürzt):
    {temp_outline_str}
    
    ---
    
    Bisheriger Handlungsverlauf (Zusammenfassungen früherer Kapitel):
    {scene_past_summaries_str or "Keine früheren Kapitel."}
    
    ---
    
    Volltext der letzten {fulltext_count} Kapitel (als Stilreferenz und für Kontinuität):
    {scene_fulltext_str}
    
    ---
    
    Aktuelles Kapitel: Kapitel {chapter.chapter_number} - \"{chapter.title}\"
    {f"Zusammenfassung des Kapitels: {current_summary}" if current_summary else ""}
    
    {prev_scenes_context}
    
    ---
    
    AUFGABE:
    Schreibe jetzt die Romanprosa für **Szene {scene['scene_number']}** (von insgesamt {len(scenes)} Szenen in diesem Kapitel).
    
    Szenen-Vorgaben:
    {pov_line}
    - Ort: {scene.get('setting', 'Nicht spezifiziert')}
    - Ziel: {scene.get('goal', 'Nicht spezifiziert')}
    - Konflikt: {scene.get('conflict', 'Nicht spezifiziert')}
    - Ausgang: {scene.get('outcome', 'Nicht spezifiziert')}
    - Emotionaler Verlauf: {scene.get('emotional_arc', 'Nicht spezifiziert')}
    - Ziel-Wortanzahl für diese Szene: ca. {words} Wörter.
    
    {feedback_clause}
    
    WICHTIGE SCHREIBREGELN:
    1. Schreibe AUSSCHLIESSLICH diese eine Szene (ca. {words} Wörter). Schreibe NICHT das gesamte Kapitel!
    2. Sobald der in 'Ausgang' beschriebene Zustand der Szene erreicht ist, beende die Generierung sofort.
    3. Beschreibe oder erwähne KEINE Ereignisse oder Dialoge der darauffolgenden Szenen vorab.
    4. Setze den bisherigen Text nahtlos und stilistisch identisch fort. Wiederhole keine Ereignisse, die bereits im bisherigen Text stattgefunden haben. Wenn diese Szene an einem anderen Ort oder zu einer anderen Zeit spielt als die vorherige Szene, verankere den Leser direkt zu Beginn kurz und elegant in der neuen Umgebung (z. B. durch einen kurzen Übergangssatz, der den Orts- oder Zeitwechsel beschreibt).
    5. Füge keine Überschriften, Kapitel- oder Szenennummern (wie 'Szene 1') oder Trennlinien ein. Beginne direkt mit der Romanprosa.
    """
            
            if is_en:
                system_instruction = (
                    f"You are an award-winning novelist. Your writing style follows these directives:\n{style_resolved}\n\n"
                    f"{genre_section}\n\n"
                    "Write exclusively the novel prose for the requested scene in English. Write fluid, "
                    "atmospheric, and rich prose. Do NOT use headings, scene numbers, metadata, or chapter titles. "
                    "Begin immediately with the story.\n"
                    "Use standard double quotes (“...”) for dialogue. Do NOT use German quotes („...“) or markdown asterisks/underscores around dialogue.\n\n"
                    "ATTENTION: You are writing ONLY this single scene. "
                    "Strictly adhere to the target word budget. Stop immediately once the scene's outcome is achieved."
                    f"{get_kids_book_prompt(g_config.get('is_kids_book', False), language='en')}"
                )
            else:
                system_instruction = (
                    f"Du bist ein preisgekrönter Romanautor. Dein Schreibstil folgt diesen Vorgaben:\n{style_resolved}\n\n"
                    f"{genre_section}\n\n"
                    "Schreibe ausschließlich die Romanprosa für die angeforderte Szene. Schreib flüssig, "
                    "atmosphärisch und detailreich. Benutze KEINE Überschriften, Szenennummern, Meta-Kommentare oder den Kapitelnamen. "
                    "Beginne sofort mit der Geschichte.\n"
                    "Benutze unter keinen Umständen Markdown-Sternchen (*) oder Unterstriche (_), um Gedanken, Durchsagen oder wörtliche Rede hervorzuheben. "
                    "Nutze für wörtliche Rede und Durchsagen stattdessen klassische deutsche Anführungszeichen (z. B. „...“ oder »...«).\n\n"
                    "ACHTUNG: Du schreibst nur eine EINZELNE Szene des Kapitels (nicht das gesamte Kapitel). "
                    "Halte dich streng an das vorgegebene Wortbudget und übertreibe es nicht mit Abschweifungen. "
                    "Beende die Generierung sofort, sobald die Handlung der aktuellen Szene abgeschlossen ist."
                    f"{get_kids_book_prompt(g_config.get('is_kids_book', False), language='de')}"
                )
            if "Stilproben" in (style_resolved or ""):
                system_instruction += (
                    "\n\nACHTUNG: Die in den Vorgaben enthaltenen Stilproben zeigen deinen bisherigen Schreibstil für dieses Buch. "
                    "Halte dich eng an diesen Ton, Rhythmus und diese Wortwahl."
                )
            if "reasoner" in model.lower() or "pro" in model.lower():
                system_instruction += (
                    "\n\nNOTE for Reasoning models: Keep your thinking concise to preserve output token budget for the prose."
                )
            
            try:
                response = await generate_text(
                    prompt=scene_prompt,
                    model=model,
                    temperature=0.8,
                    max_tokens=scene_max_tokens,
                    system_instruction=system_instruction
                )
                scene_prose = response.strip().replace("*", "")
                
                # Strip leading headers or typical scene labels
                scene_prose = clean_chapter_prose(scene_prose, chapter.title, chapter.chapter_number)
                scene_prose = re.sub(r'^(?:---\s*)?(?:szene|scene)\s*\d+\s*(?:[:\-\.]|---)?\s*', '', scene_prose, flags=re.IGNORECASE).strip()
                
                if chapter_prose:
                    chapter_prose += "\n\n***\n\n" + scene_prose
                else:
                    chapter_prose = scene_prose
            except Exception as e:
                logger.error(f"Error generating scene {scene['scene_number']} in chapter {chapter.chapter_number}: {e}")
                raise e
        return chapter_prose
        
    else:
        # Fallback to single-run chapter generation if no structured scenes are found
        writing_instruction = f"""
    {f"Chapter Plot Outline: {chapter.plot_outline}" if is_en else f"Kapitel-Plot (Was passieren soll): {chapter.plot_outline}"}
    """
    
        if is_en:
            system_instruction = (
                f"You are an award-winning novelist. Your writing style follows these directives:\n{style_resolved}\n\n"
                f"{genre_section}\n\n"
                "Write exclusively the novel prose for the requested chapter in English. Write fluid, "
                "atmospheric, and vivid prose. Do NOT include headings, chapter numbers (like 'Chapter 1'), "
                "or metadata. Begin directly with the first sentence of the story.\n"
                "Use standard double quotes (“...”) for dialogue. Do NOT use markdown asterisks or underscores around dialogue."
                f"{get_kids_book_prompt(g_config.get('is_kids_book', False), language='en')}"
            )
        else:
            system_instruction = (
                f"Du bist ein preisgekrönter Romanautor. Dein Schreibstil folgt diesen Vorgaben:\n{style_resolved}\n\n"
                f"{genre_section}\n\n"
                "Schreibe ausschließlich die Romanprosa für das angeforderte Kapitel. Schreib flüssig, "
                "atmosphärisch und detailreich. Benutze KEINE Überschriften, Kapitelnummern (wie 'Kapitel 1'), "
                "Meta-Kommentare oder den Kapiteltitel am Anfang des Textes. Beginne sofort mit dem ersten Satz der Geschichte. "
                "Benutze unter keinen Umständen Markdown-Sternchen (*) oder Unterstriche (_), um Gedanken, Durchsagen oder wörtliche Rede hervorzuheben. "
                "Nutze für wörtliche Rede und Durchsagen stattdessen klassische deutsche Anführungszeichen (z. B. „...“ oder »...«)."
                f"{get_kids_book_prompt(g_config.get('is_kids_book', False), language='de')}"
            )
            
        estimated_tokens = int(target_words * 1.4)
        dynamic_max_tokens = max(8192, min(estimated_tokens + 2048, 16384))
        
        if is_en:
            prompt = f"""
    Book project background:
    - Book Title: {project.title}
    - Concept Idea: {project.prompt}
    - Characters: {chars_str}
    - Complete Book Outline:
    {outline_str}
    
    ---
    
    Plot progression so far:
    {past_summaries_str or "No previous chapters."}
    
    ---
    
    Full text of the last {len(fulltext_chapters)} chapters:
    {fulltext_str}
    
    ---
    
    Task:
    Write the complete Chapter {chapter.chapter_number} titled: \"{chapter.title}\" in English.
    
    {writing_instruction}
    
    {feedback_clause}
    
    Write a rich, literary chapter (Target word count: approx. {target_words} words). 
    Ensure engaging dialogue, character depth, and appropriate pacing.
    Return exclusively the chapter prose.
    """
        else:
            prompt = f"""
    Hier sind die Rahmendaten für das Buchprojekt:
    - Buchtitel: {project.title}
    - Ursprungsidee: {project.prompt}
    - Charakter-Übersicht: {chars_str}
    - Gesamte Gliederung des Buches:
    {outline_str}
    
    ---
    
    Bisheriger Handlungsverlauf (Zusammenfassungen früherer Kapitel):
    {past_summaries_str or "Keine früheren Kapitel."}
    
    ---
    
    Volltext der letzten {len(fulltext_chapters)} Kapitel (als Stilreferenz und für Kontinuität):
    {fulltext_str}
    
    ---
    
    Aufgabe:
    Schreibe jetzt das gesamte Kapitel {chapter.chapter_number} mit dem Titel: \"{chapter.title}\"
    
    {writing_instruction}
    
    {feedback_clause}
    
    Schreibe ein langes, literarisch hochwertiges Kapitel (Ziel-Wortanzahl: ca. {target_words} Wörter). 
    Achte auf lebendige Dialoge, tiefe Charaktereinblicke und ein angemessenes Pacing passend zum gewählten Stil.
    Gib ausschließlich die Kapitelprosa zurück.
    """
    
        model_limit = MODEL_CONTEXT_LIMITS.get(model, 32000)
        output_budget = dynamic_max_tokens
        input_budget = model_limit - output_budget - 2000  # Safety margin
        
        total_input_tokens = estimate_tokens(prompt)
        if total_input_tokens > input_budget:
            logger.warning(f"Context overflow detected: {total_input_tokens} > {input_budget}. Truncating outline.")
            temp_outline_str = truncate_to_budget(outline_str, max(500, input_budget // 4))
            
            if is_en:
                prompt = f"""
    Book project background:
    - Book Title: {project.title}
    - Concept Idea: {project.prompt}
    - Characters: {chars_str}
    - Complete Book Outline (Truncated):
    {temp_outline_str}
    
    ---
    
    Plot progression so far:
    {past_summaries_str or "No previous chapters."}
    
    ---
    
    Full text of the last {len(fulltext_chapters)} chapters:
    {fulltext_str}
    
    ---
    
    Task:
    Write the complete Chapter {chapter.chapter_number} titled: \"{chapter.title}\" in English.
    
    {writing_instruction}
    
    {feedback_clause}
    
    Return exclusively the chapter prose.
    """
            else:
                prompt = f"""
    Hier sind die Rahmendaten für das Buchprojekt:
    - Buchtitel: {project.title}
    - Ursprungsidee: {project.prompt}
    - Charakter-Übersicht: {chars_str}
    - Gesamte Gliederung des Buches (Gekürzt):
    {temp_outline_str}
    
    ---
    
    Bisheriger Handlungsverlauf (Zusammenfassungen früherer Kapitel):
    {past_summaries_str or "Keine früheren Kapitel."}
    
    ---
    
    Volltext der letzten {len(fulltext_chapters)} Kapitel (als Stilreferenz und für Kontinuität):
    {fulltext_str}
    
    ---
    
    Aufgabe:
    Schreibe jetzt das gesamte Kapitel {chapter.chapter_number} mit dem Titel: \"{chapter.title}\"
    
    {writing_instruction}
    
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
                max_tokens=dynamic_max_tokens,
                system_instruction=system_instruction
            )
            prose = response.strip().replace("*", "")
            return clean_chapter_prose(prose, chapter.title, chapter.chapter_number)
        except Exception as e:
            logger.error(f"Error generating chapter {chapter.chapter_number}: {e}")
            raise e

async def generate_chapter_summary(
    chapter_content: str, 
    model: str = "gemini-3.1-flash-lite",
    language: str = "de"
) -> str:
    """Generate a 50-80 word summary of the chapter content."""
    is_en = (language == "en")
    if is_en:
        prompt = f"""
        Summarize the following book chapter in exactly 50 to 80 words in English.
        Focus on plot progression, critical decisions, and character arcs.
        
        Chapter content:
        {chapter_content}
        
        Return ONLY the summary text. No introduction, no 'Summary:'.
        """
    else:
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
        return "Chapter was written." if is_en else "Kapitel wurde geschrieben."

async def proofread_chapter(
    chapter_content: str, 
    characters_bible: str, 
    outline: str, 
    chapter_num: int, 
    model: str = "gemini-3.7-flash",
    language: str = "de"
) -> List[Dict[str, Any]]:
    """Proofread the chapter content for consistency, style, and grammar, returning structured findings."""
    is_en = (language == "en")
    
    if is_en:
        system_instruction = (
            "You are a professional book editor and proofreader. "
            "Analyze the given chapter for logical consistency, style flaws, pacing weaknesses, and grammar/spelling. "
            "Respond strictly in JSON format."
        )
        prompt = f"""
        Reference data for the book:
        - Character Bible: {characters_bible}
        - Outline: {outline}
        
        Analyze Chapter {chapter_num} for issues. Find as many relevant issues as possible (at least 10 to 15 findings if present).
        
        Chapter content:
        \"\"\"
        {chapter_content}
        \"\"\"
        
        Categorize issues into:
        - 'consistency' (Plot holes, eye color changes, timeline contradictions)
        - 'style' (Repetitive phrasing, awkward sentence flow)
        - 'pacing' (Pacing issues, jarring transitions)
        - 'grammar' (Typos, punctuation, grammatical mistakes)
        
        Return a list of findings in English. Each finding must have:
        - category (one of the 4 above)
        - description (Clear description of the error in English)
        - original_snippet (the exact sentence/passage containing the error)
        - suggested_rewrite (proposed correction in English fitting the context)
        
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
    else:
        system_instruction = (
            "Du bist ein professioneller Lektor und Korrektor. "
            "Analysiere das gegebene Buchkapitel auf logische Konsistenz, Stilfehler, Pacing-Schwächen und Grammatik/Rechtschreibung. "
            "Antworte ausschließlich im JSON-Format."
        )
        prompt = f"""
        Hier sind die Referenzdaten für das Buch:
        - Charakter-Bible: {characters_bible}
        - Gliederung: {outline}
        
        Analysiere Kapitel {chapter_num} auf Probleme. Finde so viele Probleme wie möglich (mindestens 10 bis 15 relevante Befunde, falls vorhanden). Sei extrem gründlich und suche auch nach kleineren Stil-, Grammatik-, Zeichensetzungs- und Wortwiederholungsfehlern.
        
        Kapitelinhalt:
        \"\"\"
        {chapter_content}
        \"\"\"
        
        Kategorisiere die Probleme in:
        - 'consistency' (Logikfehler, falsche Augenfarben, Plot-Widersprüche)
        - 'style' (Wortwiederholungen, holpriger Satzbau)
        - 'pacing' (Pacing-Fehler, sprunghafter Plotfluss)
        - 'grammar' (Tippfehler, Grammatikfehler)
        
        Gib eine Liste von Problemen zurück. Jedes Problem muss folgende Felder haben:
        - category (eine der 4 Kategorien oben)
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
    model: str = "gemini-3.7-flash",
    language: str = "de"
) -> List[Dict[str, Any]]:
    """Analyze the complete book manuscript for plot holes, character inconsistencies, and style breaks."""
    is_en = (language == "en")
    ch_lbl = "Chapter" if is_en else "Kapitel"
    
    # Concatenate all chapters with clear headers
    manuscript_parts = []
    for c in chapters:
        content_text = c.content or ("[Chapter not written yet]" if is_en else "[Kapitel wurde noch nicht geschrieben]")
        manuscript_parts.append(f"=== {ch_lbl} {c.chapter_number}: {c.title} ===\n{content_text}")
    manuscript_text = "\n\n".join(manuscript_parts)
    
    if is_en:
        system_instruction = (
            "You are a senior acquisitions and developmental editor. "
            "Analyze the entire manuscript for narrative contradictions, logic errors, "
            "character inconsistencies, and stylistic tonal breaks across chapters. "
            "Respond strictly in JSON format."
        )
        prompt = f"""
        Reference data for the book:
        - Character Bible: {characters_bible}
        - Outline: {outline}
        
        Analyze the manuscript for overarching macro-level issues. Find at least 10 to 15 relevant findings.
        
        MANUSCRIPT:
        \"\"\"
        {manuscript_text}
        \"\"\"
        
        Categorize issues into:
        - 'consistency' (Contradictions, character traits changing, timeline gaps)
        - 'style' (Abrupt tonal shifts between chapters, repetitive prose across chapters)
        - 'pacing' (Pacing flaws, abrupt unearned climaxes)
        - 'grammar' (Systematic grammar/spelling errors across multiple chapters)
        
        Return a list of findings in English:
        - category
        - description (Description of the issue in English)
        - chapters_involved (List of integers of affected chapter numbers, e.g. [2, 5])
        - suggested_fix (Concrete recommendation in English)
        
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
    else:
        system_instruction = (
            "Du bist ein leitender Bestseller-Lektor. "
            "Analysiere das gesamte Manuskript auf inhaltliche Widersprüche, Logikfehler, "
            "Charakter-Konsistenz und Stilbrüche zwischen den Kapiteln. "
            "Antworte ausschließlich im JSON-Format."
        )
        prompt = f"""
        Hier sind die Referenzdaten für das Buch:
        - Charakter-Bible: {characters_bible}
        - Gliederung (Outline): {outline}
        
        Analysiere das folgende gesamte Manuskript auf übergeordnete Probleme (Logikfehler, Charakter-Inkonsistenzen, Stilbrüche, Grammatikmuster). Finde so viele Probleme wie möglich (mindestens 10 bis 15 relevante Befunde, falls vorhanden). Sei extrem gründlich und suche nach Widersprüchen, Stilbrüchen und systematischen Rechtschreib- oder Grammatikfehlern im gesamten Buch.
        
        MANUSKRIPT:
        \"\"\"
        {manuscript_text}
        \"\"\"
        
        Kategorisiere die Probleme in:
        - 'consistency' (z. B. Augenfarbe ändert sich, Figur taucht auf obwohl tot, Gegenstand wechselt den Besitzer ohne Grund, Zeitachsensprung)
        - 'style' (z. B. Kapitel 3 klingt modern, Kapitel 4 plötzlich altertümlich; Tonwechsel; extreme Wortwiederholungen über Kapitel hinweg)
        - 'pacing' (Pacing-Probleme, sprunghafte Entwicklungen im Plotfluss)
        - 'grammar' (systematische Rechtschreib- oder Grammatikfehler im gesamten Buch oder in mehreren Kapiteln)
        
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
    model: str = "gemini-3.1-flash-lite",
    is_kids_book: bool = False,
    language: str = "de"
) -> Dict[str, Any]:
    """Improve / rewrite a single chapter outline based on feedback/instructions."""
    is_en = (language == "en")
    
    # If the outline has already been expanded, extract the clean summary to prevent recursive double-expansion.
    if current_plot_outline and ("--- Szene" in current_plot_outline or "--- Scene" in current_plot_outline):
        import re
        summary_match = re.match(r"^(?:Zusammenfassung|Summary):\s*(.*?)(?=\n\s*---\s*(?:Szene|Scene)|\n\n---\s*(?:Szene|Scene)|$)", current_plot_outline, re.DOTALL | re.IGNORECASE)
        if summary_match:
            current_plot_outline = summary_match.group(1).strip()
        else:
            parts = re.split(r"---\s*(?:Szene|Scene)\s*\d+\s*---", current_plot_outline, flags=re.IGNORECASE)
            if parts:
                current_plot_outline = parts[0].replace("Zusammenfassung:", "").replace("Summary:", "").strip()

    style_resolved = get_author_names_improved(style)
    
    if is_en:
        system_instruction = (
            "You are a bestselling novelist. You are helping revise and polish a single chapter outline "
            "based on user instructions. Respond strictly in JSON format."
            f"{get_kids_book_prompt(is_kids_book, language='en')}"
        )
        prompt_content = f"""
        Book background:
        - Book concept/plot: {project_prompt}
        - Genre: {genre}
        - Author style: {style_resolved}
        - Characters: {characters_bible}
        
        Complete Book Outline:
        {full_outline}
        
        Currently revising Chapter {chapter_number}:
        - Current Title: {current_title}
        - Current Plot/Outline: {current_plot_outline}
        
        User revision instructions:
        \"{instruction}\"
        
        Please revise this chapter based on the instruction and overall book context in English.
        Ensure it fits logically with the other chapters.
        
        Return a JSON object with:
        - title (Updated or retained chapter title)
        - plot_outline (Revised chapter plot outline, approx. 100-150 words)
        
        Format:
        {{
          "title": "...",
          "plot_outline": "..."
        }}
        """
    else:
        system_instruction = (
            "Du bist ein Bestseller-Autor. Du hilfst dabei, ein einzelnes Kapitel einer Buchgliederung (Outline) "
            "zu überarbeiten und zu verbessern. Antworte ausschließlich im JSON-Format."
            f"{get_kids_book_prompt(is_kids_book, language='de')}"
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
        \"{instruction}\"
        
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
    model: str = "gemini-3.1-flash-lite",
    target_words_per_chapter: int = 2500,
    genre_config: Optional[dict] = None,
    use_scene_beats: bool = True,
    language: str = "de"
) -> Dict[str, Any]:
    """Expands a single chapter outline into structured scene beats or a detailed 3-4 paragraph blueprint."""
    is_en = (language == "en")
    
    # If the outline has already been expanded, extract the clean summary to prevent recursive double-expansion.
    if current_plot_outline and ("--- Szene" in current_plot_outline or "--- Scene" in current_plot_outline):
        import re
        summary_match = re.match(r"^(?:Zusammenfassung|Summary):\s*(.*?)(?=\n\s*---\s*(?:Szene|Scene)|\n\n---\s*(?:Szene|Scene)|$)", current_plot_outline, re.DOTALL | re.IGNORECASE)
        if summary_match:
            current_plot_outline = summary_match.group(1).strip()
        else:
            parts = re.split(r"---\s*(?:Szene|Scene)\s*\d+\s*---", current_plot_outline, flags=re.IGNORECASE)
            if parts:
                current_plot_outline = parts[0].replace("Zusammenfassung:", "").replace("Summary:", "").strip()

    style_resolved = get_author_names_improved(style)
    
    if not use_scene_beats:
        if is_en:
            system_instruction = (
                "You are a bestselling novelist. Expand a brief chapter outline into a highly detailed, "
                "consistent 3 to 4 paragraph chapter blueprint in English. Respond strictly in JSON format."
            )
            prompt_content = f"""
            Book background:
            - Concept/plot: {project_prompt}
            - Genre: {genre}
            - Style: {style_resolved}
            - Characters: {characters_bible}
            
            Full Outline:
            {full_outline}
            
            Developing Chapter {chapter_number}:
            - Title: {current_title}
            - Brief outline: {current_plot_outline}
            
            Return a JSON object:
            - title
            - plot_outline (3-4 detailed paragraphs in English)
            """
        else:
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
            
    # New behavior: structured scene beats
    pov_hint = ""
    if genre_config and genre_config.get("pov") == "dual_alternating":
        if is_en:
            pov_hint = f"\nCRITICAL: Chapter {chapter_number} is told from the perspective of the {'female' if chapter_number % 2 == 1 else 'male'} protagonist."
        else:
            pov_hint = (
                f"\nWICHTIG: Dieses Kapitel ({chapter_number}) wird aus der Perspektive des "
                f"{'weiblichen' if chapter_number % 2 == 1 else 'männlichen'} Hauptcharakters erzählt. "
                f"Alle Szenen MÜSSEN aus dieser Perspektive geplant sein."
            )
    elif genre_config and genre_config.get("pov") == "single_female":
        pov_hint = "\nCRITICAL: All scenes MUST be from female protagonist POV." if is_en else "\nWICHTIG: Alle Szenen MÜSSEN aus der Perspektive des weiblichen Hauptcharakters erzählt sein."
    elif genre_config and genre_config.get("pov") == "single_male":
        pov_hint = "\nCRITICAL: All scenes MUST be from male protagonist POV." if is_en else "\nWICHTIG: Alle Szenen MÜSSEN aus der Perspektive des männlichen Hauptcharakters erzählt sein."
    elif genre_config and genre_config.get("pov") == "omniscient":
        if is_en:
            pov_hint = "\nCRITICAL: Narrative POV is Omniscient. Set 'pov_character' to 'Narrator' for all scenes."
        else:
            pov_hint = (
                "\nWICHTIG: Die gewählte Erzählperspektive ist 'Allwissend' (auktorialer Erzähler / allgemeiner Erzähler). "
                "Es gibt keinen einzelnen charaktergebundenen Point of View (POV). Alle Szenen MÜSSEN aus der allwissenden, "
                "übergeordneten Erzählerperspektive geschrieben sein. Setze für das Feld 'pov_character' bei allen Szenen "
                "konsequent 'Erzähler' ein."
            )
        
    recommended_scenes = max(3, min(7, target_words_per_chapter // 500))
    kids_book_clause = get_kids_book_prompt(genre_config.get('is_kids_book', False) if genre_config else False, language=language)
    
    if is_en:
        system_instruction = (
            "You are a bestselling novelist and story architect. Your task is to expand a brief chapter outline "
            "into a detailed structured sequence of scene beats in English. Respond strictly in JSON format."
            f"{kids_book_clause}"
        )
        prompt_content = f"""
        Book background:
        - Concept: {project_prompt}
        - Genre: {genre}
        - Author style: {style_resolved}
        - Characters: {characters_bible}
        
        Full Outline:
        {full_outline}
        
        Developing Chapter {chapter_number}:
        - Current Title: {current_title}
        - Current Outline: {current_plot_outline}
        {pov_hint}
        
        Create a scene beats structure with {recommended_scenes} to {recommended_scenes + 2} scenes in English.
        Target total chapter word count: approx. {target_words_per_chapter} words.
        
        CRITICAL:
        - Every scene must have a clear CONFLICT.
        - Scenes must flow logically.
        - The final scene should set a cliffhanger or hook.
        
        Return a JSON object:
        {{
          "title": "Chapter Title",
          "scene_beats": [
            {{
              "scene_number": 1,
              "pov_character": "POV Character Name",
              "setting": "Scene Setting/Location",
              "goal": "What does the POV character want?",
              "conflict": "What obstacle arises?",
              "outcome": "How does the scene conclude?",
              "emotional_arc": "Emotional shift (e.g. 'Doubt -> Resolve')",
              "estimated_words": 400
            }}
          ],
          "chapter_summary": "Brief summary of the entire chapter"
        }}
        """
    else:
        system_instruction = (
            "Du bist ein Bestseller-Autor und Story-Architekt. Deine Aufgabe ist es, eine kurze "
            "Kapitelgliederung zu einer detaillierten Szenen-Struktur auszuarbeiten. "
            "Jede Szene bekommt einen klaren dramaturgischen Aufbau mit Ziel, Konflikt und Ausgang. "
            "Antworte ausschließlich im JSON-Format."
            f"{kids_book_clause}"
        )
        prompt_content = f"""
        Rahmendaten des Buches:
        - Buchidee/Plot: {project_prompt}
        - Genre: {genre}
        - Autorenstil: {style_resolved}
        - Charaktere: {characters_bible}
        
        Gesamt-Gliederung des Buches:
        {full_outline}
        
        Wir arbeiten Kapitel {chapter_number} aus:
        - Aktueller Titel: {current_title}
        - Aktuelle Kurz-Gliederung: {current_plot_outline}
        {pov_hint}
        
        Erstelle eine Szenen-Struktur mit {recommended_scenes} bis {recommended_scenes + 2} Szenen.
        Das Kapitel soll insgesamt ca. {target_words_per_chapter} Wörter umfassen.
        Verteile das Wortbudget sinnvoll auf die Szenen (manche Szenen sind kürzer/länger).
        
        WICHTIG:
        - Jede Szene braucht einen klaren KONFLIKT – keine Szene ohne Spannung!
        - Die Szenen müssen logisch aufeinander aufbauen.
        - Die letzte Szene soll einen Hook/Cliffhanger für das nächste Kapitel setzen.
        - Emotional Arcs sollen variieren (nicht jede Szene gleich emotional aufgeladen).
        
        Gib ein JSON-Objekt mit diesen Feldern zurück:
        {{
          "title": "Kapitel-Titel",
          "scene_beats": [
            {{
              "scene_number": 1,
              "pov_character": "Name des POV-Charakters",
              "setting": "Wo spielt die Szene?",
              "goal": "Was will der POV-Charakter?",
              "conflict": "Was steht im Weg?",
              "outcome": "Wie endet die Szene?",
              "emotional_arc": "Emotionale Entwicklung (z.B. 'Angst → Entschlossenheit')",
              "estimated_words": 400
            }},
            ...
          ],
          "chapter_summary": "Kurze Zusammenfassung des gesamten Kapitels"
        }}
        """
    
    try:
        response = await generate_text(
            prompt=prompt_content,
            model=model,
            temperature=0.75,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=ExpandedChapterOutlineSchema
        )
        cleaned = clean_json_string(response)
        data = json.loads(cleaned)
        
        beats = data.get("scene_beats", [])
        formatted_outline = format_scene_beats_as_text(beats, language=language)
        
        chap_sum = current_plot_outline.strip() if current_plot_outline else data.get("chapter_summary", "").strip()
        if chap_sum:
            sum_header = "Summary" if is_en else "Zusammenfassung"
            formatted_outline = f"{sum_header}: {chap_sum}\n\n{formatted_outline}"
        
        pov_char = None
        if beats:
            pov_char = beats[0].get("pov_character")
            
        return {
            "title": data.get("title", current_title),
            "plot_outline": formatted_outline,
            "pov_character": pov_char
        }
    except Exception as e:
        logger.error(f"Error in expand_chapter_outline for chapter {chapter_number}: {e}")
        return {
            "title": current_title,
            "plot_outline": current_plot_outline
        }


async def apply_global_feedback_to_outline(
    characters_bible: str,
    current_outline: str,
    findings: List[Dict[str, Any]],
    model: str = "gemini-3.7-flash",
    language: str = "de"
) -> str:
    """
    Overwrites or adjusts the plot outlines in the book outline based on global proofreading findings.
    Returns the updated outline JSON string conforming to BookOutlineSchema.
    """
    is_en = (language == "en")
    
    if is_en:
        system_instruction = (
            "You are a senior acquisitions and developmental editor. "
            "Your task is to revise an existing book outline so that all identified findings and issues "
            "are resolved in English. Respond strictly in JSON format according to BookOutlineSchema."
        )
        findings_str_list = []
        for i, f in enumerate(findings, 1):
            cats = f.get("category", "Unknown")
            desc = f.get("description", "No description")
            chaps = f.get("chapters_involved", [])
            suggested = f.get("suggested_fix", "No fix")
            findings_str_list.append(
                f"Finding #{i} [{cats}]:\n"
                f"- Description: {desc}\n"
                f"- Affected Chapters: {chaps}\n"
                f"- Suggested Fix: {suggested}"
            )
        findings_str = "\n\n".join(findings_str_list)
        
        prompt = f"""
        Book reference data:
        - Character Bible: {characters_bible}
        
        Current Outline:
        {current_outline}
        
        Identified findings and issues:
        \"\"\"
        {findings_str}
        \"\"\"
        
        Task:
        Revise the outline (BookOutlineSchema) in English. Correct affected chapters to completely resolve the issues.
        Leave unaffected chapters intact.
        """
    else:
        system_instruction = (
            "Du bist ein leitender Bestseller-Lektor. "
            "Deine Aufgabe ist es, eine bestehende Buch-Gliederung (Outline) so zu überarbeiten, "
            "dass die gefundenen Fehler (Findings) korrigiert werden. "
            "Antworte ausschließlich im JSON-Format gemäß des vorgegebenen Schemas."
        )
        findings_str_list = []
        for i, f in enumerate(findings, 1):
            cats = f.get("category", "Unbekannt")
            desc = f.get("description", "Keine Beschreibung")
            chaps = f.get("chapters_involved", [])
            suggested = f.get("suggested_fix", "Kein Vorschlag")
            findings_str_list.append(
                f"Befund #{i} [{cats}]:\n"
                f"- Beschreibung: {desc}\n"
                f"- Betroffene Kapitel: {chaps}\n"
                f"- Lösungsvorschlag: {suggested}"
            )
        findings_str = "\n\n".join(findings_str_list)
        
        prompt = f"""
        Hier sind die Referenzdaten für das Buch:
        - Charakter-Bible: {characters_bible}
        
        Aktuelle Gliederung des Buches:
        {current_outline}
        
        Es wurden folgende inhaltliche und stilistische Probleme (Findings) identifiziert:
        \"\"\"
        {findings_str}
        \"\"\"
        
        Aufgabe:
        Überarbeite die Gliederung (BookOutlineSchema). Korrigiere die Gliederungen/Details der betroffenen Kapitel,
        um die beschriebenen Fehler und Widersprüche vollständig aufzulösen. 
        Halte dich dabei eng an die vorgeschlagenen Lösungen (suggested_fix). 
        Lass unbeteiligte Kapitel unverändert. Behalte den generellen Aufbau und das JSON-Format exakt bei.
        """
    
    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.3,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=BookOutlineSchema
        )
        return clean_json_string(response)
    except Exception as e:
        logger.error(f"Error in apply_global_feedback_to_outline: {e}")
        return current_outline


async def proofread_outline_globally(
    chapters: List[BookChapter], 
    characters_bible: str, 
    model: str = "gemini-3.7-flash",
    language: str = "de"
) -> List[Dict[str, Any]]:
    """
    Analyzes the plot outlines (blueprints) of all chapters for logical consistency,
    character contradictions, and pacing issues.
    """
    is_en = (language == "en")
    ch_lbl = "Chapter" if is_en else "Kapitel"
    
    # Concatenate all outlines with clear headers
    outline_parts = []
    for c in chapters:
        outline_parts.append(
            f"=== {ch_lbl} {c.chapter_number}: {c.title} ===\n"
            f"Outline/Blueprint: {c.plot_outline or ('[None]' if is_en else '[Keine Vorgabe]')}"
        )
    outline_text = "\n\n".join(outline_parts)
    
    if is_en:
        system_instruction = (
            "You are a senior acquisitions and developmental editor. "
            "Analyze the chapter blueprints/outlines for logical plot contradictions, "
            "character inconsistencies, and pacing flaws. Respond strictly in JSON format."
        )
        prompt = f"""
        Book reference data:
        - Character Bible: {characters_bible}
        
        Analyze the following chapter blueprints:
        \"\"\"
        {outline_text}
        \"\"\"
        
        Categorize issues into:
        - 'consistency' (Character continuity, contradictions, setting errors)
        - 'style' (Tonal shifts or target audience divergence)
        - 'pacing' (Pacing issues, jarring jumps between chapters)
        
        Return a list of findings in English:
        - category
        - description (Issue description in English)
        - chapters_involved (List of integers of affected chapters, e.g. [2, 4])
        - suggested_fix (Concrete recommendation in English)
        
        Format:
        [
          {{
            "category": "consistency",
            "description": "...",
            "chapters_involved": [2, 4],
            "suggested_fix": "..."
          }}
        ]
        """
    else:
        system_instruction = (
            "Du bist ein leitender Bestseller-Lektor. "
            "Analysiere die Gliederung (Kapitel-Entwürfe/Blueprints) des Buches auf inhaltliche Widersprüche, "
            "Logikfehler, Charakter-Inkonsistenz und Pacing-Probleme zwischen den Kapiteln. "
            "Antworte ausschließlich im JSON-Format."
        )
        prompt = f"""
        Hier sind die Referenzdaten für das Buch:
        - Charakter-Bible: {characters_bible}
        
        Analysiere die folgenden Kapitel-Entwürfe (Blueprints/Outlines) auf logische Widersprüche, Charakter-Inkonsistenzen und Pacing-Probleme:
        
        KAPITEL-ENTWÜRFE:
        \"\"\"
        {outline_text}
        \"\"\"
        
        Kategorisiere die Probleme in:
        - 'consistency' (z. B. eine Figur stirbt in Kapitel 2, taucht aber in Kapitel 4 wieder auf; Augenfarbe ändert sich; Mia ist eine Eule, wird aber plötzlich als Katze bezeichnet)
        - 'style' (z. B. abrupte Tonwechsel in den Beschreibungen oder Zielgruppenverschiebungen)
        - 'pacing' (Pacing-Probleme, extreme Handlungssprünge zwischen den Kapitel-Blaupausen)
        
        Gib eine Liste von Problemen zurück. Jedes Problem muss folgende Felder haben:
        - category (eine der 3 Kategorien oben)
        - description (Beschreibung des Fehlers auf Deutsch)
        - chapters_involved (eine Liste von Integers der Kapitelnummern, die von diesem Problem betroffen sind, z.B. [2, 4])
        - suggested_fix (Konkreter Vorschlag für die Korrektur der Kapitel-Gliederung auf Deutsch)
        
        Format:
        [
          {{
            "category": "consistency",
            "description": "...",
            "chapters_involved": [2, 4],
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
        logger.error(f"Error in proofread_outline_globally: {e}")
        return []


# --- Series AI Workflows ---

async def generate_series_architecture(
    title: str,
    description: str,
    genre: str,
    style: str,
    genre_config: Optional[dict] = None,
    planned_volumes: Optional[int] = None,
    model: str = "gemini-3.7-flash",
    language: str = "de"
) -> Dict[str, Any]:
    """
    Generates full worldbuilding/lore, master characters, cover styleguide,
    series arc, and Volume 1 concept for a brand-new book series.
    """
    style_resolved = get_author_names_improved(style)
    from app.services.genre_profiles import build_genre_prompt_section
    g_config = genre_config or {}
    genre_section = build_genre_prompt_section(
        genre,
        selected_tropes=g_config.get("tropes", []),
        pov=g_config.get("pov"),
        spice_level=g_config.get("spice_level")
    )
    is_en = (language == "en")
    
    if is_en:
        vol_text = f"The series is planned for approx. {planned_volumes} volumes." if planned_volumes else "The series is planned as an ongoing, open-ended book franchise."
        system_instruction = (
            "You are a master series architect, worldbuilder, and bestselling author. "
            "Design the foundational series universe, recurring master characters, "
            "cover design system, and Volume 1 premise in English. Respond strictly in JSON format."
            f"{get_kids_book_prompt(g_config.get('is_kids_book', False), language='en')}"
        )
        prompt = f"""
        New Book Series Data:
        - Series Title: {title}
        - Core Premise / Conflict: {description}
        - Genre: {genre}
        - Author style: {style_resolved}
        - Scope: {vol_text}
        
        {genre_section}
        
        Create a comprehensive Series Architecture in English:
        1. 'world_lore': Detailed worldbuilding (Setting, magic/technology rules, factions, history).
        2. 'characters': 4 to 6 archetypal recurring master characters (with 'name', 'role', 'description', 'traits').
        3. 'cover_style_prompt': Detailed image prompt template in ENGLISH for book covers of this series ('Series title prominent at top, Volume number banner, Book title in center, author Dirk Proessel at bottom').
        4. 'series_arc': Overarching multi-book story arc and milestones (e.g. 'Volume 1: ..., Volume 2: ..., Volume 3: ...').
        5. 'volume_1_title': Catchy, creative book title for Volume 1 in English.
        6. 'volume_1_subtitle': Subtitle (e.g. 'Volume 1: The Secret of Shadows').
        7. 'volume_1_prompt': Concrete plot premise for Volume 1 in English.
        """
    else:
        vol_text = f"Die Serie ist auf ca. {planned_volumes} Bände ausgelegt." if planned_volumes else "Die Serie ist als fortlaufende, offene Buchreihe angelegt."
        system_instruction = (
            "Du bist ein hochkarätiger Serien-Architekt, Weltenbauer und Bestseller-Autor. "
            "Deine Aufgabe ist es, für eine neue Buch-Serie das fundamentale Serien-Universum, "
            "die wiederkehrenden Stamm-Charaktere, das Cover-Design-System und den Einstieg für Band 1 zu entwerfen. "
            "Antworte ausschließlich im JSON-Format."
            f"{get_kids_book_prompt(g_config.get('is_kids_book', False), language='de')}"
        )
        prompt = f"""
        Rahmendaten der neuen Buch-Serie:
        - Serientitel: {title}
        - Serien-Prämisse / Kernkonflikt: {description}
        - Genre: {genre}
        - Autorenstil: {style_resolved}
        - Umfang: {vol_text}
        
        {genre_section}
        
        Erstelle eine umfassende Serien-Architektur:
        1. 'world_lore': Ausführliches Worldbuilding (Setting, Regeln, Magie/Technologie, Schauplätze, Fraktionen und Hintergrundgeschichte).
        2. 'characters': 4 bis 6 archetypische, vielschichtige Stamm-Charaktere, die über mehrere Bände tragen (mit 'name', 'role', 'description', 'traits').
        3. 'cover_style_prompt': Ein detailliertes Prompt-Template auf ENGLISCH für Buchcover dieser Serie. Es muss den Art-Style (z. B. Oil painting, Cinematic digital art), die Farbpalette, Beleuchtung und das typografische Layout ('Series title prominent at top, Volume number banner, Book title in center, author Dirk Proessel at bottom') beschreiben.
        4. 'series_arc': Die übergeordnete Story-Entwicklung und Meilensteine der einzelnen Bände (z. B. 'Band 1: ..., Band 2: ..., Band 3: ...').
        5. 'volume_1_title': Ein packender, kreativer Buchtitel für Band 1.
        6. 'volume_1_subtitle': Ein passender Untertitel (z. B. 'Band 1: Das Geheimnis der Schatten').
        7. 'volume_1_prompt': Konkrete Handlungsidee / Plot-Prämisse für Band 1, die als Ausgangspunkt für die Kapitelgliederung dient.
        """

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=SeriesArchitectureSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in generate_series_architecture: {e}")
        # Fallback basic structure
        return {
            "world_lore": f"The universe of {title}." if is_en else f"Das Universum von {title}. Ein Schauplatz voller Abenteuer im Genre {genre}.",
            "characters": [
                {"name": "Protagonist", "role": "Protagonist", "description": "The main hero." if is_en else "Der Hauptcharakter der Reihe.", "traits": ["brave", "determined"] if is_en else ["mutig", "entschlossen", "loyal"]}
            ],
            "cover_style_prompt": f"Professional cinematic book cover design for {genre} series, bold typography title at top, author Dirk Proessel at bottom, highly detailed art style.",
            "series_arc": "Volume 1: Introduction and initial conflict." if is_en else "Band 1: Einführung und erster Konflikt.",
            "volume_1_title": f"{title} - The Beginning" if is_en else f"{title} - Der Anfang",
            "volume_1_subtitle": "Volume 1" if is_en else "Band 1",
            "volume_1_prompt": description
        }


async def extract_series_from_book(
    project: BookProject,
    chapters: List[BookChapter],
    model: str = "gemini-3.7-flash",
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts overarching series worldbuilding, lore, master characters bible,
    and cover style from an existing book project to turn it into Band 1.
    """
    lang = language or getattr(project, "language", "de") or "de"
    is_en = (lang == "en")
    ch_lbl = "Chapter" if is_en else "Kapitel"
    
    chapter_summaries = []
    for c in chapters:
        summary_text = c.running_summary or (c.content[:300] + "..." if c.content else c.plot_outline)
        chapter_summaries.append(f"{ch_lbl} {c.chapter_number} ({c.title}): {summary_text}")
    full_synopsis = "\n".join(chapter_summaries) or project.prompt

    existing_chars = project.characters_bible or ("No character bible provided." if is_en else "Keine explizite Charakter-Bibel vorhanden.")
    existing_cover = project.cover_prompt or ("No cover prompt provided." if is_en else "Kein Cover-Prompt vorhanden.")

    if is_en:
        system_instruction = (
            "You are a senior editor and series architect. "
            "Analyze an existing book and extract the overarching worldbuilding, recurring characters, "
            "and visual cover design system in English to turn this book into Volume 1 of a series. "
            "Respond strictly in JSON format."
        )
        prompt = f"""
        Existing Book Data (Volume 1):
        - Title: {project.title}
        - Genre: {project.genre}
        - Style: {project.style}
        - Premise: {project.prompt}
        - Existing Characters:
        {existing_chars}
        - Existing Cover Prompt:
        {existing_cover}
        - Book Synopsis / Story so far:
        \"\"\"
        {full_synopsis[:4000]}
        \"\"\"
        
        Extract and structure the series foundation in English:
        1. 'world_lore': Overarching worldbuilding (rules, setting, factions, history).
        2. 'characters': Recurring master cast of the series.
        3. 'cover_style_prompt': Standardized cover design prompt template in ENGLISH.
        4. 'series_arc': Proposed overarching series arc for upcoming sequels.
        """
    else:
        system_instruction = (
            "Du bist ein Bestseller-Lektor und Serien-Architekt. "
            "Analysiere ein bestehendes Buch und extrahiere das übergeordnete Worldbuilding, "
            "die wiederkehrenden Stamm-Charaktere und das visuelle Cover-Design-System, "
            "um dieses Buch in den ersten Band einer mehrteiligen Serie umzuwandeln. "
            "Antworte ausschließlich im JSON-Format."
        )
        prompt = f"""
        Hier sind die Daten des bestehenden Buches (Band 1):
        - Buchtitel: {project.title}
        - Genre: {project.genre}
        - Autorenstil: {project.style}
        - Ausgangsidee: {project.prompt}
        - Bestehende Charaktere:
        {existing_chars}
        - Bisheriges Cover-Design / Prompt:
        {existing_cover}
        - Handlungsverlauf des Buches:
        \"\"\"
        {full_synopsis[:4000]}
        \"\"\"
        
        Extrahiere und strukturiere die Serien-Grundlagen:
        1. 'world_lore': Das übergeordnete Worldbuilding (Setting, Regeln, Magie/Technik, Schauplätze, Zeitlinie).
        2. 'characters': Die wiederkehrenden Stamm-Charaktere der Serie mit Aussehen, Hintergrund und Motivation.
        3. 'cover_style_prompt': Ein standardisiertes Cover-Design-Prompt-Template auf ENGLISCH, das den visuellen Stil, die Beleuchtung und das typografische Layout dieses Franchise festlegt.
        4. 'series_arc': Ein Vorschlag für einen übergeordneten Handlungsbogen für Fortsetzungen (Band 2, Band 3 etc.).
        """

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=SeriesExtractedSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in extract_series_from_book: {e}")
        chars_list = []
        try:
            if project.characters_bible:
                parsed = json.loads(clean_json_string(project.characters_bible))
                if isinstance(parsed, list):
                    chars_list = parsed
        except Exception:
            pass
        return {
            "world_lore": f"The universe of '{project.title}'." if is_en else f"Das Setting und Universum von '{project.title}' im Genre {project.genre}.",
            "characters": chars_list or [{"name": "Protagonist", "role": "Protagonist", "description": "Main hero", "traits": ["brave"]}],
            "cover_style_prompt": project.cover_prompt or f"Cinematic book cover art style for {project.genre} series, bold title layout, author Dirk Proessel.",
            "series_arc": f"Volume 1: {project.title} - Continued in Volume 2." if is_en else f"Band 1: {project.title} - Die Geschichte wird in Band 2 fortgesetzt."
        }


async def suggest_sequel_pitches(
    series: BookSeries,
    previous_books: List[BookProject],
    latest_book_summary: str,
    model: str = "gemini-3.7-flash",
    language: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generates 3 distinct and engaging sequel pitches for the next volume of a series.
    """
    lang = language or getattr(series, "language", "de") or "de"
    is_en = (lang == "en")
    next_volume_number = len(previous_books) + 1
    vol_lbl = "Volume" if is_en else "Band"
    prev_titles = ", ".join([f"{vol_lbl} {b.series_order or i+1}: {b.title}" for i, b in enumerate(previous_books)])

    if is_en:
        system_instruction = (
            "You are a lead story architect and bestselling author. "
            f"Develop 3 compelling, distinct plot pitches for Volume {next_volume_number} of a book series in English. "
            "Respond strictly in JSON format."
        )
        prompt = f"""
        Series Information:
        - Series Title: {series.title}
        - Premise: {series.description}
        - Genre: {series.genre}
        - Author Style: {series.style}
        - Preceding Volumes: {prev_titles}
        - Worldbuilding & Lore: {series.world_lore or 'Not provided'}
        - Master Cast: {series.characters_bible or 'Not provided'}
        - Series Arc: {series.series_arc or 'Not provided'}
        
        Plot of the latest volume (Status quo / cliffhangers / loose ends):
        \"\"\"
        {latest_book_summary}
        \"\"\"
        
        Develop exactly 3 distinct directions for Volume {next_volume_number} in English:
        1. Pitch 1: 'Direct Continuation / Aftermath'
        2. Pitch 2: 'New Threat / New Case'
        3. Pitch 3: 'Escalation & Revelations'
        
        Each pitch must have:
        - 'title': Strong book title
        - 'subtitle': 'Volume {next_volume_number}: [Catchy subtitle]'
        - 'pitch': Blurb description (approx. 80-120 words)
        - 'core_conflict': The central conflict
        - 'tone': The narrative tone
        """
    else:
        system_instruction = (
            "Du bist ein leitender Story-Architect und Bestseller-Autor. "
            f"Entwickle 3 packende, unterschiedliche Handlungs-Pitches für Band {next_volume_number} einer Buch-Serie. "
            "Antworte ausschließlich im JSON-Format."
        )
        prompt = f"""
        Serien-Informationen:
        - Serientitel: {series.title}
        - Serien-Prämisse: {series.description}
        - Genre: {series.genre}
        - Autorenstil: {series.style}
        - Bisherige Bände: {prev_titles}
        - Worldbuilding & Lore: {series.world_lore or 'Keine Angabe'}
        - Stamm-Charaktere: {series.characters_bible or 'Keine Angabe'}
        - Serien-Handlungsbogen: {series.series_arc or 'Keine Angabe'}
        
        Handlung des letzten Bandes (Status Quo / Finale / Offene Fäden):
        \"\"\"
        {latest_book_summary}
        \"\"\"
        
        Entwickle genau 3 unterschiedliche Richtungen für Band {next_volume_number}:
        1. Pitch 1: 'Direkte Fortsetzung / Konsequenzen' (Schließt direkt an das Ende an, löst Cliffhanger oder unmittelbare Folgen).
        2. Pitch 2: 'Neues Abenteuer / Neuer Fall' (Etwas zeitlicher Abstand, eine neue akute Bedrohung, die den Stamm-Cast fordert).
        3. Pitch 3: 'Eskalation & Enthüllung' (Die Einsätze verdoppeln sich, alte Geheimnisse aus der Serien-Lore kommen ans Licht).
        
        Jeder Pitch muss haben:
        - 'title': Ein starker Buchtitel für Band {next_volume_number}
        - 'subtitle': 'Band {next_volume_number}: [Passender Band-Untertitel]'
        - 'pitch': Ausführlicher Klappentext (ca. 80-120 Wörter)
        - 'core_conflict': Der zentrale Konflikt
        - 'tone': Die Ausrichtung / Stimmung
        """

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.75,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=SequelPitchesResponseSchema
        )
        cleaned = clean_json_string(response)
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data.get("pitches", [])
        return data
    except Exception as e:
        logger.error(f"Error in suggest_sequel_pitches: {e}")
        return [
            {
                "title": f"{series.title} - {vol_lbl} {next_volume_number}",
                "subtitle": f"{vol_lbl} {next_volume_number}: The Next Chapter" if is_en else f"Band {next_volume_number}: Das nächste Kapitel",
                "pitch": "The adventures continue with a new challenge facing the heroes." if is_en else "Die Abenteuer gehen weiter. Eine neue Herausforderung wartet auf die Helden.",
                "core_conflict": "A new unforeseen conflict.",
                "tone": "Exciting and suspenseful" if is_en else "Spannend und handlungsgetrieben"
            }
        ]


async def evolve_and_suggest_characters(
    series_characters_bible: str,
    previous_summary: str,
    sequel_pitch: str,
    genre: str,
    style: str,
    model: str = "gemini-3.1-flash-lite",
    is_kids_book: bool = False,
    language: str = "de"
) -> Dict[str, Any]:
    """
    Evolves the returning master cast from the series bible and suggests 2-3 new characters tailored to the sequel.
    """
    is_en = (language == "en")
    style_resolved = get_author_names_improved(style)
    
    if is_en:
        system_instruction = (
            "You are a character designer and novelist. "
            "Evolve the existing returning cast of a book series and create 2 to 3 new characters "
            "essential for the sequel in English. Respond strictly in JSON format."
            f"{get_kids_book_prompt(is_kids_book, language='en')}"
        )
        prompt = f"""
        Genre: {genre}
        Author style: {style_resolved}
        
        Returning Master Cast:
        {series_characters_bible}
        
        The Story So Far:
        {previous_summary}
        
        Plot of the new volume:
        {sequel_pitch}
        
        Task:
        1. 'evolved_characters': Update returning characters' descriptions, relationships, and goals for the beginning of this volume in English.
        2. 'new_characters': Create 2 to 3 new characters tailored for this volume.
        """
    else:
        system_instruction = (
            "Du bist ein Charakter-Designer und Romanautor. "
            "Entwickle die bestehenden Figuren einer Buch-Serie basierend auf den vergangenen Ereignissen weiter "
            "und erstelle 2 bis 3 neue Figuren, die für die Handlung der Fortsetzung unerlässlich sind. "
            "Antworte ausschließlich im JSON-Format."
            f"{get_kids_book_prompt(is_kids_book, language='de')}"
        )
        prompt = f"""
        Genre: {genre}
        Autorenstil: {style_resolved}
        
        Bisherige Stamm-Charaktere der Serie:
        {series_characters_bible}
        
        Was bisher geschah (Vergangene Ereignisse & Entwicklungen):
        {previous_summary}
        
        Handlung des neuen Bandes:
        {sequel_pitch}
        
        Aufgabe:
        1. 'evolved_characters': Nimm die bisherigen Stamm-Charaktere und aktualisiere ihre Beschreibungen, Beziehungen, Traumata und Ziele passend zum Beginn dieses neuen Bandes.
        2. 'new_characters': Erfinde 2 bis 3 neue, faszinierende Charaktere speziell für diesen neuen Band (z. B. neuer Antagonist, wichtiger Informant, Rivale oder Verbündeter).
        """

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.7,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=CharacterEvolutionSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in evolve_and_suggest_characters: {e}")
        return {
            "evolved_characters": [],
            "new_characters": []
        }


async def suggest_series_cover_prompt(
    series_title: str,
    series_cover_template: str,
    volume_number: int,
    volume_title: str,
    volume_prompt: str,
    genre: str,
    style: str,
    model: str = "gemini-3.1-flash-lite"
) -> str:
    """
    Generates a cover prompt for Band N that strictly maintains visual continuity with the series cover styleguide.
    """
    system_instruction = (
        "Du bist ein Experte für Buchcover-Design und Bild-Prompt-Engineering für Buchreihen. "
        "Erstelle einen englischen Cover-Prompt für den Folgeband einer Serie. "
        "WICHTIG: Behalte den Kunststil, die Farbharmonie und die Typografie-Struktur des Serien-Styleguides exakt bei, "
        "passe aber das Hauptmotiv, die Bandnummer und den Buchtitel an den Inhalt dieses Bandes an. "
        "Antworte ausschließlich mit dem fertigen englischen Prompt ohne Einleitung."
    )

    prompt = f"""
    Serien-Styleguide & Cover-Template:
    \"\"\"
    {series_cover_template}
    \"\"\"

    Angaben zum neuen Band:
    - Serientitel: {series_title}
    - Bandnummer: Band {volume_number} (Volume {volume_number})
    - Buchtitel: {volume_title}
    - Handlungsinhalt / Thema dieses Bandes: {volume_prompt}
    - Genre: {genre}
    - Stil: {style}

    Anweisungen für den neuen Prompt:
    1. Der Prompt muss auf ENGLISCH sein.
    2. Der Typografie-Aufbau MUSS konsistent bleiben: Serientitel "{series_title}" oben, Bandnummer "Band {volume_number}" bzw. "Vol. {volume_number}", Buchtitel "{volume_title}" in großer eleganter Schrift, Autorenname "Dirk Proessel" unten.
    3. Das visuelle Motiv muss die Schlüsselszene/das Thema des neuen Bandes darstellen, aber in genau demselben Rendering-Stil, Lighting und Farbpalette wie im Serien-Styleguide definiert.
    """

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.7,
            system_instruction=system_instruction
        )
        return response.strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"Error in suggest_series_cover_prompt: {e}")
        return f"Professional book cover design for {series_title} Volume {volume_number}: {volume_title}, maintaining franchise visual identity, author Dirk Proessel."


# ---------------------------------------------------------------------------
# Anthology / Short Story Collection Synthesis
# ---------------------------------------------------------------------------

class AnthologySynthesisSchema(BaseModel):
    title: str = Field(description="Ein verkaufsstarker, packender Gesamttitel für den Sammelband")
    subtitle: str = Field(description="Ein ansprechender Untertitel")
    blurb: str = Field(description="Ein mitreißender Klappentext / Buchbeschreibung, der die Vielfalt der enthaltenen Geschichten anteasert")
    foreword: str = Field(description="Ein poetisches Vorwort / Einleitung für den Sammelband (150-250 Wörter)")
    cover_prompt: str = Field(description="Ein detaillierter, englischer Bildprompt für die Cover-Generierung")
    epub_dedication: str = Field(description="Eine passende Widmung (2-4 Zeilen)")
    epub_afterword: str = Field(description="Ein kurzes Nachwort (100-150 Wörter)")


async def synthesize_anthology_concept(
    story_items: List[Dict[str, Any]],
    genre: str = "Erotik",
    style: str = "Anaïs Nin",
    author: Optional[str] = None,
    language: str = "de",
    model: str = "gemini-3.7-flash"
) -> Dict[str, Any]:
    """
    Synthesizes an anthology / short story collection from a list of individual stories:
    suggests a catchy book title, subtitle, blurb, foreword, cover prompt, and afterword.
    """
    is_en = (language == "en")
    count = len(story_items)
    
    stories_summary = []
    for idx, s in enumerate(story_items, 1):
        t = s.get("title", f"Story {idx}")
        syn = s.get("synopsis") or s.get("description") or ""
        stories_summary.append(f"{idx}. «{t}»: {syn[:250]}")
    
    stories_text = "\n".join(stories_summary)
    author_display = author or ("Dirk Proessel" if not is_en else "Dirk Proessel")

    if is_en:
        system_instruction = (
            "You are a bestselling editor, book designer, and publisher. "
            "Synthesize a cohesive, high-converting short story collection / anthology "
            "from the provided individual stories. Respond strictly in JSON format."
        )
        prompt = f"""
        Genre: {genre}
        Writing style: {style}
        Number of stories: {count}
        Author / Pen name: {author_display}
        
        Included stories:
        {stories_text}
        
        Task:
        1. 'title': A magnetic, evocative anthology book title (e.g. including theme or count, like '{count} Sensual Nights').
        2. 'subtitle': A compelling subtitle (e.g. 'An Exclusive Anthology of {count} Short Stories').
        3. 'blurb': An exciting, high-converting book description (2-3 paragraphs) teasing the emotional variety of stories.
        4. 'foreword': An atmospheric introduction / preface (150-250 words) inviting the reader into this collection.
        5. 'cover_prompt': A detailed, cinematic ENGLISH cover art prompt for Imagen 3 / Flux representing the core atmosphere, with space for title and author '{author_display}'.
        6. 'epub_dedication': A poetic dedication (2-4 lines).
        7. 'epub_afterword': A thoughtful afterword (100-150 words).
        """
    else:
        system_instruction = (
            "Du bist ein renommierter Verlags-Lektor, Buchdesigner und Bestseller-Autor. "
            "Erstelle aus den bereitgestellten Einzelgeschichten ein stimmiges, verkaufsstarkes Gesamtkonzept "
            "für einen Kurzgeschichten-Sammelband (Anthologie). Antworte ausschließlich im JSON-Format."
        )
        prompt = f"""
        Genre: {genre}
        Autorenstil: {style}
        Anzahl der Geschichten: {count}
        Autoren- / Künstlername: {author_display}
        
        Enthaltene Geschichten:
        {stories_text}
        
        Aufgabe:
        1. 'title': Ein magnetischer, packender Buchtitel für den Sammelband (z. B. '{count} Sinnliche Nächte: Erotische Geschichten' oder passend zum Thema).
        2. 'subtitle': Ein ansprechender Untertitel (z. B. 'Ein exklusiver Sammelband mit {count} verführerischen Geschichten').
        3. 'blurb': Ein mitreißender Klappentext (2–3 Absätze), der die emotionale Bandbreite und Höhepunkte der Geschichten anteasert.
        4. 'foreword': Ein stimmungsvolles Vorwort / Einleitung des Autors (150–250 Wörter), das den Leser in die Welt des Bandes entführt.
        5. 'cover_prompt': Ein detaillierter, englischer Bildprompt für die Cover-Generierung (Imagen 3 / Flux), der die Atmosphäre visualisiert und Raum für den Buchtitel und Autorenname '{author_display}' lässt.
        6. 'epub_dedication': Eine poetische Widmung (2–4 Zeilen).
        7. 'epub_afterword': Ein reflektierendes Nachwort (100–150 Wörter).
        """

    try:
        from app.services.text_generator import generate_text
        response = await generate_text(
            prompt=prompt,
            model=model,
            temperature=0.75,
            response_mime_type="application/json",
            system_instruction=system_instruction,
            response_schema=AnthologySynthesisSchema
        )
        cleaned = clean_json_string(response)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Error in synthesize_anthology_concept: {e}")
        default_title = f"{count} {genre}-Geschichten" if not is_en else f"{count} {genre} Stories"
        return {
            "title": default_title,
            "subtitle": f"Ein Sammelband mit {count} Geschichten" if not is_en else f"A Collection of {count} Stories",
            "blurb": f"Eine faszinierende Sammlung von {count} Geschichten im Genre {genre}.",
            "foreword": f"Willkommen zu diesem Sammelband mit {count} ausgewählten Geschichten.",
            "cover_prompt": f"Artistic book cover illustration for {genre} story collection titled {default_title}, elegant lighting, high quality, author {author_display}.",
            "epub_dedication": "Für alle Liebhaber guter Geschichten.",
            "epub_afterword": "Vielen Dank fürs Lesen dieser Geschichtensammlung."
        }






