"""
Story generation service using Google Gemini Flash.
Two-step process: 1) Generate outline  2) Write detailed chapters
"""

from google import genai
from app.config import settings
import asyncio
import json
import re

client = genai.Client(api_key=settings.GEMINI_API_KEY)


MODEL = "gemini-3-flash-preview"

STANZWERK_BIBLIOTHEK = {
    "adults": [
        {"id": "kehlmann", "name": "Daniel Kehlmann", "wortwahl": "Präzise, intellektuell, elegant", "atmosphaere": "Magischer Realismus, geistreich, historisch distanziert", "erzaehlweise": "Auktorial, verspielt, ironisch"},
        {"id": "zeh", "name": "Juli Zeh", "wortwahl": "Analytisch, präzise, juristisch kühl", "atmosphaere": "Gesellschaftskritisch, angespannt, realitätsnah", "erzaehlweise": "Multiperspektivisch, sezierend, kühl"},
        {"id": "fitzek", "name": "Sebastian Fitzek", "wortwahl": "Atemlos, plakativ, treibend", "atmosphaere": "Düster, klaustrophobisch, spannungsgetrieben", "erzaehlweise": "Rasant, ständige Cliffhanger, unzuverlässig"},
        {"id": "sueskind", "name": "Patrick Süskind", "wortwahl": "Sinnlich, olfaktorisch detailliert, historisch exakt", "atmosphaere": "Obsessiv, detailverliebt, grotesk-schön", "erzaehlweise": "Auktorial, intensiv, fast schon wissenschaftlich-beschreibend"},
        {"id": "kracht", "name": "Christian Kracht", "wortwahl": "Snobistisch, affektiert, kühl", "atmosphaere": "Dekadent, entfremdet, neusachlich", "erzaehlweise": "Distanziert, dandyhaft, emotionslos berichtend"},
        {"id": "bachmann", "name": "Ingeborg Bachmann", "wortwahl": "Metaphorisch, lyrisch, intensiv", "atmosphaere": "Melancholisch, existenziell bedroht, tiefgründig", "erzaehlweise": "Bewusstseinsnah, poetisch verdichtet"},
        {"id": "kafka", "name": "Franz Kafka", "wortwahl": "Trocken, bürokratisch, glasklar", "atmosphaere": "Surreal, beklemmend, ausweglos", "erzaehlweise": "Sachlicher Bericht albtraumhafter Zustände"},
        {"id": "borchert", "name": "Wolfgang Borchert", "wortwahl": "Hart, stakkatoartig, unverblümt", "atmosphaere": "Kalt, karg, nachkriegs-existenziell", "erzaehlweise": "Reduziert, expressionistisch, drängend"},
        {"id": "jaud", "name": "Tommy Jaud", "wortwahl": "Alltagssprachlich, pointiert, humoristisch", "atmosphaere": "Hektisch, alltäglich, wunderbar peinlich", "erzaehlweise": "Aneinanderreihung von Fettnäpfchen, zynisch-komisch"}
    ],
    "kids": [
        {"id": "funke", "name": "Cornelia Funke", "wortwahl": "Magisch, farbenfroh, bildstark", "atmosphaere": "Wundervoll, abenteuerlich, märchenhaft", "erzaehlweise": "Mitreißend, immersiv, warmherzig"},
        {"id": "pantermueller", "name": "Alice Pantermüller", "wortwahl": "Rotzig, kindgerecht, umgangssprachlich", "atmosphaere": "Chaotisch, alltäglich, lustig", "erzaehlweise": "Frech, tagebuchartig, im Plauderton"},
        {"id": "auer", "name": "Margit Auer", "wortwahl": "Empathisch, warm, verständlich", "atmosphaere": "Geborgen, geheimnisvoll, magisch-alltäglich", "erzaehlweise": "Pädagogisch wertvoll, spannungsvoll, auf Augenhöhe der Kinder"}
    ]
}

