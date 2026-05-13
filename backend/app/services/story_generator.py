"""
Story generation service using Google Gemini Flash.
Two-step process: 1) Generate outline  2) Write detailed chapters
"""

from google import genai
from app.config import settings
import asyncio
import json
import re
from app.services.text_generator import generate_text
from app.services.rate_limiter import rate_limiter
from app.services.store import store
import logging
from pydantic import BaseModel

class StorySegment(BaseModel):
    plot_action: str
    setting: str
    emotional_shift: str
    ending_note: str

class OutlineSchema(BaseModel):
    title: str
    synopsis: str
    segments: list[StorySegment]

class PostStoryAnalysisSchema(BaseModel):
    refined_synopsis: str
    highlights: str

class SinglePassSchema(BaseModel):
    title: str
    synopsis: str
    full_text: str

logger = logging.getLogger(__name__)


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
        },
        {
            "id": "rooney",
            "name": "Sally Rooney",
            "wortwahl": "Schlicht, präzise, schmucklos",
            "atmosphaere": "Melancholisch, modern-urban",
            "erzaehlweise": "Fokus auf das Ungesagte, innerer Monolog"
        },
        {
            "id": "nin",
            "name": "Anaïs Nin",
            "wortwahl": "Bildreich, metaphorisch, lyrisch",
            "atmosphaere": "Intim, berauschend sinnlich, traumgleich",
            "erzaehlweise": "Tiefenpsychologisch erkundend, subjektiv"
        },
        {
            "id": "miller",
            "name": "Henry Miller",
            "wortwahl": "Vital, derb, ungeschönt",
            "atmosphaere": "Existenzialistisch, energetisch, ungebändigt",
            "erzaehlweise": "Ausschweifend, respektlos gegenüber Konventionen"
        },
        {
            "id": "rice",
            "name": "Anne Rice",
            "wortwahl": "Barock, reich an Adjektiven, opulent",
            "atmosphaere": "Gotisch, dekadent, prächtig-düster",
            "erzaehlweise": "Ausufernd beschreibend, hochemotional"
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
    "Fabel": {"name": "Fabel", "ziel": "Eine Lebensweisheit illustrieren", "tropen": "Tierprotagonisten mit menschlichen Eigenschaften, die Moral am Ende, klare Gut/Falsch-Zuordnung, einfache Sprache, zeitlose Schauplätze (Wald, Dorf, Marktplatz)"},
    "Modern Romanze": {"name": "Modern Romanze", "ziel": "Romantische Spannung in einem modernen urbanen Umfeld aufbauen", "tropen": "Schlagfertige Dialoge (Banter), Großstadt-Kulisse, Zufallsbegegnungen, moderne Dating-Dilemmata, Humor und Herzklopfen"},
    "Sinnliche Romanze": {"name": "Sinnliche Romanze", "ziel": "Emotionale und physische Annäherung (Slow Burn)", "tropen": "Intensive Blicke, zufällige Berührungen, knisternde Stille, Herzklopfen, romantisches Setting, ungesagte Wünsche"},
    "Erotik": {"name": "Erotik", "ziel": "Erkundung von Verlangen und körperlicher Leidenschaft", "tropen": "Sinnliche Details, physische Spannung, Spiel mit Verführung, Entdeckung des Körpers, ästhetische Beschreibungen, Hingabe"},
    "Dark Romance": {"name": "Dark Romance", "ziel": "Überwindung von Grenzen und Tabus in einer moralisch grauen Welt", "tropen": "Dominanz und Hingabe, verbotenes Verlangen, düstere Verführung, emotionale Extreme, Spiel mit dem Feuer, komplexe Machtdynamiken"}
}

