"""
Story generation service using Google Gemini Flash.
Two-step process: 1) Generate outline  2) Write detailed chapters
"""

from google import genai
from app.config import settings
import asyncio
import json
import re
from app.services.rate_limiter import rate_limiter

client = genai.Client(api_key=settings.GEMINI_API_KEY)


# Centralized models now coming from app.config.settings

STANZWERK_BIBLIOTHEK = {
    "adults": [
        {"id": "kehlmann", "name": "Daniel Kehlmann", "wortwahl": "Präzise, intellektuell, elegant", "atmosphaere": "Magischer Realismus, geistreich, historisch distanziert", "erzaehlweise": "Auktorial, verspielt, ironisch"},
        {"id": "zeh", "name": "Juli Zeh", "wortwahl": "Analytisch, präzise, juristisch kühl", "atmosphaere": "Gesellschaftskritisch, angespannt, realitätsnah", "erzaehlweise": "Multiperspektivisch, sezierend, kühl"},
        {"id": "fitzek", "name": "Sebastian Fitzek", "wortwahl": "Atemlos, plakativ, treibend", "atmosphaere": "Düster, klaustrophobisch, spannungsgetrieben", "erzaehlweise": "Rasant, ständige Cliffhanger, unzuverlässig"},
        # {"id": "sueskind", "name": "Patrick Süskind", "wortwahl": "Sinnlich, olfaktorisch detailliert, historisch exakt", "atmosphaere": "Obsessiv, detailverliebt, grotesk-schön", "erzaehlweise": "Auktorial, intensiv, fast schon wissenschaftlich-beschreibend"},
        {"id": "kracht", "name": "Christian Kracht", "wortwahl": "Snobistisch, affektiert, kühl", "atmosphaere": "Dekadent, entfremdet, neusachlich", "erzaehlweise": "Distanziert, dandyhaft, emotionslos berichtend"},
        # {"id": "bachmann", "name": "Ingeborg Bachmann", "wortwahl": "Metaphorisch, lyrisch, intensiv", "atmosphaere": "Melancholisch, existenziell bedroht, tiefgründig", "erzaehlweise": "Bewusstseinsnah, poetisch verdichtet"},
        {"id": "kafka", "name": "Franz Kafka", "wortwahl": "Trocken, bürokratisch, glasklar", "atmosphaere": "Surreal, beklemmend, ausweglos", "erzaehlweise": "Sachlicher Bericht albtraumhafter Zustände"},
        # {"id": "borchert", "name": "Wolfgang Borchert", "wortwahl": "Hart, stakkatoartig, unverblümt", "atmosphaere": "Kalt, karg, nachkriegs-existenziell", "erzaehlweise": "Reduziert, expressionistisch, drängend"},
        {"id": "jaud", "name": "Tommy Jaud", "wortwahl": "Alltagssprachlich, pointiert, humoristisch", "atmosphaere": "Hektisch, alltäglich, wunderbar peinlich", "erzaehlweise": "Aneinanderreihung von Fettnäpfchen, zynisch-komisch"},
        {
            "id": "regener",
            "name": "Sven Regener",
            "wortwahl": "umgangssprachlich, berlinerisch und bewusst abschweifend",
            "atmosphaere": "eine melancholische, aber gemütliche Alltagsstimmung",
            "erzaehlweise": "endlose, urkomische Dialogschleifen über völlige Nichtigkeiten"
        },
        {
            "id": "strunk",
            "name": "Heinz Strunk",
            "wortwahl": "eine Mischung aus derbem Vokabular und präziser, hässlicher Poesie",
            "atmosphaere": "trostlos-komisch und leicht beklemmend",
            "erzaehlweise": "sezierender Fokus auf das menschliche und soziale Scheitern"
        },
        {
            "id": "kling",
            "name": "Marc-Uwe Kling",
            "wortwahl": "trocken, präzise und stark auf Pointen fixiert",
            "atmosphaere": "eine logisch-absurde Welt mit gesellschaftskritischem Unterton",
            "erzaehlweise": "schnelle, schlagfertige Dialoge und dialektische Wortspiele"
        },
        {
            "id": "stuckrad_barre",
            "name": "Benjamin von Stuckrad-Barre",
            "wortwahl": "hyper-nervös, voller Markennamen und Anglizismen",
            "atmosphaere": "hektisch, eitel und scharf-beobachtend",
            "erzaehlweise": "atemlose Stakkato-Sätze und ironische Milieu-Studien"
        },
        {
            "id": "evers",
            "name": "Horst Evers",
            "wortwahl": "unaufgeregt, bodenständig und herrlich trocken",
            "atmosphaere": "eine warmherzige Welt, in der die Logik ständig falsch abbiegt",
            "erzaehlweise": "erzählende Schilderung von Alltagskatastrophen, die völlig eskalieren"
        },
        {
            "id": "loriot",
            "name": "Loriot",
            "wortwahl": "gestochen scharfes, übertrieben höfliches Hochdeutsch und förmliche Floskeln",
            "atmosphaere": "eine steife, bürgerliche Umgebung, in der die Etikette schwerer wiegt als die Logik",
            "erzaehlweise": "minuziöse Schilderung von Kommunikationsstörungen und das Eskalieren von banalen Missverständnissen"
        },
        {
            "id": "pratchett",
            "name": "Terry Pratchett",
            "wortwahl": "Scharfsinnig, metaphernreich, britisch-trocken",
            "atmosphaere": "Satirisch-warmherzig; eine Welt auf dem Rücken von Elefanten",
            "erzaehlweise": "Parodie von Fantasy-Tropen, brillante Fußnoten, Entlarvung von Dummheit"
        },
        {
            "id": "adams",
            "name": "Douglas Adams",
            "wortwahl": "Technisch-absurd, lakonisch, kosmisch-kühl",
            "atmosphaere": "Kosmisches Chaos, in dem ständig die Parkuhr abläuft",
            "erzaehlweise": "Philosophischer Blödsinn, trockene Oneliner, totale Vernichtung der Logik"
        },
        {
            "id": "kinney",
            "name": "Jeff Kinney",
            "wortwahl": "Einfach, authentisch, pubertär-ironisch",
            "atmosphaere": "Die ungeschönte, peinliche Welt des Schulhofs",
            "erzaehlweise": "Tagebuch-Stil, pointiertes Scheitern, Fokus auf Alltags-Fettnäpfchen"
        },
        {
            "id": "kaestner",
            "name": "Erich Kästner",
            "wortwahl": "Klar, ironisch, moralisch ohne erhobenen Zeigefinger",
            "atmosphaere": "Menschlich, hoffnungsvoll, geprägt von scharfem Witz",
            "erzaehlweise": "Beobachtend, ehrlich, mit großem Herz für die kleinen Leute"
        },
        {
            "id": "lindgren",
            "name": "Astrid Lindgren",
            "wortwahl": "Herzlich, mutig, kindlich-weise",
            "atmosphaere": "Sommerlich-melancholisch, tief geborgen und frei",
            "erzaehlweise": "Voller Empathie, Fokus auf Gerechtigkeit und kindliche Stärke"
        },
        {
            "id": "dahl",
            "name": "Roald Dahl",
            "wortwahl": "Erfinderisch, drastisch, leicht grausam",
            "atmosphaere": "Skurril, makaber-lustig, herrlich respektlos",
            "erzaehlweise": "Schadenfreude, klare Parteinahme für Kinder gegen fiese Erwachsene"
        },
        {
            "id": "christie",
            "name": "Agatha Christie",
            "wortwahl": "Sachlich, britisch-höflich, bieder",
            "atmosphaere": "Trügerisch idyllisch, logisch-kalt und analytisch",
            "erzaehlweise": "Strenges Rätsel-Design (Whodunnit), Fokus auf psychologische Motive"
        },
        {
            "id": "king",
            "name": "Stephen King",
            "wortwahl": "Detailreich, volksnah, markenfixiert",
            "atmosphaere": "Alltäglich, langsam ins Unheimliche und Grauenvolle kippend",
            "erzaehlweise": "Psychologischer Horror, Fokus auf Urängste in der Vorstadt"
        },
        {
            "id": "hemingway",
            "name": "Ernest Hemingway",
            "wortwahl": "Karg, substantivlastig, fast keine Adjektive",
            "atmosphaere": "Stoisch, unterkühlt, emotional beherrscht",
            "erzaehlweise": "Kurze Sätze, Eisberg-Modell (das Wichtigste steht zwischen den Zeilen)"
        }
    ],
    "kids": [
        {"id": "funke", "name": "Cornelia Funke", "wortwahl": "Magisch, farbenfroh, bildstark", "atmosphaere": "Wundervoll, abenteuerlich, märchenhaft", "erzaehlweise": "Mitreißend, immersiv, warmherzig"},
        {"id": "pantermueller", "name": "Alice Pantermüller", "wortwahl": "Rotzig, kindgerecht, umgangssprachlich", "atmosphaere": "Chaotisch, alltäglich, lustig", "erzaehlweise": "Frech, tagebuchartig, im Plauderton"},
        {"id": "auer", "name": "Margit Auer", "wortwahl": "Empathisch, warm, verständlich", "atmosphaere": "Geborgen, geheimnisvoll, magisch-alltäglich", "erzaehlweise": "Pädagogisch wertvoll, spannungsvoll, auf Augenhöhe der Kinder"}
    ]
}

