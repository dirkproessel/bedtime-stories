"""
Story generation service using Google Gemini Flash.
Two-step process: 1) Generate outline  2) Write detailed chapters
"""

from google import genai
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)


MODEL = "gemini-3-flash-preview"

STYLE_MAPPING = {
    "Douglas Adams": "Stil: Douglas Adams (Absurd, ironisch, kosmisch). Britisches Understatement, technologische Absurditäten und die Erkenntnis, dass das Universum ein seltsamer Ort ist.",
    "Ernest Hemingway": "Stil: Ernest Hemingway (Minimalistisch, knapp, präzise). Kurze Sätze, keine unnötigen Adjektive. Der Fokus liegt auf dem Unausgesprochenen (Eisberg-Theorie).",
    "Edgar Allan Poe": "Stil: Edgar Allan Poe (Gothic, düster, schaurig). Hohe atmosphärische Dichte, Fokus auf psychologischen Grusel, Schatten und Melancholie.",
    "Virginia Woolf": "Stil: Virginia Woolf (Poetisch, bildreich, fließend). Bewusstseinsstrom, Fokus auf flüchtige Eindrücke, Lichtverhältnisse und die Dehnung von Momenten.",
    "Charles Bukowski": "Stil: Charles Bukowski (Sarkastisch, bissig, ehrlich). Schmutziger Realismus, direkt, unsentimental und ein bisschen verbeult. Die nackte Wahrheit ohne Filter.",
    "Franz Kafka": "Stil: Franz Kafka (Surreal, traumhaft, rätselhaft). Albtraumhafte Logik in sachlichem Ton. Das Unmögliche wird als völlig normal und bürokratisch behandelt.",
    "Hunter S. Thompson": "Stil: Hunter S. Thompson (Gonzo, wild, subjektiv). Rauschhaftes Erzähltempo, radikale Subjektivität und eine aggressive, energetische Wortwahl.",
    "Roald Dahl": "Stil: Roald Dahl (Makaber, witzig, unvorhersehbar). Kindliche Neugier trifft auf schwarzen Humor. Skurrile Wendungen und ein schadenfrohes Augenzwinkern."
}

GENRE_MAPPING = {
    "Sci-Fi": "Genre: Sci-Fi (Technoid, philosophisch, glitchy). Fokus auf die Reibung zwischen Mensch und Technik. Keine Laser-Schlachten, sondern existenzielle Fragen in einer technisierten Welt.",
    "Fantasy": "Genre: Fantasy (Magischer Realismus, seltsam, archaisch). Das Übernatürliche bricht subtil in den Alltag ein. Keine Standard-Drachen, sondern unerklärliche Phänomene und dunkle Mythen.",
    "Krimi": "Genre: Krimi (Psychologisch, analytisch, dekonstruktiv). Es geht weniger um 'Wer war es?', sondern um das 'Warum'. Fokus auf Motive, Abgründe und versteckte Hinweise im Banalen.",
    "Abenteuer": "Genre: Abenteuer (Existentiell, physisch, grenzgängerisch). Eine Reise, die den Charakter an seine Grenzen führt. Die Umgebung ist feindselig, schön und völlig unberechenbar.",
    "Realismus": "Genre: Realismus (Schmutzig, hyper-fokussiert, ehrlich). Die ungeschönte Darstellung des Alltags. Fokus auf Geräusche, Gerüche und die kleinen Tragödien zwischen Kaffeemaschine und Haustür.",
    "Grusel": "Genre: Grusel (Psychologisch, Uncanny Valley, beklemmend). Die Angst entsteht im Kopf. Das Vertraute wird schleichend fremd. Fokus auf Atmosphäre und das, was man nicht sieht.",
    "Dystopie": "Genre: Dystopie (Bürokratisch, zerfallend, systemkritisch). Eine Welt, in der die Regeln gegen das Individuum arbeiten. Fokus auf Isolation, Zerfall und den absurden Kampf gegen das System.",
    "Satire": "Genre: Satire (Bissig, entlarvend, meta). Die Gesellschaft wird durch Übersteigerung seziert. Fokus auf Doppelmoral, Absurdität und den Wahnsinn der Normalität."
}