HOOK_PERSONEN = [
    "Der Perfektionist (Zwanghaft, achtet auf Details)",
    "Der reuige Sünder (Sucht Vergebung)",
    "Die kühle Strategin (Plant drei Schritte voraus)",
    "Der loyale Diener (Weiß zu viel, sagt nichts)",
    "Der charismatische Blender (Lebt von der Fassade)",
    "Die furchtlose Grenzgängerin (Riskiert alles)",
    "Der melancholische Sammler (Hängt an der Vergangenheit)",
    "Die unschuldige Beobachterin (Sieht, was sie nicht verstehen darf)",
    "Der gefallene Held (Zynisch und müde)",
    "Die manipulative Gastgeberin (Kontrolliert die soziale Bühne)",
    "Der stumme Zeuge (Jemand, den man übersieht)",
    "Die rastlose Sucherin (Findet nie, was sie braucht)",
    "Der strenge Lehrmeister (Fordert absolute Disziplin)",
    "Die verlorene Erbin (Trägt eine Last, die sie nicht will)",
    "Der unberechenbare Rivale (Spiegelt die Schwächen des anderen)",
    "Die geduldige Rächerin (Wartet auf den richtigen Moment)",
    "Der paranoide Experte (Traut niemandem)",
    "Die empathische Außenseiterin (Spürt die Spannungen im Raum)",
    "Der kühne Hochstapler (Spielt ein gefährliches Spiel)",
    "Die erschöpfte Autorität (Trägt zu viel Verantwortung)",
    "Der idealistische Träumer (Wird von der Realität eingeholt)",
    "Die diskrete Vermittlerin (Löst Probleme im Schatten)",
    "Der bittere Skeptiker (Hinterfragt jedes Motiv)",
    "Die verborgene Bedrohung (Wirkt harmlos, ist es nicht)",
    "Der letzte Getreue (Bleibt, wenn alle anderen gehen)"
]

HOOK_SETTINGS = [
    "Das verregnete Hafenviertel (Nass, laut, anonym)",
    "Die Bibliothek bei Nacht (Staubig, still, ehrwürdig)",
    "Die luxuriöse Penthouse-Suite (Kalt, gläsern, isoliert)",
    "Der dichte Tannenwald (Eng, schattig, geheimnisvoll)",
    "Das überfüllte Spiegelkabinett (Verwirrend, hell, verzerrt)",
    "Die verlassene Bergstation (Windig, rostig, einsam)",
    "Der prunkvolle Ballsaal (Grell, laut, maskiert)",
    "Die sterile Intensivstation (Weiß, piepend, klinisch)",
    "Das nächtliche Parkdeck (Beton, Neon, Echo)",
    "Der verwilderte Schlossgarten (Überwuchert, duftend, melancholisch)",
    "Die stickige Hinterzimmer-Bar (Rauchig, dunkel, verrucht)",
    "Das Archiv der verlorenen Briefe (Papier, Geheimnisse, Stille)",
    "Die zugige U-Bahn-Station (Kalt, metallisch, Transit)",
    "Das Gewächshaus im Sturm (Glas, prasselnder Regen, grün)",
    "Die Galerie für moderne Kunst (Minimalistisch, teuer, leer)",
    "Das Lagerhaus am Fluss (Holzig, modrig, weit)",
    "Der einsame Leuchtturm (Salzig, stürmisch, exponiert)",
    "Die VIP-Lounge eines Casinos (Samt, Gold, nervös)",
    "Das schattige Beichtzimmer (Eng, hölzern, intim)",
    "Der Korridor eines Nobelhotels (Teppich, Türen, anonym)",
    "Die Werkstatt eines Uhrmachers (Tickend, präzise, kleinteilig)",
    "Das baufällige Amphitheater (Steinern, geschichtsträchtig, offen)",
    "Die Küche während einer Feier (Hektisch, heiß, ehrlich)",
    "Das Observatorium am Abgrund (Metallisch, weit, sternenklar)",
    "Der Steg im Morgengrauen (Nebel, Holz, still)"
]