def get_author_names(style_string: str) -> str:
    """Helper to resolve author IDs (comma separated) to their full names."""
    selected_ids = [s.strip() for s in style_string.split(",")] if style_string else []
    all_authors = {a['id']: a for category in STANZWERK_BIBLIOTHEK.values() for a in category}
    valid_names = [all_authors[aid]['name'] for aid in selected_ids if aid in all_authors]
    
    if not valid_names:
        return "Neutraler Autor"
    return ", ".join(valid_names)

def generate_modular_prompt(style_string: str) -> str:
    selected_ids = [s.strip() for s in style_string.split(",")] if style_string else []
    all_authors = {a['id']: a for category in STANZWERK_BIBLIOTHEK.values() for a in category}
    valid_authors = [all_authors[aid] for aid in selected_ids if aid in all_authors]
    
    if not valid_authors:
        return "Stil: Neutraler, klarer Autorentyp."
        
    rules = [
        "Basis-Stil (40%): Ein klarer, gut vorlesbarer Stil mit natürlichem Rhythmus. Nutze eine Mischung aus prägnanten Sätzen und eleganten Nebensätzen, um den Lesefluss lebendig zu gestalten."
    ]
    
    if len(valid_authors) == 1:
        author = valid_authors[0]
        rules.append(f"Zusätzlicher Einfluss (60%) von {author['name']}:")
        rules.append(f"- Wortwahl: {author['wortwahl']}")
        rules.append(f"- Atmosphäre: {author['atmosphaere']}")
        rules.append(f"- Erzählweise: {author['erzaehlweise']}")
    elif len(valid_authors) == 2:
        a1, a2 = valid_authors
        rules.append("Zusätzlicher Einfluss (60%), aufgeteilt auf zwei Autoren:")
        rules.append(f"- Wortwahl ({a1['name']}): {a1['wortwahl']}")
        rules.append(f"- Atmosphäre ({a2['name']}): {a2['atmosphaere']}")
        rules.append(f"- Erzählweise (gemischt): Eine Synthese beider Ansätze ({a1['erzaehlweise']} UND {a2['erzaehlweise']})")
    else:
        a1, a2, a3 = valid_authors[:3]
        rules.append("Zusätzlicher Einfluss (60%), strikt aufgeteilt auf drei Autoren:")
        rules.append(f"- Wortwahl ({a1['name']}): {a1['wortwahl']}")
        rules.append(f"- Atmosphäre ({a2['name']}): {a2['atmosphaere']}")
        rules.append(f"- Erzählweise ({a3['name']}): {a3['erzaehlweise']}")
        
    return "\n".join(rules)