def generate_modular_prompt(style_string: str) -> str:
    selected_ids = [s.strip() for s in style_string.split(",")] if style_string else []
    all_authors = {a['id']: a for category in STANZWERK_BIBLIOTHEK.values() for a in category}
    valid_authors = [all_authors[aid] for aid in selected_ids if aid in all_authors]
    
    if not valid_authors:
        return "Stil: Neutraler, klarer Autorentyp."
        
    rules = [
        "Basis-Stil (60%): Ein neutraler, professioneller, klarer und zugänglicher Schreibstil."
    ]
    
    if len(valid_authors) == 1:
        author = valid_authors[0]
        rules.append(f"Zusätzlicher Einfluss (40%) von {author['name']}:")
        rules.append(f"- Wortwahl: {author['wortwahl']}")
        rules.append(f"- Atmosphäre: {author['atmosphaere']}")
        rules.append(f"- Erzählweise: {author['erzaehlweise']}")
    elif len(valid_authors) == 2:
        a1, a2 = valid_authors
        rules.append("Zusätzlicher Einfluss (40%), aufgeteilt auf zwei Autoren:")
        rules.append(f"- Wortwahl ({a1['name']}): {a1['wortwahl']}")
        rules.append(f"- Atmosphäre ({a2['name']}): {a2['atmosphaere']}")
        rules.append(f"- Erzählweise (gemischt): Eine Synthese beider Ansätze ({a1['erzaehlweise']} UND {a2['erzaehlweise']})")
    else:
        a1, a2, a3 = valid_authors[:3]
        rules.append("Zusätzlicher Einfluss (40%), strikt aufgeteilt auf drei Autoren:")
        rules.append(f"- Wortwahl ({a1['name']}): {a1['wortwahl']}")
        rules.append(f"- Atmosphäre ({a2['name']}): {a2['atmosphaere']}")
        rules.append(f"- Erzählweise ({a3['name']}): {a3['erzaehlweise']}")
        
    return "\n".join(rules)

GENRES_BIBLIOTHEK = {
    "Krimi": {"name": "Krimi", "ziel": "Lösung eines Rätsels", "tropen": "Indizien, Verdächtige, falsche Fährten"},
    "Abenteuer": {"name": "Abenteuer", "ziel": "Eine Reise bewältigen", "tropen": "Aufbruch, Hindernisse, Heldenreise"},
    "Science-Fiction": {"name": "Science-Fiction", "ziel": "Was-wäre-wenn-Szenario", "tropen": "Zukunfts-Technik, fremde Welten"},
    "Märchen": {"name": "Märchen", "ziel": "Ordnung wiederherstellen", "tropen": "Magische Wesen, Wandlung, Alltagsmagie"},
    "Komödie": {"name": "Komödie", "ziel": "Absurdität entlarven", "tropen": "Situationskomik, Verwechslungen"},
    "Thriller": {"name": "Thriller", "ziel": "Überleben / Bedrohung abwenden", "tropen": "Countdown, hohe Spannung, verborgene Gefahr"},
    "Drama": {"name": "Drama", "ziel": "Innere Konflikte klären", "tropen": "Tiefe Dialoge, Fokus auf Freundschaft"},
    "Grusel": {"name": "Grusel", "ziel": "Das Unheimliche erfahren", "tropen": "Schatten, alte Geheimnisse, Gänsehaut"}
}