GENRE_HOOKS_LIBRARY = {
    "Krimi": "Im Tresor lag kein Gold, sondern ein warmer Apfelkuchen und ein Zettel: 'Du bist zu spät, Kommissar.'",
    "Abenteuer": "Die Karte versprach den Pfad der Stille, doch das rhythmische Klopfen hinter uns war seit Stunden unser einziger Begleiter.",
    "Science-Fiction": "Das Terminal zeigte das Datum 21. Juni 2024 an – den Tag, an dem mein Vater verschwand. Doch draußen bestanden die Ruinen nur noch aus ewigem Neonlicht.",
    "Märchen": "Der Spiegel log nie, doch heute Morgen weigerte er sich, überhaupt ein Bild zu zeigen. Erst als die Prinzessin weinte, flüsterte er einen Namen, der im Königreich verboten war.",
    "Komödie": "Der Toaster hatte heute Morgen schlechte Laune und weigerte sich, Brot zu rösten, es sei denn, man sang ihm die Nationalhymne vor. In meiner Unterwäsche stehend, begann ich die erste Strophe.",
    "Thriller": "Fünf Minuten vor der Detonation stellte ich fest, dass der Entschärfungs-Code auf der Rückseite meines eigenen Ausweises stand. Dummerweise lag der Ausweis noch im Auto, das bereits auf dem Weg zur Schrottpresse war.",
    "Drama": "Sie sah ihn an und wusste, dass dieser Abschied der letzte war. Nicht wegen des Koffers in seiner Hand, sondern wegen der Art, wie er den Blick nicht mehr vom Boden hob.",
    "Grusel": "Das Kinderlachen kam eindeutig vom Dachboden – unmöglich in einem Haus, das seit fünfzig Jahren leer stand.",
    "Fantasy": "Das Schwert leuchtete nicht blau bei Gefahr, sondern begann leise zu summen, wenn jemand eine Lüge aussprach. Als der König den Thron bestieg, füllte ein ohrenbetäubender Lärm den Saal.",
    "Satire": "Das neue Ministerium für Effizienz hatte soeben beschlossen, das Atmen in ungeraden Minuten zu besteuern. Die Bürger klatschten Beifall, da die Steuererleichterung für das Ausatmen als historischer Sieg der Freiheit gefeiert wurde.",
    "Dystopie": "In einer Welt ohne Farben war die rote Blume in ihrem Hinterhof ein Todesurteil. Sie hielt die Gießkanne fest und wartete auf das Signal der Drohnen.",
    "Historisch": "Berlin, 1928: Der Rauch in der Bar war so dicht wie die Geheimnisse, die wir austauschten. Karl wusste, dass die Telegramme niemals ankommen durften, wenn wir den Morgen erleben wollten.",
    "Mythologie": "Hermes hatte seine Sandalen verloren, und der Olymp war im Chaos versunken. Ohne seine Eilmeldungen wusste Zeus nicht einmal, welchen Sterblichen er heute mit einem Blitz treffen sollte.",
    "Roadtrip": "Der alte Ford Mustang hatte mehr Rost als Lack, aber er war unsere einzige Chance, die Grenze vor Sonnenuntergang zu erreichen. Hinter uns wirbelte der Wüstenstaub alles auf, was wir jemals Zuhause genannt hatten.",
    "Gute Nacht": "Der Mond deckte die Wiesen mit einem silbernen Tuch zu, und die Uhren im Haus verlangsamten ihren Takt. Alles, was blieb, war das leise Atmen des Waldes vor dem Fenster.",
    "Fabel": "Der Fuchs erklärte dem Raben, dass Käse heutzutage völlig überbewertet sei und stattdessen Krypto-Währungen die Zukunft seien. Der Rabe, der noch nie ein Smartphone gesehen hatte, ließ vor lauter Verwirrung aber trotzdem seinen Bissen fallen.",
    "Modern Romanze": "An der Kasse im Supermarkt berührten sich unsere Hände beim Griff nach der letzten Packung Bio-Kaffee. Er lächelte so charmant, dass ich fast vergaß, dass er mich gerade bei eBay Kleinanzeigen für meinen alten Schrank versetzt hatte.",
    "Sinnliche Romanze": "Die Luft zwischen uns knisterte wie statische Elektrizität kurz vor einem Sommergewitter. Jede seiner Bewegungen war so langsam und bedacht, dass mein Herzschlag den Rhythmus seiner Schritte übernahm.",
    "Erotik": "Sein Blick brannte auf meiner Haut, noch bevor seine Finger den Saum meines Kleides erreichten. Das Verlangen war kein Flüstern mehr, sondern ein forderndes Echo, das jeden vernünftigen Gedanken im Keim erstickte.",
    "Dark Romance": "Er war mein Untergang und meine Rettung zugleich, ein Schatten, der mir die Freiheit stahl und mir zeigte, wie süß Gefangenschaft sein kann. Seine Liebe war kein Geschenk, sie war ein Besitzanspruch, den ich mit jedem Atemzug mehr genoss."
}

