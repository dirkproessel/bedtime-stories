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
    on_progress: callable = None, # on_progress(status_type, message, pct)
) -> dict:
    # Due to LLM word length limits (~1000 words max per request), 
    # we always use the multi-pass (chapter-by-chapter) generation.
    return await _generate_multi_pass(prompt, genre, style, characters, target_minutes, on_progress)


async def _generate_single_pass(prompt, genre, style, characters, target_minutes, on_progress):
    """Original single-pass logic for shorter stories with improved JSON cleanup."""
    selected_style_info = STYLE_MAPPING.get(style, STYLE_MAPPING["Douglas Adams"])
    selected_genre_info = GENRE_MAPPING.get(genre, GENRE_MAPPING["Realismus"])
    word_count = target_minutes * 200
    char_text = f"\nHauptcharaktere: {', '.join(characters)}" if characters else ""

    master_prompt = f"""Du bist ein preisgekrönter Autor. Schreibe eine abgeschlossene Kurzgeschichte.

STRIKTE REGELN:
1. Literarischer Anspruch: Halte dich strikt an den gewählten Autoren-Stil. Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Die Geschichte endet mit dem letzten narrativen Moment. Kein Kitsch, keine Moral!
2. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
3. Pacing & Detail: Hetze nicht durch die Handlung. Entwickle Szenen langsam. Beschreibe Texturen, Gerüche und die Umgebung so präzise, dass ein Kopfkino entsteht (No Rush!).
4. Format: Schreibe die Geschichte als einen fließenden Text. Nutze lediglich szenische Absätze oder subtile Zeitensprünge, keine nummerierten Kapitel.
5. Umfang: Nutze das volle Output-Limit für maximale Detailtiefe. Ziel: Vorlesedauer {target_minutes} Min (~{word_count} Wörter).

Parameter:
Genre: {selected_genre_info}
Stil: {selected_style_info}
Inhalt/Zusatzwunsch: {prompt}{char_text}

Antworte EXKLUSIV im JSON-Format:
{{
    "title": "Titel",
    "synopsis": "Zusammenfassung",
    "full_text": "Text der Geschichte..."
}}"""

    if on_progress:
        await on_progress("generating_text", f"Schreibe '{style}'-Geschichte ({target_minutes} Min)...", 5)

    import asyncio
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL,
        contents=master_prompt,
        config={"response_mime_type": "application/json", "temperature": 0.85, "max_output_tokens": 8192}
    )

    import json
    import re
    
    text = response.text.strip()
    
    # Robust JSON extraction: Find the first { and the last }
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)
    else:
        # Fallback to basic markdown cleanup if regex fails
        if text.startswith("```json"):
            text = text.replace("```json", "", 1).replace("```", "", 1).strip()
        elif text.startswith("```"):
            text = text.replace("```", "", 2).strip()

    try:
        data = json.loads(text)
        # Handle cases where full_text itself contains JSON (recursive LLM error)
        story_content = data.get("full_text", "")
        if isinstance(story_content, dict):
            story_content = story_content.get("full_text", str(story_content))
            
        return {
            "title": data.get("title", "Eine neue Geschichte"),
            "synopsis": data.get("synopsis", "Kurzgeschichte"),
            "chapters": [{"title": "Geschichte", "text": story_content}]
        }
    except Exception as e:
        import logging
        logging.error(f"Failed to parse story JSON: {e}. Raw: {text[:200]}")
        return {
            "title": "Anomalie im Labor", 
            "synopsis": "Die Geschichte konnte nicht korrekt formatiert werden.", 
            "chapters": [{"title": "Text", "text": text}]
        }