GENRES_BIBLIOTHEK = {
    "Krimi": {"name": "Krimi", "ziel": "Lösung eines Rätsels", "tropen": "Whodunnit-Struktur, Alibi-Prüfung, Rote Heringe (falsche Fährten), Deduktion, der entscheidende Sachbeweis"},
    "Abenteuer": {"name": "Abenteuer", "ziel": "Eine Reise bewältigen", "tropen": "In-Medias-Res-Start, physische Hindernisse, das magische Artefakt, die Mentor-Figur, exotische Schauplätze"},
    "Science-Fiction": {"name": "Science-Fiction", "ziel": "Was-wäre-wenn-Szenario", "tropen": "Technobabble, ethisches Dilemma, Worldbuilding-Details, futuristischer Slang, spekulative Biologie"},
    "Märchen": {"name": "Märchen", "ziel": "Ordnung wiederherstellen", "tropen": "Die Zahl Drei (Wiederholungen), sprechende Objekte, klare Gut-Böse-Moral, Prüfungen des Herzens, Anthropomorphismus"},
    "Komödie": {"name": "Komödie", "ziel": "Absurdität entlarven", "tropen": "Schlagabtausch (Banter), Running Gags, komische Fallhöhe, Ironie, absurde Logikketten, Slapstick-Elemente"},
    "Thriller": {"name": "Thriller", "ziel": "Überleben / Bedrohung abwenden", "tropen": "Tickende Uhr (Zeitdruck), unzuverlässiger Erzähler, Paranoia, Cliffhanger am Kapitelende, Twists"},
    "Drama": {"name": "Drama", "ziel": "Innere Konflikte klären", "tropen": "Subtext in Gesprächen, Flashbacks, innere Monologe, emotionaler Wendepunkt, Katharsis"},
    "Grusel": {"name": "Grusel", "ziel": "Das Unheimliche erfahren", "tropen": "Das Unheimliche (Uncanny), Foreshadowing, Isolation, Verfall, das Unbekannte (Andeutungen statt Zeigen)"},
    "Fantasy": {"name": "Fantasy", "ziel": "Das Böse bezwingen", "tropen": "Das Erwählten-Motiv, Magie-System mit Regeln, Companions, epische Landschaften, das Artefakt der Macht"},
    "Satire": {"name": "Satire", "ziel": "Absurdes entlarven", "tropen": "Überzeichnung, ironische Umkehrung, fiktive Institutionen, der naive Erzähler, Brecht'scher Verfremdungseffekt"},
    "Dystopie": {"name": "Dystopie", "ziel": "Unterdrückung entkommen oder aufdecken", "tropen": "Die Lüge des Systems, das verbotene Objekt/Wort, innerer Widerstand, Propaganda als Kulisse, Hope Spot"},
    "Historisch": {"name": "Historisch", "ziel": "Vergangenes lebendig machen", "tropen": "Period-accurate Details, Zeitgeist als Antagonist, historische Nebenfiguren, Anachronismus als Stilmittel"},
    "Mythologie": {"name": "Mythologie", "ziel": "Kosmische Ordnung erklären", "tropen": "Göttliche Intervention, Hybris als Motor, das Orakel, Sterblicher vs. Unsterblicher, Metamorphose als Auflösung"},
    "Roadtrip": {"name": "Roadtrip", "ziel": "Sich selbst (wieder)finden", "tropen": "Der unfreiwillige Begleiter, Orte als Charaktere, das Gespräch im Auto, die unerwartete Abzweigung, Ankommen als Metapher"},
    "Gute Nacht": {"name": "Gute Nacht", "ziel": "Zur Ruhe kommen, sicher ankommen", "tropen": "Langsames Tempo, sinkende Energie-Kurve, beruhigende Wiederholungen, warme Bilder (Licht, Wärme, Stille), offenes Ende ohne Auflösungsdruck"},
    "Fabel": {"name": "Fabel", "ziel": "Eine Lebensweisheit illustrieren", "tropen": "Tierprotagonisten mit menschlichen Eigenschaften, die Moral am Ende, klare Gut/Falsch-Zuordnung, einfache Sprache, zeitlose Schauplätze (Wald, Dorf, Marktplatz)"}
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
        {"typ": "Der soziale Bruch", "logik": "Eine banale Höflichkeit führt zu einer völlig unerwarteten Reaktion."},
        {"typ": "Das falsche Detail", "logik": "An einem vertrauten Ort liegt ein Objekt, das dort absolut nicht hingehört."},
        {"typ": "Die verschwiegene Wahrheit", "logik": "Ein Gespräch über Belangloses maskiert eine tiefe, unsichtbare Spannung."},
        {"typ": "Die fatale Verwechslung", "logik": "Ein kleiner Griff ins falsche Regal löst eine unvorhersehbare Kette von Ereignissen aus."},
        {"typ": "Das Familiengeheimnis", "logik": "Ein Erbstück entpuppt sich als Beweis für eine jahrzehntelange Lüge."},
        {"typ": "Der rätselhafte Fund", "logik": "In der eigenen Tasche findet sich ein Hinweis auf ein fremdes Leben."},
        {"typ": "Die plötzliche Erkenntnis", "logik": "Mitten im Smalltalk versteht er plötzlich die wahre Bedeutung eines alten Satzes."},
        {"typ": "Der unheimliche Zufall", "logik": "Zwei fremde Ereignisse scheinen auf beängstigende Weise verknüpft."},
        {"typ": "Die unterdrückte Angst", "logik": "Ein alltäglicher Vorgang triggert eine Erinnerung, die alles infrage stellt."},
        {"typ": "Der stille Beobachter", "logik": "Ein winziger Hinweis macht aus einem Gefühl die Gewissheit, beobachtet zu werden."},
        {"typ": "Die Physiognomische Entgleisung", "logik": "Ein flüchtiges Muskelzucken im Gesicht widerspricht der Aussage und enthüllt eine bittere Wahrheit."},
        {"typ": "Das olfaktorisch-biografische Echo", "logik": "Ein banaler Geruch katapultiert den Protagonisten in eine lähmende Erinnerung."},
        {"typ": "Die haptische Dissonanz", "logik": "Die Textur eines Gegenstandes fühlt sich 'falsch' an und deutet auf eine gezielte Täuschung hin."},
        {"typ": "Das Milieu-Störgeräusch", "logik": "In einer geordneten Umgebung taucht ein Detail auf, das dort absolut deplatziert ist."},
        {"typ": "Die rhetorische Sackgasse", "logik": "Ein Satz, der als Kompliment beginnt, lässt durch ein winziges Zögern Verachtung spürbar werden."},
        {"typ": "Die statistische Anomalie", "logik": "Eine rein zufällige Beobachtung löst eine paranoide, aber logisch begründbare Schlussfolgerung aus."}
    ]
    
    import random
    selected_hook = random.choice(stanzwerk_hooks)
        
    prompt = f"""Du bist ein Meister der präzisen Alltagsbeobachtung. Generiere einen Story-Hook, der eine realistische Situation durch eine unerwartete Wendung oder ein psychologisches Detail spannend macht.

Regeln:
- Bleibe innerhalb der physikalischen Gesetze (kein Surrealismus).
- Finde die Spannung im Zwischenmenschlichen oder in einem verborgenen Geheimnis.
- Nutze starke Verben statt Adjektiven.
- Der Satz muss einen Konflikt andeuten, keine Lösung.
- WICHTIG: Exakt 1 Satz, maximal 15 Wörter

Werkzeug:
Struktur-Schablone: [{selected_hook['typ']}]: {selected_hook['logik']}
"""
    try:
        if not rate_limiter.has_daily_quota("text"):
            return "Das Tageslimit für Geschichten ist leider erreicht. Bitte versuche es morgen wieder."
            
        await rate_limiter.wait_for_capacity("text")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_TEXT_MODEL,
            contents=prompt,
            config={
                "temperature": 0.9,
                "max_output_tokens": 1000,
                "top_k": 20,
            }
        )
        rate_limiter.increment_daily_quota("text")
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
    remix_type: str | None = None,
    further_instructions: str | None = None,
    parent_text: dict | None = None,
) -> dict:
    # Due to LLM word length limits (~1000 words max per request), 
    # we always use the multi-pass (chapter-by-chapter) generation.
    return await _generate_multi_pass(
        prompt, genre, style, characters, target_minutes, on_progress,
        remix_type, further_instructions, parent_text
    )