async def generate_story_hook(genre: str, author_id: str) -> str:
    """Generate a single max 15-word story hook based on a given genre and author ID."""
    
    # Try to find the genre and author objects
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Abenteuer"])
    author = None
    all_authors = {a['id']: a for category in STANZWERK_BIBLIOTHEK.values() for a in category}
    if author_id in all_authors:
        author = all_authors[author_id]
        
    author_desc = f"{author['name']} ({author['wortwahl']} / {author['atmosphaere']})" if author else "Ein klarer, sachlicher Literat."
        
    stanzwerk_hooks = [
        {"typ": "Der Kontrast-Hook", "logik": "Kombiniere ein banales Objekt mit einer unmöglichen biologischen Eigenschaft."},
        {"typ": "Der Metaphysische Riss", "logik": "Beschreibe eine tägliche Routine, die durch eine surreale Zeitverschiebung gestört wird."},
        {"typ": "Die Olfaktorische Falle", "logik": "Beginne mit einem Geruch, der an diesem Ort absolut unmöglich ist."},
        {"typ": "Das Logik-Loch", "logik": "Stelle eine knochentrockene Behauptung auf, die ein physikalisches Gesetz ignoriert."},
        {"typ": "Die haptische Miniatur", "logik": "Beschreibe ein Werkzeug oder Objekt so detailreich, dass man es spüren kann."},
        {"typ": "Der Snob-Snapshot", "logik": "Betrachte eine luxuriöse Oberfläche mit extremer, gelangweilter Distanz."},
        {"typ": "Der Psycho-Countdown", "logik": "Ein gewöhnliches Geräusch wird plötzlich zur unmittelbaren, tödlichen Bedrohung."},
        {"typ": "Das Alltags-Geheimnis", "logik": "Ein Tier oder Objekt schließt einen geheimen Bund mit dem Protagonisten."},
        {"typ": "Die Trümmer-Ehrlichkeit", "logik": "Ein extrem kurzer, harter Satz über Kälte, Hunger oder das nackte Überleben."},
        {"typ": "Der Turbo-Slapstick", "logik": "Ein peinliches Missgeschick eskaliert innerhalb von Sekunden zur totalen Katastrophe."}
    ]
    
    import random
    selected_hook = random.choice(stanzwerk_hooks)
        
    prompt = f"""WICHTIGE REGEL: Antworte mit exakt 1 Satz! Maximal 15 Wörter! Kein Wort mehr!

Du bist ein erfolgreicher Kinder- und Jugendbuchautor. Generiere einen Story-Hook, der eine alltägliche Situation aus den Angeln hebt. Vermeide platte Witze. Setze dort an, wo die Logik des Alltags einen Riss bekommt. Nutze keine Standard-Adjektive... Der Hook muss eine Frage hinterlassen.

Werkzeug:
Struktur-Schablone: [{selected_hook['typ']}]: {selected_hook['logik']}
"""
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL,
            contents=prompt,
            config={
                "temperature": 0.9,
                "max_output_tokens": 1000,
                "top_k": 20,
            }
        )
        return response.text.strip().strip('"').strip("'")
    except Exception as e:
        import logging
        logging.error(f"Failed to generate hook: {e}")
        return "Ein Toaster erwacht und fragt nach dem Sinn des Brotes."

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
    selected_style_info = generate_modular_prompt(style)
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Abenteuer"])
    # 130 words per minute is a standard, relaxed reading pace for audiobooks
    word_count = target_minutes * 130
    char_text = f"\nHauptcharaktere: {', '.join(characters)}" if characters else ""
    user_hook = prompt

    master_prompt = f"""Du bist ein preisgekrönter Autor. Schreibe eine abgeschlossene Kurzgeschichte.

STRIKTE REGELN:
1. Literarischer Anspruch: Lass Dich von den Stil-Vorgaben inspirieren:
{selected_style_info}
Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Die Geschichte endet mit dem letzten narrativen Moment. Kein Kitsch, keine Moral!
2. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
3. Pacing & Detail: Hetze nicht durch die Handlung. Entwickle Szenen langsam. Beschreibe Texturen, Gerüche und die Umgebung so präzise, dass ein Kopfkino entsteht (No Rush!).
4. Format: Schreibe die Geschichte als einen fließenden Text. Nutze lediglich szenische Absätze oder subtile Zeitensprünge, keine nummerierten Kapitel.
5. Umfang: Fasse dich extrem präzise und meide überladene Füllwörter. Maximiere die sprachliche Dichte. Ziel: Vorlesedauer {target_minutes} Min (EXAKT ~{word_count} Wörter, KEINESFALLS mehr!). Blähe den Text nicht künstlich auf.

Rahmenbedingungen:
Schreibe eine Geschichte im Genre {genre_data['name']}. Der Kern der Handlung (Nutzer-Wunsch) ist: {user_hook}{char_text}. Folge dem Narrativ: {genre_data['ziel']} unter Verwendung von {genre_data['tropen']}.

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
    selected_style_info = generate_modular_prompt(style)
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Abenteuer"])
    user_hook = prompt
    char_text = f"\nHauptcharaktere: {', '.join(characters)}" if characters else ""
    
    # Target total words. 130 WPM is a better average for comfortable bedtime reading pacing.
    total_words = target_minutes * 130
    
    # Enforce strictly 5-minute chapters (650 words each).
    # 10 min = 2 chapters, 15 min = 3 chapters, 20 min = 4 chapters
    num_segments = max(2, target_minutes // 5)
    words_per_segment = total_words // num_segments

    if on_progress:
        await on_progress("generating_text", f"Plane Geschichte ({target_minutes} Min, {num_segments} Kapitel)...", 2)

    # Step 1: Generate Outline
    outline_prompt = f"""Erstelle eine detaillierte Gliederung für eine {target_minutes}-minütige Kurzgeschichte.