async def generate_story_hook(genre: str, author_id: str, user_input: str | None = None) -> str:
    """Generate a story hook using a multi-example few-shot prompt."""
    
    import random
    
    # 1. Get genre-specific example
    genre_example = GENRE_HOOKS_LIBRARY.get(genre, GENRE_HOOKS_LIBRARY["Abenteuer"])
    
    # 2. Get 2 random examples for variety (few-shot)
    other_genres = [g for g in GENRE_HOOKS_LIBRARY.keys() if g != genre]
    random_genres = random.sample(other_genres, 2)
    random_examples = [GENRE_HOOKS_LIBRARY[g] for g in random_genres]

    context_str = ""
    if user_input and user_input.strip():
        context_str = f"\nNUTZE DIESEN INPUT ALS BASIS ODER INSPIRATION:\n\"{user_input.strip()}\"\n"

    prompt = f"""Du bist ein kreativer Ideengeber für Kurzgeschichten. Generiere einen vollständigen Hook für eine Kurzgeschichte im Genre {genre}. {context_str}

REGELN:
- Nutze exakt 2-3 KURZE Sätze.
- In Summe maximal 50-60 Wörter.
- Beende JEDEN Satz vollständig mit Punkt, Ausrufezeichen oder Fragezeichen.
- KEINE abgebrochenen Sätze.
- Keine Einleitung, kein Gelaber, nur der Hook. 
- Stil: Hochwertig, überraschend, klischeefrei.

BEISPIELE FÜR DIE GEWÜNSCHTE QUALITÄT UND STRUKTUR:
1. (Genre {random_genres[0]}): "{random_examples[0]}"
2. (Genre {random_genres[1]}): "{random_examples[1]}"
3. (Genre {genre} - ZIELVORGABE): "{genre_example}"

DEIN HOOK:"""

    try:
        if not rate_limiter.has_daily_quota("text"):
            return "Das Tageslimit für Geschichten ist leider erreicht. Bitte versuche es morgen wieder."
            
        await rate_limiter.wait_for_capacity("text")
        # Inspiration/Hook should always be fast - use the default Flash model from config
        text_model = settings.GEMINI_TEXT_MODEL
        logger.info(f"Generating story hook with model: {text_model}")

        response_text = await generate_text(
            prompt=prompt,
            model=text_model,
            temperature=0.9,
            max_tokens=2000
        )
        rate_limiter.increment_daily_quota("text")
        hook_text = response_text.strip().strip('"').strip("'")
        
        # Log full text for debugging
        logger.info(f"GEN HOOK (raw): '{hook_text}'")
        
        # We stop doing aggressive trimming to see if the model can now finish its work
        return hook_text
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


async def _api_request_with_retry(func, *args, on_progress=None, max_retries=3, initial_delay=2, **kwargs):
    """Retries a function call with exponential backoff if it fails with a 503 error."""
    for i in range(max_retries):
        try:
            # We use to_thread because the genai SDK might be blocking
            logger.info(f"API_REQUEST: Calling {func.__name__ if hasattr(func, '__name__') else str(func)}")
            return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            from google.genai import errors
            # Check if it's a 503/Unavailable error
            err_str = str(e).upper()
            is_unavailable = "503" in err_str or "UNAVAILABLE" in err_str or isinstance(e, errors.ServerError)
            
            if is_unavailable and i < max_retries - 1:
                delay = initial_delay * (2 ** i)
                logger.warning(f"Gemini API 503/Unavailable (Attempt {i+1}). Retrying in {delay}s... Error: {e}")
                if on_progress:
                    # Report retry to user via progress callback
                    try:
                        await on_progress("retrying", f"Verbindung wird wiederholt (Versuch {i+2}/{max_retries})...")
                    except: pass
                await asyncio.sleep(delay)
                continue
            raise e