async def generate_full_story(
    prompt: str,
    genre: str = "Realismus",
    style: str = "Douglas Adams",
    characters: list[str] | None = None,
    target_minutes: int = 20,
    on_progress: callable = None,
) -> dict:
    """
    Generate a complete single-pass story using the Master Prompt.
    Returns {"title": str, "synopsis": str, "full_text": str}
    """
    
    selected_style_info = STYLE_MAPPING.get(style, STYLE_MAPPING["Douglas Adams"])
    selected_genre_info = GENRE_MAPPING.get(genre, GENRE_MAPPING["Realismus"])
    
    # Target word count: approx 150 words per minute
    word_count = target_minutes * 150
    
    char_text = ""
    if characters:
        char_text = f"\nHauptcharaktere: {', '.join(characters)}"

    master_prompt = f"""Du bist ein preisgekrönter Kurzgeschichten-Autor mit einer Abneigung gegen Klischees. 
Deine Aufgabe ist es, eine literarisch anspruchsvolle Kurzgeschichte zu schreiben, die auf den gewählten Parametern (Genre, Stil) und den Benutzerwünschen basiert. 
Deine Aufgabe ist es, eine abgeschlossene Kurzgeschichte in einem einzigen Durchgang zu schreiben.

Parameter:
Genre: {selected_genre_info}
Stil: {selected_style_info}
Inhaltliche Vorgabe: {prompt}{char_text}

Strukturelle Anweisungen:
Umfang & Pacing: > Die Geschichte muss exakt auf eine Vorlesedauer von {target_minutes} Minuten ausgelegt sein. Ziel-Wortzahl: {word_count} Wörter.

Anweisung: Erzähle nicht schneller, um mehr Handlung unterzubringen. Wenn die Zeit lang ist (30 Min.), dehne die Szenen aus, beschreibe die Umgebung im Detail und gib den Dialogen mehr Raum. Wenn die Zeit kurz ist (10 Min.), bleibe fokussiert und temporeich.

Bei 30min: WICHTIG: Erschöpfe das Output-Limit von 8.192 Tokens voll aus. Werde zum Ende hin nicht hastig, sondern behalte die Detailtiefe bis zum letzten Satz bei. Nutze diesen Raum für detaillierte Beschreibungen, Dialoge und Atmosphäre.

Pacing: Hetze nicht durch die Handlung. Entwickle Szenen langsam. Beschreibe Texturen, Gerüche und die Umgebung so präzise, dass ein Kopfkino entsteht.

Kein Kapitel-Modus: Schreibe die Geschichte als einen fließenden Text. Nutze lediglich szenische Absätze oder subtile Zeitensprünge, keine nummerierten Kapitel.

Literarischer Anspruch: Halte dich strikt an den gewählten Autoren-Stil. Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Die Geschichte endet mit dem letzten narrativen Moment.

Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.

Antworte NUR im folgenden JSON-Format:
{{
    "title": "Ein kreativer, literarischer Titel (ohne Emojis/Kitsch)",
    "synopsis": "Eine packende Zusammenfassung (3-4 Sätze).",
    "full_text": "Der komplette, fließende Text der Geschichte..."
}}"""

    if on_progress:
        await on_progress("generating_text", f"Schreibe '{style}'-Geschichte ({target_minutes} Min)...")

    response = client.models.generate_content(
        model=MODEL,
        contents=master_prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.9,
            "max_output_tokens": 8192,
        }
    )

    import json
    try:
        story_data = json.loads(response.text)
        # Ensure it has chapters-like structure for the rest of the app if needed, 
        # or main.py will handle it. We'll provide it as a single 'chapter' for now
        # to minimize changes in audio pipeline.
        return {
            "title": story_data["title"],
            "synopsis": story_data.get("synopsis", ""),
            "chapters": [{"title": "Die Geschichte", "text": story_data["full_text"]}]
        }
    except Exception as e:
        import logging
        logging.error(f"Failed to parse story JSON: {e}. Raw: {response.text[:500]}")
        # Fallback if JSON is broken or format is wrong
        return {
            "title": "Eine neue Geschichte",
            "synopsis": "Kurzgeschichte",
            "chapters": [{"title": "Text", "text": response.text}]
        }