async def _generate_multi_pass(prompt, genre, style, characters, target_minutes, on_progress):
    """Two-step generation for long stories to ensure length and flow."""
    selected_style_info = STYLE_MAPPING.get(style, STYLE_MAPPING["Douglas Adams"])
    selected_genre_info = GENRE_MAPPING.get(genre, GENRE_MAPPING["Realismus"])
    
    # Target total words
    total_words = target_minutes * 200
    
    # Strictly enforce 5-minute chapters (1000 words each) based on the user selection.
    # 10 min = 2 chapters, 15 min = 3 chapters, 20 min = 4 chapters
    num_segments = max(2, target_minutes // 5)
    words_per_segment = total_words // num_segments

    if on_progress:
        await on_progress("generating_text", f"Plane '{style}'-Geschichte ({target_minutes} Min, {num_segments} Kapitel)...", 2)

    # Step 1: Generate Outline
    outline_prompt = f"""Erstelle eine detaillierte Gliederung für eine {target_minutes}-minütige Kurzgeschichte.
Genre: {selected_genre_info}
Stil: {selected_style_info}
Inhalt: {prompt}

Teile die Geschichte in {num_segments} logische Abschnitte (Akte) auf. Jeder Abschnitt muss etwa {words_per_segment} Wörter Text generieren.
Antworte NUR im JSON-Format:
{{
    "title": "Titel",
    "synopsis": "Detaillierte Zusammenfassung",
    "segments": [
        {{ "title": "Abschnitt 1", "goal": "Was in diesem Teil passiert..." }},
        ...
    ]
}}"""

    try:
        outline_res = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=outline_prompt,
            config={"response_mime_type": "application/json"}
        )
        
        text = outline_res.text.strip()
        
        # Robust JSON extraction for outline
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        else:
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).replace("```", "", 1).strip()
            elif text.startswith("```"):
                text = text.replace("```", "", 2).strip()
                
        outline_data = json.loads(text)
        title = outline_data.get("title", "Eine neue Geschichte")
        synopsis = outline_data.get("synopsis", "Kurzgeschichte")
        segments = outline_data.get("segments", [])
    except Exception as e:
        import logging
        logging.error(f"Multi-pass outline failure: {e}")
        # Graceful fallback to single-pass if outline fails
        return await _generate_single_pass(prompt, genre, style, characters, target_minutes, on_progress)
    
    if not segments:
        return await _generate_single_pass(prompt, genre, style, characters, target_minutes, on_progress)
    
    full_chapters = []
    
    # Step 2: Iterative Writing
    for i, seg in enumerate(segments):
        if on_progress:
            pct = 5 + int((i / num_segments) * 25) # Up to 30%
            await on_progress("generating_text", f"Schreibe Kapitel {i+1}/{num_segments}: {seg['title']}...", pct)
            
        # Context is just the end of the previous chapter to maintain continuity
        context = f"Ende des vorherigen Kapitels: {full_chapters[-1]['text'][-1000:]}" if full_chapters else "Dies ist der Beginn der Geschichte."
        
        write_prompt = f"""Schreibe das nächste chronologische Kapitel der Geschichte im Stil von {style}.

STRIKTE REGELN:
1. Literarischer Anspruch: Halte dich strikt an den Autoren-Stil ({style}). Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Kein Kitsch, keine Moral!
2. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
3. Pacing & Detail: Dehne die Szenen aus (Slow Pacing). Beschreibe Texturen, Licht, Gerüche und Dialoge so ausführlich, dass Kopfkino entsteht. Schreibe langsam und bedächtig (No Rush!).
4. Format: Keine Kapitelüberschriften im generierten Text! Nur der fließende Erzähltext für dieses Kapitel.
5. Umfang: Du MUSST ca. {words_per_segment} Wörter (ca. 5 Minuten Vorlesezeit) für dieses Kapitel schreiben. Nutze harte Dialoge und ausführliche Beschreibungen, um die Länge zu füllen.

Rahmenbedingungen:
Titel der Gesamtgeschichte: {title}
Zusammenfassung der Geschichte: {synopsis}
Fokus / Ziel DIESES Kapitels: {seg['goal']}
{context}
"""
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=write_prompt,
            config={"temperature": 0.8}
        )
        segment_text = response.text.strip()
        
        full_chapters.append({
            "title": seg['title'],
            "text": segment_text
        })

    return {
        "title": title,
        "synopsis": synopsis,
        "chapters": full_chapters
    }