async def _generate_single_pass(
    prompt, genre, style, characters, target_minutes, on_progress,
    remix_type=None, further_instructions=None, parent_text=None
):
    """Original single-pass logic for shorter stories with improved JSON cleanup."""
    selected_style_info = generate_modular_prompt(style)
    genre_data = GENRES_BIBLIOTHEK.get(genre, GENRES_BIBLIOTHEK["Abenteuer"])
    # 150 words per minute is a better target for a richer story without being too dense
    word_count = target_minutes * 150
    char_text = f"\nHauptcharaktere: {', '.join(characters)}" if characters else ""
    user_hook = prompt

    # Context for remix
    remix_context = ""
    if remix_type == "improvement" and parent_text:
        # For improvements, we treat the LLM as an editor
        original_story_str = json.dumps(parent_text, ensure_ascii=False)
        remix_context = f"""
### REMIX-MODUS: VERBESSERUNG (EDITOR)
DIES IST EINE GEZIELTE ÜBERARBEITUNG DER FOLGENDEN GESCHICHTE:
{original_story_str}

SPEZIELLE ANWEISUNGEN FÜR DIE VERBESSERUNG:
{further_instructions or 'Mache die Geschichte einfach besser.'}

WICHTIGE REGELN FÜR DIESEN MODUS:
1. BEWAHRE DEN KERN: Behalte die grundlegende Handlung, die Namen der Charaktere und die Schauplätze bei, sofern sie nicht explizit geändert werden sollen.
2. PUNKTUELLE EDITS: Ändere nur, was nötig ist, um die 'Speziellen Anweisungen' zu erfüllen oder um den Stil zu optimieren.
3. KONTINUITÄT: Die neue Version muss sich wie eine verbesserte Fassung des Originals anfühlen, nicht wie eine völlig neue Geschichte.
"""
    elif remix_type == "sequel" and parent_text:
        parent_synopsis = parent_text.get("synopsis", "Teil 1")
        parent_title = parent_text.get("title", "Die erste Geschichte")
        remix_context = f"\n\nDIES IST EINE FORTSETZUNG (SEQUEL) ZU:\nTitel: {parent_title}\nZusammenfassung von Teil 1: {parent_synopsis}\n\nANWEISUNGEN FÜR DIE FORTSETZUNG:\n{further_instructions or 'Erzähle die Geschichte weiter.'}"

    master_prompt = f"""Du bist ein preisgekrönter Autor. Schreibe eine abgeschlossene Kurzgeschichte.

STRIKTE REGELN:
1. NATÜRLICHER RHYTHMUS: Achte auf einen abwechslungsreichen Satzbau. Nutze sowohl kurze, prägnante Aussagen als auch elegante Nebensätze, um einen flüssigen Leserythmus zu erzeugen. Das macht die Geschichte für das Vorlesen (Audio) lebendiger und interessanter. Vermeide jedoch extrem überladene Schachtelsätze.
2. Stil-Inspiration:
{selected_style_info}
Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Die Geschichte endet mit dem letzten narrativen Moment. Kein Kitsch, keine Moral!
3. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
4. Pacing & Detail: Hetze nicht durch die Handlung. Entwickle Szenen durch konkrete Details, aber halte die Syntax (Satzbau) einfach.
5. UMFANG: ZIELGRÖßE: ca. {word_count} Wörter. Nutze eine präzise Wortwahl statt vieler Adjektive. Die neue sprachliche Freiheit darf NICHT zu unnötiger Länge führen. Vermeide Abschweifungen.

Rahmenbedingungen:
Schreibe eine Geschichte im Genre {genre_data['name']}. Der Kern der Handlung (Nutzer-Wunsch) ist: {user_hook}{char_text}. Folge dem Narrativ: {genre_data['ziel']} unter Verwendung von {genre_data['tropen']}.
{remix_context}

Antworte EXKLUSIV im validen JSON-Format. WICHTIG: Entwerte (escape) alle Anführungszeichen innerhalb von Texten mit einem Backslash (z.B. \\"Wort\\").
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
    # Get current model from DB or fallback to config
    text_model = store.get_system_setting("gemini_text_model", settings.GEMINI_TEXT_MODEL)
    logger.info(f"Generating single-pass story with model: {text_model}")

    response_text = await generate_text(
        prompt=master_prompt,
        model=text_model,
        temperature=0.85,
        max_tokens=16384,
        response_mime_type="application/json",
        response_schema=SinglePassSchema
    )
    rate_limiter.increment_daily_quota()

    text = response_text.strip()
    
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
    except Exception as json_err:
        logger.warning(f"Single-pass JSON parse failed: {json_err}. Attempting aggressive cleanup...")
        text = re.sub(r',\s*\}', '}', text)
        text = re.sub(r',\s*\]', ']', text)
        try:
            data = json.loads(text)
        except:
            raise json_err
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
        # For improvements, we treat the LLM as an editor
        original_story_str = json.dumps(parent_text, ensure_ascii=False)
        remix_context = f"""
### REMIX-MODUS: VERBESSERUNG (EDITOR)
DIES IST EINE GEZIELTE ÜBERARBEITUNG DER FOLGENDEN GESCHICHTE:
{original_story_str}

SPEZIELLE ANWEISUNGEN FÜR DIE VERBESSERUNG:
{further_instructions or 'Mache die Geschichte einfach besser.'}

