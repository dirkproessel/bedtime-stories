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

class SceneBeatSchema(BaseModel):
    scene_number: int = Field(description="Fortlaufende Nummer der Szene (1-basiert)")
    pov_character: str = Field(description="Name des Charakter, aus dessen Perspektive erzählt wird")
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
    "gemini-3.5-flash": 1048576,       # 1M tokens
    "gemini-3.1-flash-lite": 1048576,
    "gemini-3.1-pro-preview": 2097152,  # 2M tokens
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

def format_scene_beats_as_text(beats: list) -> str:
    """Konvertiert Scene Beats in lesbaren Text für das plot_outline-Feld."""
    lines = []
    for beat in beats:
        sn = beat.get("scene_number", "?")
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
    """Strip markdown code blocks around JSON if present."""
    s = s.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
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
    
    # Pattern for "Kapitel X", "Kapitel X: ...", "Kapitel X - ..."
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

async def suggest_characters(prompt: str, genre: str, style: str, model: str = "gemini-3.1-flash-lite") -> List[Dict[str, Any]]:
    """Generate 3-5 character suggestions based on a book idea."""
    style_resolved = get_author_names_improved(style)
    from app.services.genre_profiles import get_genre_profile
    profile = get_genre_profile(genre)
    genre_context = ""
    if profile.id != "default":
        genre_context = f"\nGenre-spezifische Anforderungen: {profile.description}\n"
        if profile.emotional_arc_template:
            genre_context += f"Emotionaler Bogen: {profile.emotional_arc_template}\n"

    system_instruction = (
        "Du bist ein erfahrener Romanautor und Charakter-Designer. "
        f"{genre_context}"
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
    instruction: Optional[str] = None,
    genre_config: Optional[dict] = None
) -> Dict[str, Any]:
    """Generate a chapter outline for the book."""
    style_resolved = get_author_names_improved(style)
    
    # Parse genre config and build genre-specific prompt section
    from app.services.genre_profiles import build_genre_prompt_section
    g_config = genre_config or {}
    genre_section = build_genre_prompt_section(
        genre,
        selected_tropes=g_config.get("tropes", []),
        pov=g_config.get("pov"),
        spice_level=g_config.get("spice_level")
    )
    
    system_instruction = (
        "Du bist ein Bestseller-Autor. Entwerfe eine spannende, kapitelweise Gliederung (Outline) "
        "für eine Novelle. Antworte ausschließlich im JSON-Format."
    )
    
    instruction_str = f"\nNutzer-Anweisung/Kritik zur Berücksichtigung für diese Gliederung:\n\"{instruction}\"\n" if instruction else ""
    
    prompt_content = f"""
    Buchidee: {prompt}
    
    {genre_section}
    
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
    """Generate prose for a chapter utilizing a sliding window context and scene beats if available."""
    # Build character bible string
    chars_str = project.characters_bible or "Keine Angabe"
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
    outline_str = "\n".join([f"Kapitel {c.get('chapter_number')}: {c.get('title')} - {c.get('plot_outline')}" for c in outline_chapters])
    
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
        past_summaries.append(f"Kapitel {c.chapter_number} ({c.title}): {c.running_summary or 'Inhalt geschrieben.'}")
    past_summaries_str = "\n".join(past_summaries) if past_summaries else ""

    # Build full-text sections for recent chapters
    fulltext_sections = []
    for c in fulltext_chapters:
        fulltext_sections.append(
            f"=== VOLLTEXT KAPITEL {c.chapter_number}: {c.title} ===\n"
            f"{c.content or 'Kein Inhalt vorhanden.'}"
        )
    fulltext_str = "\n\n---\n\n".join(fulltext_sections) if fulltext_sections else "Dies ist das erste Kapitel des Buches."
        
    feedback_clause = ""
    if feedback:
        feedback_clause = f"\n**WICHTIGE ÄNDERUNGSANWEISUNG VOM USER (Für diesen Rewrite):**\n\"{feedback}\"\nBitte überarbeite das Kapitel und beachte diese Anweisung unbedingt!"

    # Detect if plot_outline is scene beats structured
    scenes = []
    if chapter.plot_outline and "--- Szene" in chapter.plot_outline:
        import re
        sections = re.split(r"--- Szene \d+ ---", chapter.plot_outline, flags=re.IGNORECASE)
        for i in range(1, len(sections)):
            text = sections[i].strip()
            scene = {"scene_number": i}
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("POV:"):
                    scene["pov_character"] = line[4:].strip()
                elif line.startswith("Ort:"):
                    scene["setting"] = line[4:].strip()
                elif line.startswith("Ziel:"):
                    scene["goal"] = line[5:].strip()
                elif line.startswith("Konflikt:"):
                    scene["conflict"] = line[9:].strip()
                elif line.startswith("Ausgang:"):
                    scene["outcome"] = line[8:].strip()
                elif line.startswith("Emotion:"):
                    scene["emotional_arc"] = line[8:].strip()
                elif line.startswith("Wörter:"):
                    scene["estimated_words"] = line[7:].strip()
            scenes.append(scene)

    if scenes:
        logger.info(f"Generating chapter {chapter.chapter_number} scene-by-scene ({len(scenes)} scenes)")
        chapter_prose = ""
        import re
        
        # Extract chapter summary if present in outline
        current_summary = ""
        if chapter.plot_outline:
            sum_match = re.match(r"^Zusammenfassung:\s*(.*?)\n\n", chapter.plot_outline, re.DOTALL | re.IGNORECASE)
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
            
            prev_scenes_context = ""
            if chapter_prose:
                prev_scenes_context = f"\nBisher geschriebene Szenen für dieses Kapitel (setze nahtlos und flüssig fort):\n{chapter_prose}\n"
            else:
                prev_scenes_context = "\nDies ist der Anfang dieses Kapitels. Beginne direkt mit dem ersten Satz.\n"
                
            scene_prompt = f"""
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
    
    Aktuelles Kapitel: Kapitel {chapter.chapter_number} - \"{chapter.title}\"
    {f"Zusammenfassung des Kapitels: {current_summary}" if current_summary else ""}
    
    {prev_scenes_context}
    
    ---
    
    AUFGABE:
    Schreibe jetzt die Romanprosa für **Szene {scene['scene_number']}** (von insgesamt {len(scenes)} Szenen in diesem Kapitel).
    
    Szenen-Vorgaben:
    - POV: {scene.get('pov_character', chapter.pov_character or 'Hauptcharakter')} (Schreibe konsequent aus dieser Perspektive!)
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
    4. Setze den bisherigen Text nahtlos und stilistisch identisch fort. Wiederhole keine Ereignisse, die bereits im bisherigen Text stattgefunden haben.
    5. Füge keine Überschriften, Kapitel- oder Szenennummern (wie 'Szene 1') oder Trennlinien ein. Beginne direkt mit der Romanprosa.
    """
            
            # Token budget check
            model_limit = MODEL_CONTEXT_LIMITS.get(model, 32000)
            scene_max_tokens = int(words * 1.5 + 1000)
            input_budget = model_limit - scene_max_tokens - 2000
            
            total_input_tokens = estimate_tokens(scene_prompt)
            if total_input_tokens > input_budget:
                logger.warning(f"Context overflow in scene {scene['scene_number']}: {total_input_tokens} > {input_budget}. Truncating outline.")
                temp_outline_str = truncate_to_budget(outline_str, max(500, input_budget // 4))
                # Re-build scene_prompt with truncated outline
                scene_prompt = f"""
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
    
    Aktuelles Kapitel: Kapitel {chapter.chapter_number} - \"{chapter.title}\"
    {f"Zusammenfassung des Kapitels: {current_summary}" if current_summary else ""}
    
    {prev_scenes_context}
    
    ---
    
    AUFGABE:
    Schreibe jetzt die Romanprosa für **Szene {scene['scene_number']}** (von insgesamt {len(scenes)} Szenen in diesem Kapitel).
    
    Szenen-Vorgaben:
    - POV: {scene.get('pov_character', chapter.pov_character or 'Hauptcharakter')} (Schreibe konsequent aus dieser Perspektive!)
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
    4. Setze den bisherigen Text nahtlos und stilistisch identisch fort. Wiederhole keine Ereignisse, die bereits im bisherigen Text stattgefunden haben.
    5. Füge keine Überschriften, Kapitel- oder Szenennummern (wie 'Szene 1') oder Trennlinien ein. Beginne direkt mit der Romanprosa.
    """
            
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
            )
            if "Stilproben" in (style_resolved or ""):
                system_instruction += (
                    "\n\nACHTUNG: Die in den Vorgaben enthaltenen Stilproben zeigen deinen bisherigen Schreibstil für dieses Buch. "
                    "Halte dich eng an diesen Ton, Rhythmus und diese Wortwahl."
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
                scene_prose = re.sub(r'^(?:---\s*)?szene\s*\d+\s*(?:[:\-\.]|---)?\s*', '', scene_prose, flags=re.IGNORECASE).strip()
                
                if chapter_prose:
                    chapter_prose += "\n\n" + scene_prose
                else:
                    chapter_prose = scene_prose
            except Exception as e:
                logger.error(f"Error generating scene {scene['scene_number']} in chapter {chapter.chapter_number}: {e}")
                raise e
                
        return chapter_prose
        
    else:
        # Fallback to single-run chapter generation if no structured scenes are found
        writing_instruction = f"""
    Kapitel-Plot (Was passieren soll): {chapter.plot_outline}
    """
    
        system_instruction = (
            f"Du bist ein preisgekrönter Romanautor. Dein Schreibstil folgt diesen Vorgaben:\n{style_resolved}\n\n"
            f"{genre_section}\n\n"
            "Schreibe ausschließlich die Romanprosa für das angeforderte Kapitel. Schreib flüssig, "
            "atmosphärisch und detailreich. Benutze KEINE Überschriften, Kapitelnummern (wie 'Kapitel 1'), "
            "Meta-Kommentare oder den Kapiteltitel am Anfang des Textes. Beginne sofort mit dem ersten Satz der Geschichte. "
            "Benutze unter keinen Umständen Markdown-Sternchen (*) oder Unterstriche (_), um Gedanken, Durchsagen oder wörtliche Rede hervorzuheben. "
            "Nutze für wörtliche Rede und Durchsagen stattdessen klassische deutsche Anführungszeichen (z. B. „...“ oder »...«)."
        )
        if "Stilproben" in (style_resolved or ""):
            system_instruction += (
                "\n\nACHTUNG: Die in den Vorgaben enthaltenen Stilproben zeigen deinen bisherigen Schreibstil für dieses Buch. "
                "Halte dich eng an diesen Ton, Rhythmus und diese Wortwahl, um Konsistenz zu gewährleisten."
            )
            
        estimated_tokens = int(target_words * 1.4)
        dynamic_max_tokens = max(8192, min(estimated_tokens + 2048, 16384))
        
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
            
            # Re-build prompt with truncated outline
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
    model: str = "gemini-3.1-flash-lite",
    target_words_per_chapter: int = 2500,
    genre_config: Optional[dict] = None,
    use_scene_beats: bool = True
) -> Dict[str, Any]:
    """Expands a single chapter outline into structured scene beats or a detailed 3-4 paragraph blueprint."""
    style_resolved = get_author_names_improved(style)
    
    if not use_scene_beats:
        # Old behavior: paragraph blueprint
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
        pov_hint = (
            f"\nWICHTIG: Dieses Kapitel ({chapter_number}) wird aus der Perspektive des "
            f"{'weiblichen' if chapter_number % 2 == 1 else 'männlichen'} Hauptcharakters erzählt. "
            f"Alle Szenen MÜSSEN aus dieser Perspektive geplant sein."
        )
    elif genre_config and genre_config.get("pov") == "single_female":
        pov_hint = "\nWICHTIG: Alle Szenen MÜSSEN aus der Perspektive des weiblichen Hauptcharakters erzählt sein."
    elif genre_config and genre_config.get("pov") == "single_male":
        pov_hint = "\nWICHTIG: Alle Szenen MÜSSEN aus der Perspektive des männlichen Hauptcharakters erzählt sein."
        
    recommended_scenes = max(3, min(7, target_words_per_chapter // 500))
    
    system_instruction = (
        "Du bist ein Bestseller-Autor und Story-Architekt. Deine Aufgabe ist es, eine kurze "
        "Kapitelgliederung zu einer detaillierten Szenen-Struktur auszuarbeiten. "
        "Jede Szene bekommt einen klaren dramaturgischen Aufbau mit Ziel, Konflikt und Ausgang. "
        "Antworte ausschließlich im JSON-Format."
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
        formatted_outline = format_scene_beats_as_text(beats)
        
        # Prepend chapter summary if present
        chap_sum = data.get("chapter_summary")
        if chap_sum:
            formatted_outline = f"Zusammenfassung: {chap_sum.strip()}\n\n{formatted_outline}"
        
        # Determine main POV character for the chapter
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
    model: str = "gemini-3.5-flash"
) -> str:
    """
    Overwrites or adjusts the plot outlines in the book outline based on global proofreading findings.
    Returns the updated outline JSON string conforming to BookOutlineSchema.
    """
    system_instruction = (
        "Du bist ein leitender Bestseller-Lektor. "
        "Deine Aufgabe ist es, eine bestehende Buch-Gliederung (Outline) so zu überarbeiten, "
        "dass die gefundenen Fehler (Findings) korrigiert werden. "
        "Antworte ausschließlich im JSON-Format gemäß des vorgegebenen Schemas."
    )
    
    # Format the findings into a readable string
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
    model: str = "gemini-3.5-flash"
) -> List[Dict[str, Any]]:
    """
    Analyzes the plot outlines (blueprints) of all chapters for logical consistency,
    character contradictions, and pacing issues.
    """
    system_instruction = (
        "Du bist ein leitender Bestseller-Lektor. "
        "Analysiere die Gliederung (Kapitel-Entwürfe/Blueprints) des Buches auf inhaltliche Widersprüche, "
        "Logikfehler, Charakter-Inkonsistenz und Pacing-Probleme zwischen den Kapiteln. "
        "Antworte ausschließlich im JSON-Format."
    )
    
    # Concatenate all outlines with clear headers
    outline_parts = []
    for c in chapters:
        outline_parts.append(
            f"=== Kapitel {c.chapter_number}: {c.title} ===\n"
            f"Gliederung/Blueprint: {c.plot_outline or '[Keine Vorgabe]'}"
        )
    outline_text = "\n\n".join(outline_parts)
    
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