async def _generate_single_pass(
    prompt, genre, style, characters, target_minutes, on_progress,
    remix_type=None, further_instructions=None, parent_text=None
):
    """Original single-pass logic for shorter stories with improved JSON cleanup."""
    selected_style_info = generate_modular_prompt(style)
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Abenteuer"])
    # 120 words per minute is a safe target for natural prosody with subordinate clauses
    word_count = target_minutes * 120
    char_text = f"\nHauptcharaktere: {', '.join(characters)}" if characters else ""
    user_hook = prompt

    # Context for remix
    remix_context = ""
    if remix_type == "improvement" and parent_text:
        remix_context = f"\n\nDIES IST EINE VERBESSERUNG DER FOLGENDEN GESCHICHTE:\n{json.dumps(parent_text, ensure_ascii=False)}\n\nSPEZIELLE ANWEISUNGEN FÜR DIE VERBESSERUNG:\n{further_instructions or 'Mache die Geschichte einfach besser.'}"
    elif remix_type == "sequel" and parent_text:
        parent_synopsis = parent_text.get("synopsis", "Teil 1")
        parent_title = parent_text.get("title", "Die erste Geschichte")
        remix_context = f"\n\nDIES IST EINE FORTSETZUNG (SEQUEL) ZU:\nTitel: {parent_title}\nZusammenfassung von Teil 1: {parent_synopsis}\n\nANWEISUNGEN FÜR DIE FORTSETZUNG:\n{further_instructions or 'Erzähle die Geschichte weiter.'}"

    master_prompt = f"""Du bist ein preisgekrönter Autor. Schreibe eine abgeschlossene Kurzgeschichte.

202: STRIKTE REGELN:
203: 1. NATÜRLICHER RHYTHMUS: Achte auf einen abwechslungsreichen Satzbau. Nutze sowohl kurze, prägnante Aussagen als auch elegante Nebensätze, um einen flüssigen Leserythmus zu erzeugen. Das macht die Geschichte für das Vorlesen (Audio) lebendiger und interessanter. Vermeide jedoch extrem überladene Schachtelsätze.
204: 2. Stil-Inspiration:
205: {selected_style_info}
206: Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Die Geschichte endet mit dem letzten narrativen Moment. Kein Kitsch, keine Moral!
207: 3. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
208: 4. Pacing & Detail: Hetze nicht durch die Handlung. Entwickle Szenen durch konkrete Details, aber halte die Syntax (Satzbau) einfach.
209: 5. UMFANG: STRENGES MAXIMUM von {word_count} Wörtern. Nutze eine präzise Wortwahl statt vieler Adjektive. Die neue sprachliche Freiheit darf NICHT zu unnötiger Länge führen. Vermeide Abschweifungen.

Rahmenbedingungen:
Schreibe eine Geschichte im Genre {genre_data['name']}. Der Kern der Handlung (Nutzer-Wunsch) ist: {user_hook}{char_text}. Folge dem Narrativ: {genre_data['ziel']} unter Verwendung von {genre_data['tropen']}.
{remix_context}

Antworte EXKLUSIV im JSON-Format:
{{
    "title": "Titel",
    "synopsis": "Zusammenfassung",
    "full_text": "Text der Geschichte..."
}}"""

    if on_progress:
        await on_progress("generating_text", f"Schreibe '{style}'-Geschichte ({target_minutes} Min)...", 5)

    if not rate_limiter.has_daily_quota("text"):
        raise RuntimeError("Das Tageslimit für KI-Generierungen ist heute leider erreicht.")

    await rate_limiter.wait_for_capacity("text")
    import asyncio
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL,
        contents=master_prompt,
        config={"response_mime_type": "application/json", "temperature": 0.85, "max_output_tokens": 8192}
    )
    rate_limiter.increment_daily_quota()

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