WICHTIGE REGELN FÜR DIESEN MODUS:
1. BEWAHRE DEN KERN: Behalte die grundlegende Handlung, die Namen der Charaktere und die Schauplätze bei, sofern sie nicht explizit geändert werden sollen.
2. PUNKTUELLE EDITS: Ändere nur, was nötig ist, um die 'Speziellen Anweisungen' zu erfüllen oder um den Stil zu optimieren.
3. KONTINUITÄT: Die neue Version muss sich wie eine verbesserte Fassung des Originals anfühlen, nicht wie eine völlig neue Geschichte.
"""
    elif remix_type == "sequel" and parent_text:
        parent_synopsis = parent_text.get("synopsis", "Teil 1")
        parent_title = parent_text.get("title", "Die erste Geschichte")
        remix_context = f"\n\nDIES IST EINE FORTSETZUNG (SEQUEL) ZU:\nTitel: {parent_title}\nZusammenfassung von Teil 1: {parent_synopsis}\n\nANWEISUNGEN FÜR DIE FORTSETZUNG:\n{further_instructions or 'Erzähle die Geschichte weiter.'}"

    # Target total words. 150 WPM allows for a more detailed story.
    total_words = target_minutes * 150
    
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
    if remix_type == "improvement" and parent_text:
        outline_prompt = f"""Du bist ein Editor. Überarbeite die Gliederung für eine bestehende {target_minutes}-minütige Kurzgeschichte ({num_segments} Abschnitte).
Der Kern der ursprünglichen Handlung war: {user_hook}{char_text}.
Ursprünglicher Text: {json.dumps(parent_text, ensure_ascii=False)}

SPEZIELLE VERBESSERUNGS-ANWEISUNG: {further_instructions or 'Optimiere den Text.'}

RECHNE MIT:
1. BEWAHRE DIE STRUKTUR: Halte dich an die {num_segments} Abschnitte der ursprünglichen Geschichte.
2. GEZIELTE ANPASSUNG: Plane nur Änderungen in den Segmenten, die für die 'Spezielle Verbesserungs-Anweisung' relevant sind.
3. KONTINUITÄT: Die Gliederung muss sicherstellen, dass die Geschichte ihren Charakter behält.

Antworte NUR im validen JSON-Format. WICHTIG: Entwerte (escape) alle Anführungszeichen innerhalb von Texten mit einem Backslash (z.B. \\"Wort\\").
{{
    "title": "Titel (evtl. angepasst)",
    "synopsis": "Aktualisierte Zusammenfassung",
    "segments": [
        {{ 
            "plot_action": "Was in diesem Teil im Vergleich zum Original geändert oder beibehalten wird...",
            "setting": "Ort der Handlung...",
            "emotional_shift": "Emotionale Entwicklung...",
            "ending_note": "Wie dieser Abschnitt endet..."
        }},
        ...
    ]
}}"""
    else:
        outline_prompt = f"""Erstelle eine detaillierte Gliederung für eine {target_minutes}-minütige Kurzgeschichte.
Schreibe eine Geschichte im Genre {genre_data['name']}. Der Kern der Handlung (Nutzer-Wunsch) ist: {user_hook}{char_text}. Folge dem Narrativ: {genre_data['ziel']} unter Verwendung von {genre_data['tropen']}.
{remix_context}

Stil-Vorgaben:
{selected_style_info}