Schreibe eine Geschichte im Genre {genre_data['name']}. Der Kern der Handlung (Nutzer-Wunsch) ist: {user_hook}{char_text}. Folge dem Narrativ: {genre_data['ziel']} unter Verwendung von {genre_data['tropen']}.

Stil-Vorgaben:
{selected_style_info}

Teile die Geschichte in exakt {num_segments} logische Abschnitte (Akte) auf.
Jeder Abschnitt entspricht chronologisch einem Kapitel der Geschichte.
ACHTUNG ZUR LÄNGE: Die gesamte Geschichte soll {total_words} Wörter lang werden. Jeder Abschnitt muss Material für maximal {words_per_segment} Wörter Text bieten. Keine überflüssigen Ausschweifungen!
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
        
                
        outline_data = json.loads(text)
        title = outline_data.get("title", "Eine neue Geschichte")
        synopsis = outline_data.get("synopsis", "Kurzgeschichte")
        segments = outline_data.get("segments", [])
    except Exception as e:
        import logging
        logging.error(f"Multi-pass outline failure: {e}")
        try:
            logging.error(f"Raw Outline LLM Output was: {outline_res.text}")
        except:
            pass
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
        
        is_last_chapter = (i == num_segments - 1)
        
        if is_last_chapter:
            ende_regel = f"5. UMFANG & ENDE: Schreibe ca. {words_per_segment} Wörter. DIES IST DAS FINALE KAPITEL! Führe die Geschichte zwingend zu einem runden, atmosphärischen Abschluss. Schließe die Handlung ab. Kein Cliffhanger mehr! Beende die Geschichte mit einem starken letzten Satz, niemals mit einem Cut."
        else:
            ende_regel = f"5. UMFANG & ENDE: Schreibe ca. {words_per_segment} Wörter. WICHTIG: Beende das Kapitel NIEMALS mitten in einem Satz (kein Hard Cut). Führe die Szene logisch zu Ende oder erzeuge einen weichen Übergang/Cliffhanger für das nächste Kapitel."
        
        write_prompt = f"""Schreibe das nächste chronologische Kapitel der Geschichte.

STRIKTE REGELN:
1. Literarischer Anspruch: Lass Dich von den Stil-Vorgaben inspirieren:
{selected_style_info}
Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Kein Kitsch, keine Moral!
2. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
3. Pacing & Detail: Beschreibe präzise und atmosphärisch, aber meide unnötige Füllwörter. Konzentriere die Geschichte.
4. Format: Keine Kapitelüberschriften im generierten Text! Nur der fließende Erzähltext für dieses Kapitel.
{ende_regel}

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