async def _generate_multi_pass(
    prompt, genre, style, characters, target_minutes, on_progress,
    remix_type=None, further_instructions=None, parent_text=None
):
    """Two-step generation for long stories to ensure length and flow."""
    selected_style_info = generate_modular_prompt(style)
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Abenteuer"])
    user_hook = prompt
    char_text = f"\nHauptcharaktere: {', '.join(characters)}" if characters else ""
    
    # Context for remix
    remix_context = ""
    if remix_type == "improvement" and parent_text:
        remix_context = f"\n\nDIES IST EINE VERBESSERUNG DER FOLGENDEN GESCHICHTE:\n{json.dumps(parent_text, ensure_ascii=False)}\n\nSPEZIELLE ANWEISUNGEN FÜR DIE VERBESSERUNG:\n{further_instructions or 'Mache die Geschichte einfach besser.'}"
    elif remix_type == "sequel" and parent_text:
        parent_synopsis = parent_text.get("synopsis", "Teil 1")
        parent_title = parent_text.get("title", "Die erste Geschichte")
        remix_context = f"\n\nDIES IST EINE FORTSETZUNG (SEQUEL) ZU:\nTitel: {parent_title}\nZusammenfassung von Teil 1: {parent_synopsis}\n\nANWEISUNGEN FÜR DIE FORTSETZUNG:\n{further_instructions or 'Erzähle die Geschichte weiter.'}"

    # Target total words. 120 WPM is better for natural rhythm and prosody.
    total_words = target_minutes * 120
    
    # Enforce strictly 5-minute chapters (650 words each).
    # 10 min = 2 chapters, 15 min = 3 chapters, 20 min = 4 chapters
    num_segments = max(2, target_minutes // 5)
    words_per_segment = total_words // num_segments

    if on_progress:
        msg = f"Plane Geschichte ({target_minutes} Min, {num_segments} Kapitel)..."
        if remix_type == "sequel": msg = f"Plane Fortsetzung ({target_minutes} Min, {num_segments} Kapitel)..."
        if remix_type == "improvement": msg = f"Überarbeite Geschichte ({target_minutes} Min, {num_segments} Kapitel)..."
        await on_progress("generating_text", msg, 2)

    # Step 1: Generate Outline
    outline_prompt = f"""Erstelle eine detaillierte Gliederung für eine {target_minutes}-minütige Kurzgeschichte.
Schreibe eine Geschichte im Genre {genre_data['name']}. Der Kern der Handlung (Nutzer-Wunsch) ist: {user_hook}{char_text}. Folge dem Narrativ: {genre_data['ziel']} unter Verwendung von {genre_data['tropen']}.
{remix_context}

Stil-Vorgaben:
{selected_style_info}

Teile die Geschichte in exakt {num_segments} logische Abschnitte auf.
WICHTIG: Die Geschichte soll wie aus einem Guss erscheinen. Die Abschnitte dienen nur der internen Planung.
ACHTUNG ZUR LÄNGE: Die gesamte Geschichte darf STRENGSTENS MAXIMAL {total_words} Wörter lang werden. Jeder Abschnitt muss Material für maximal {words_per_segment} Wörter Text bieten. Keine Abschweifungen oder Füllsätze!
Antworte NUR im JSON-Format:
{{
    "title": "Titel",
    "synopsis": "Prägnante Zusammenfassung (maximal 3-4 Sätze), die Lust auf die Geschichte macht.",
    "segments": [
        {{ "goal": "Was in diesem Teil passiert..." }},
        ...
    ]
}}"""

    try:
        if not rate_limiter.has_daily_quota("text"):
            raise RuntimeError("Das Tageslimit für KI-Generierungen ist heute leider erreicht.")
            
        await rate_limiter.wait_for_capacity("text")
        outline_res = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_TEXT_MODEL,
            contents=outline_prompt,
            config={"response_mime_type": "application/json"}
        )
        rate_limiter.increment_daily_quota("text")
        
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
        return await _generate_single_pass(
            prompt, genre, style, characters, target_minutes, on_progress,
            remix_type, further_instructions, parent_text
        )
    
    if not segments:
        return await _generate_single_pass(prompt, genre, style, characters, target_minutes, on_progress)
    
    full_chapters = []
    
    # Step 2: Iterative Writing
    for i, seg in enumerate(segments):
        if on_progress:
            pct = 5 + int((i / num_segments) * 25) # Up to 30%
            await on_progress("generating_text", f"Schreibe Teil {i+1}/{num_segments}...", pct)
            
        # Context is just the end of the previous chapter to maintain continuity
        context = f"Ende des vorherigen Kapitels: {full_chapters[-1]['text'][-1000:]}" if full_chapters else "Dies ist der Beginn der Geschichte."
        
        is_last_chapter = (i == num_segments - 1)
        
        if is_last_chapter:
            ende_regel = f"5. UMFANG & ENDE: Schreibe STRENG MAXIMAL {words_per_segment} Wörter. DIES IST DAS FINALE KAPITEL! Führe die Geschichte zwingend zu einem runden, atmosphärischen Abschluss. Schließe die Handlung ab. Kein Cliffhanger mehr!"
        else:
            ende_regel = f"5. UMFANG & ENDE: Schreibe STRENG MAXIMAL {words_per_segment} Wörter. WICHTIG: Beende das Kapitel NIEMALS mitten in einem Satz. Führe die Szene logisch zu Ende oder erzeuge einen weichen Übergang/Cliffhanger."
        
        write_prompt = f"""Schreibe das nächste chronologische Kapitel der Geschichte.

353: STRIKTE REGELN:
354: 1. NATÜRLICHER RHYTHMUS: Achte auf einen abwechslungsreichen Satzbau. Nutze sowohl kurze, prägnante Aussagen als auch elegante Nebensätze, um einen flüssigen Leserythmus zu erzeugen. Ideal für Audio/TTS, um Monotonie zu vermeiden. Vermeide jedoch extrem überladene Schachtelsätze.
355: 2. Stil-Inspiration:
356: {selected_style_info}
357: Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Kein Kitsch, keine Moral!
358: 3. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
359: 4. Pacing & Detail: Beschreibe präzise und atmosphärisch, aber halte den Satzbau einfach und direkt.
4. Format: Keinerlei Überschriften, Kapitelnummern oder Titel im generierten Text! Nur der reine, fließende Erzähltext für diesen Abschnitt. Die Geschichte muss nahtlos an den vorherigen Teil anknüpfen.
{f"SPEZIELLE REMIX-ANWEISUNG: {further_instructions}" if further_instructions else ""}
{ende_regel}

Rahmenbedingungen:
Titel der Gesamtgeschichte: {title}
Zusammenfassung der Geschichte: {synopsis}
Fokus / Ziel DIESES Kapitels: {seg['goal']}
{context}
"""
        if not rate_limiter.has_daily_quota("text"):
            raise RuntimeError("Das Tageslimit für KI-Generierungen wurde während der Geschichte erreicht.")
            
        await rate_limiter.wait_for_capacity("text")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_TEXT_MODEL,
            contents=write_prompt,
            config={"temperature": 0.8}
        )
        rate_limiter.increment_daily_quota()
        segment_text = response.text.strip()
        
        full_chapters.append({
            "title": "",
            "text": segment_text
        })

    return {
        "title": title,
        "synopsis": synopsis,
        "chapters": full_chapters
    }