Teile die Geschichte in exakt {num_segments} logische Abschnitte auf.
WICHTIG: Die Geschichte soll wie aus einem Guss erscheinen. Die Abschnitte dienen nur der internen Planung.
PACING & STRUKTUR: Der dramaturgische Bogen über die Segmente hinweg MUSS dem Ziel ({genre_data['ziel']}) und den Tropen ({genre_data['tropen']}) des Genres entsprechen! (z.B. eine kontinuierlich steigende Spannungskurve für Krimi/Abenteuer, oder eine stetig sinkende, beruhigende Energiekurve für Gute-Nacht-Geschichten).
ACHTUNG ZUR LÄNGE: Die gesamte Geschichte sollte etwa {total_words} Wörter lang werden. Jeder Abschnitt muss Material für ca. {words_per_segment} Wörter Text bieten. Keine Abschweifungen oder Füllsätze!
Antworte NUR im validen JSON-Format. WICHTIG: Entwerte (escape) alle Anführungszeichen innerhalb von Texten mit einem Backslash (z.B. \\"Wort\\").
{{
    "title": "Titel",
    "synopsis": "Prägnante Zusammenfassung (maximal 3-4 Sätze), die Lust auf die Geschichte macht.",
    "segments": [
        {{ 
            "plot_action": "Was konkret physisch passiert...",
            "setting": "Der Ort der Handlung...",
            "emotional_shift": "Die emotionale Entwicklung oder Stimmung...",
            "ending_note": "Wie dieser Abschnitt endet (z.B. Cliffhanger, ruhiger Ausklang)..."
        }},
        ...
    ]
}}"""

    try:
        logger.info(f"GEN_MULTI_PASS: Requesting outline from Gemini (Style: {style}, Genre: {genre}, Prompt: {prompt[:50]}...)")
        if not rate_limiter.has_daily_quota("text"):
            raise RuntimeError("Das Tageslimit für KI-Generierungen ist heute leider erreicht.")
            
        await rate_limiter.wait_for_capacity("text")
        # Get current model from DB or fallback to config
        text_model = store.get_system_setting("gemini_text_model", settings.GEMINI_TEXT_MODEL)
        logger.info(f"Generating story outline with model: {text_model}")

        response_text = await generate_text(
            prompt=outline_prompt,
            model=text_model,
            temperature=0.8,
            max_tokens=8192,
            response_mime_type="application/json"
        )
        rate_limiter.increment_daily_quota("text")
        
        text = response_text.strip()
        
        # Robust JSON extraction: Find the first { and the last }
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        else:
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).replace("```", "", 1).strip()
            elif text.startswith("```"):
                text = text.replace("```", "", 2).strip()
                
        try:
            outline_data = json.loads(text)
        except Exception as json_err:
            logger.warning(f"Initial JSON parse failed: {json_err}. Attempting aggressive cleanup...")
            # Aggressive cleanup for unescaped quotes
            # This is a heuristic: try to find common patterns like "key": "value with "quotes" inside"
            # But simpler: just try to use a more forgiving parser logic if we had one.
            # For now, let's just try to fix common trailing commas and unescaped quotes.
            text = re.sub(r',\s*\}', '}', text)
            text = re.sub(r',\s*\]', ']', text)
            try:
                outline_data = json.loads(text)
            except:
                # If it still fails, let's try one more thing: 
                # Replace "plot_action": "..." with something safer if we can find it
                raise json_err

        title = outline_data.get("title", "Eine neue Geschichte")
        synopsis = outline_data.get("synopsis", "Kurzgeschichte")
        segments = outline_data.get("segments", [])

        if on_progress:
            await on_progress("outline_done", "Planung abgeschlossen", 5, title=title, synopsis=synopsis)
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
            await on_progress("text_chapter_done", f"Teil {i+1}/{num_segments} geschrieben", pct)
            
        # Context is the entire story text generated so far to maintain consistency
        if full_chapters:
            previous_text = "\n\n".join([c['text'] for c in full_chapters])
            context = f"Bisheriger Verlauf der Geschichte:\n{previous_text}"
        else:
            context = "Dies ist der Beginn der Geschichte."
        
        is_last_chapter = (i == num_segments - 1)
        
        if is_last_chapter:
            ende_regel = f"5. UMFANG & ENDE: Ziele auf ca. {words_per_segment} Wörter ab. DIES IST DAS FINALE KAPITEL! Führe die Geschichte zwingend zu einem runden, atmosphärischen Abschluss. Schließe die Handlung ab. Kein Cliffhanger mehr!"
        else:
            ende_regel = f"5. UMFANG & ENDE: Ziele auf ca. {words_per_segment} Wörter ab. WICHTIG: Beende das Kapitel NIEMALS mitten in einem Satz. Führe die Szene logisch zu Ende oder erzeuge einen weichen Übergang/Cliffhanger."
        
        # For improvements, provide the original chapter text if available
        original_segment_context = ""
        if remix_type == "improvement" and parent_text and "chapters" in parent_text:
            if i < len(parent_text["chapters"]):
                original_segment_context = f"\nURSPRÜNGLICHER TEXT DIESES KAPITELS:\n{parent_text['chapters'][i]['text']}\n"

        write_prompt = f"""Schreibe das nächste chronologische Kapitel der Geschichte.

STRIKTE REGELN:
1. NATÜRLICHER RHYTHMUS: Achte auf einen abwechslungsreichen Satzbau. Nutze sowohl kurze, prägnante Aussagen als auch elegante Nebensätze, um einen flüssigen Leserythmus zu erzeugen. Ideal für Audio/TTS, um Monotonie zu vermeiden. Vermeide jedoch extrem überladene Schachtelsätze.
2. Stil-Inspiration:
{selected_style_info}
Vermeide jegliche Floskeln, pädagogische Zeigefinger oder moralische Zusammenfassungen am Ende. Kein Kitsch, keine Moral!
3. Show, don't tell: Erkläre nicht, wie sich Charaktere fühlen – zeige es durch ihre Handlungen und Reaktionen.
4. Pacing & Detail: Beschreibe präzise und atmosphärisch. Behandle diesen Abschnitt mit der Tiefe eines Romans. Springe nicht zu schnell in der Handlung voran.
5. VERMEIDE ÜBEREILTE ENDEN: Hetze nicht zum Schluss. Vermeide Floskeln wie "Und so lernten sie..." oder "Am Ende war alles...". Bleib im Moment der Szene.
6. Format: Keinerlei Überschriften, Kapitelnummern oder Titel im generierten Text! Nur der reine, fließende Erzähltext.
7. FORTSCHRITT STATT WIEDERHOLUNG: Wiederhole niemals Phrasen, Metaphern oder innere Monologe aus den vorherigen Kapiteln. Fasse das Bisherige nicht zusammen. Die Handlung MUSS aktiv voranschreiten. Bringe ununterbrochen neue, frische Details ein.
{f"SPEZIELLE REMIX-ANWEISUNG: {further_instructions}" if further_instructions else ""}
{original_segment_context}
{ende_regel}

Rahmenbedingungen:
Titel der Gesamtgeschichte: {title}
Zusammenfassung der Geschichte: {synopsis}
Vorgaben für DIESES Kapitel:
- Kernhandlung (Plot): {seg.get('plot_action', seg.get('goal', ''))}
- Ort (Setting): {seg.get('setting', 'Aus dem Kontext ableiten')}
- Emotionale Entwicklung: {seg.get('emotional_shift', 'Neutral')}
- Ziel für das Kapitelende: {seg.get('ending_note', 'Logisch abschließen')}
{context}
"""
        if not rate_limiter.has_daily_quota("text"):
            raise RuntimeError("Das Tageslimit für KI-Generierungen wurde während der Geschichte erreicht.")
            
        # Get current model from DB or fallback to config
        text_model = store.get_system_setting("gemini_text_model", settings.GEMINI_TEXT_MODEL)
        logger.info(f"Writing chapter {i+1} with model: {text_model}")

        response_text = await generate_text(
            prompt=write_prompt,
            model=text_model,
            temperature=0.8,
            max_tokens=8192,
            presence_penalty=0.1,
            frequency_penalty=0.3
        )
        rate_limiter.increment_daily_quota()
        segment_text = response_text.strip()
        
        full_chapters.append({
            "title": "",
            "text": segment_text
        })

    return {
        "title": title,
        "synopsis": synopsis,
        "chapters": full_chapters
    }

async def generate_post_story_analysis(title: str, chapters: list[dict]) -> dict:
    """Analyze the full story text to create a refined synopsis and extract highlights."""
    full_text = "\n\n".join([c.get("text", "") for c in chapters])
    
    prompt = f"""Du bist ein preisgekrönter Lektor und Literaturkritiker. Deine Aufgabe ist es, eine abgeschlossene Kurzgeschichte zu analysieren.

GESCHICHTE:
Titel: {title}
Text:
{full_text[:6000]} # Limit to stay within context if story is very long

AUFGABE:
1. Erstelle eine neue, "punchy" Zusammenfassung der Geschichte (max. 3-4 Sätze). Sie soll atmosphärisch sein und Lust auf das Lesen machen, ohne zu viel zu verraten (keine Spoiler der Auflösung).
2. Extrahiere die 2-3 besten "Punchlines" oder Highlights aus dem Text. Das können besonders witzige, tiefsinnige oder atmosphärische Sätze sein.

Antworte EXKLUSIV im JSON-Format:
{{
    "refined_synopsis": "Die neue Zusammenfassung...",
    "highlights": "Highlight 1 • Highlight 2 • Highlight 3"
}}"""

    try:
        await rate_limiter.wait_for_capacity("text")
        text_model = store.get_system_setting("gemini_text_model", settings.GEMINI_TEXT_MODEL)
        
        response_text = await generate_text(
            prompt=prompt,
            model=text_model,
            temperature=0.7,
            max_tokens=1000,
            response_mime_type="application/json",
            response_schema=PostStoryAnalysisSchema
        )
        rate_limiter.increment_daily_quota("text")
        
        text = response_text.strip()
        
        # Robust JSON extraction
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        else:
            if text.startswith("```json"):
                text = text.replace("```json", "", 1).replace("```", "", 1).strip()
            elif text.startswith("```"):
                text = text.replace("```", "", 2).strip()
                
        data = json.loads(text)
        return {
            "synopsis": data.get("refined_synopsis", ""),
            "highlights": data.get("highlights", "")
        }
    except Exception as e:
        logger.error(f"Post-story analysis failed: {e}")
        return {
            "synopsis": "",
            "highlights": ""
        }
