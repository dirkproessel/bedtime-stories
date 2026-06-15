"""
Genre-specific profiles for Pro Mode book generation.
Each profile contains tropes, structural hints, POV settings, 
emotional arc templates and style guidance for a specific genre.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class GenreProfile(BaseModel):
    """Configuration profile for a literary genre."""
    id: str
    name: str
    description: str
    
    # Tropes – wählbare narrative Bausteine
    available_tropes: list[dict]  # [{id, name, description}]
    
    # POV-Optionen
    pov_options: list[dict]       # [{id, name, description}]
    default_pov: str
    
    # Spice-Level (nur für Romance-Genres relevant)
    has_spice_levels: bool = False
    spice_descriptions: dict = {}  # {1: "...", 2: "...", ...}
    
    # Strukturelle Empfehlungen
    recommended_chapter_count: tuple = (8, 16)
    recommended_words_per_chapter: tuple = (2000, 3000)
    
    # Emotional Arc Vorlage
    emotional_arc_template: str = ""
    
    # Stil-Hinweise für die KI
    style_hints: list[str] = []
    
    # Kapitelende-Strategie
    chapter_ending_strategy: str = "varied"  # "cliffhanger", "resolution", "varied"


GENRE_PROFILES: Dict[str, GenreProfile] = {
    "Dark Romance": GenreProfile(
        id="dark_romance",
        name="Dark Romance",
        description="Intensive, emotionale Liebesgeschichte mit dunklen Themen und moralisch grauen Charakteren",
        available_tropes=[
            {"id": "enemies_to_lovers", "name": "Enemies to Lovers", "description": "Vom Hass zur Leidenschaft"},
            {"id": "forced_proximity", "name": "Forced Proximity", "description": "Erzwungene Nähe schafft Spannung"},
            {"id": "morally_grey", "name": "Morally Grey Hero", "description": "Protagonist mit dunkler Seite"},
            {"id": "possessive", "name": "Possessive Love Interest", "description": "Besitzergreifende, intensive Zuneigung"},
            {"id": "forbidden", "name": "Forbidden Love", "description": "Verbotene, tabuisierte Beziehung"},
            {"id": "power_imbalance", "name": "Power Imbalance", "description": "Machtgefälle zwischen den Liebenden"},
            {"id": "redemption_arc", "name": "Redemption Arc", "description": "Erlösung durch die Liebe"},
            {"id": "second_chance", "name": "Second Chance", "description": "Zweite Chance nach Trennung/Verrat"},
            {"id": "secret_identity", "name": "Secret Identity", "description": "Verborgene Identität oder Vergangenheit"},
            {"id": "captive", "name": "Captive Romance", "description": "Gefangenschaft als Katalysator"},
        ],
        pov_options=[
            {"id": "single_female", "name": "Single POV (Sie)", "description": "Nur aus ihrer Perspektive"},
            {"id": "single_male", "name": "Single POV (Er)", "description": "Nur aus seiner Perspektive"},
            {"id": "dual_alternating", "name": "Dual POV (Abwechselnd)", "description": "Kapitelweise wechselnde Perspektive"},
            {"id": "dual_split", "name": "Dual POV (Geteilt)", "description": "Innerhalb der Kapitel wechselnd"},
        ],
        default_pov="dual_alternating",
        has_spice_levels=True,
        spice_descriptions={
            1: "Clean/Sweet: Keine expliziten Szenen. Emotionale Spannung, Küsse, Andeutungen. Blende vor intimen Momenten.",
            2: "Mild: Sinnliche Szenen werden angedeutet, aber nicht ausführlich beschrieben. Fokus auf Emotionen und Atmosphäre.",
            3: "Moderat: Intime Szenen werden beschrieben, aber mit Fokus auf Emotionen und Sensorik statt expliziter Anatomie. Metaphorisch, ästhetisch.",
            4: "Steamy: Ausführliche, leidenschaftliche Szenen mit sinnlichen Details. Expliziter als Stufe 3, aber immer mit emotionaler Tiefe.",
            5: "Explicit: Sehr detaillierte, ungehemmte Darstellung. Physische Details stehen gleichberechtigt neben den Emotionen.",
        },
        recommended_chapter_count=(18, 24),
        recommended_words_per_chapter=(2500, 3500),
        emotional_arc_template="Distanz/Feindseligkeit → Neugier/Anziehung → Push-Pull/Konfrontation → Emotionale Verwundbarkeit → Dunkler Moment/Krise → Kapitulation/Hingabe → Resolution/HEA",
        style_hints=[
            "Intensive innere Monologe, die den inneren Konflikt der Protagonisten zeigen",
            "Sensorische Beschreibungen: Geruch, Berührung, Hitze, Herzschlag",
            "Kurze, atemlose Sätze bei emotionalen Höhepunkten",
            "Langsamer Aufbau (Slow Burn) mit explosiven Wendepunkten",
            "Subtexte und unausgesprochene Worte zwischen den Figuren",
            "Düstere, atmosphärische Settings (Regen, Nacht, enge Räume)",
            "Machtdynamiken in Dialogen sichtbar machen",
            "Cliffhanger an Kapitelenden, die zum Weiterlesen zwingen",
        ],
        chapter_ending_strategy="cliffhanger"
    ),
    
    "Sinnliche Romanze": GenreProfile(
        id="sinnliche_romanze",
        name="Sinnliche Romanze",
        description="Gefühlvolle, langsam aufbauende Liebesgeschichte mit knisternder Spannung",
        available_tropes=[
            {"id": "slow_burn", "name": "Slow Burn", "description": "Langsamer, qualvoller Aufbau der Anziehung"},
            {"id": "friends_to_lovers", "name": "Friends to Lovers", "description": "Von Freundschaft zu mehr"},
            {"id": "fake_dating", "name": "Fake Dating", "description": "Vorgetäuschte Beziehung wird real"},
            {"id": "only_one_bed", "name": "Only One Bed", "description": "Erzwungene Nähe durch die Umstände"},
            {"id": "grumpy_sunshine", "name": "Grumpy × Sunshine", "description": "Gegensätze ziehen sich an"},
            {"id": "small_town", "name": "Small Town Romance", "description": "Kleinstadt-Setting mit Gemeinschaft"},
            {"id": "second_chance", "name": "Second Chance", "description": "Zweite Chance nach Trennung"},
            {"id": "holiday_romance", "name": "Holiday Romance", "description": "Urlaubsromanze mit Ablaufdatum"},
        ],
        pov_options=[
            {"id": "single_female", "name": "Single POV (Sie)", "description": "Aus ihrer Perspektive"},
            {"id": "dual_alternating", "name": "Dual POV", "description": "Kapitelweise wechselnd"},
        ],
        default_pov="single_female",
        has_spice_levels=True,
        spice_descriptions={
            1: "Clean: Küsse und Händchenhalten. Emotionale Tiefe statt physischer Nähe.",
            2: "Sweet: Zärtliche, romantische Szenen. Andeutungen, aber keine explizite Darstellung.",
            3: "Sensual: Sinnliche Szenen mit Fokus auf Gefühle und Atmosphäre. Metaphorisch und ästhetisch.",
            4: "Steamy: Detailliertere intime Szenen, aber immer mit emotionalem Kontext.",
            5: "Hot: Ausführliche Liebesszenen als integraler Handlungsteil.",
        },
        recommended_chapter_count=(12, 18),
        recommended_words_per_chapter=(2000, 2500),
        emotional_arc_template="Begegnung → Funken/Anziehung → Annäherung → Erstes Hindernis → Vertiefung → Krise → Happy End",
        style_hints=[
            "Zarte, poetische Sprache bei romantischen Szenen",
            "Detaillierte Beschreibung von Blicken, Berührungen, Gesten",
            "Innere Monologe with Herzklopfen-Metaphorik",
            "Humor und Leichtigkeit in der Alltagswelt der Figuren",
            "Atmosphärische Naturbeschreibungen als Spiegel der Gefühle",
        ],
        chapter_ending_strategy="varied"
    ),
    
    "Erotik": GenreProfile(
        id="erotik",
        name="Erotik",
        description="Ästhetische, leidenschaftliche Erkundung von Verlangen und Intimität",
        available_tropes=[
            {"id": "teacher_student", "name": "Mentor/Schüler", "description": "Wissens- und Erfahrungsgefälle"},
            {"id": "boss_employee", "name": "Chef/Angestellte", "description": "Professionelle Grenzen verschwimmen"},
            {"id": "strangers", "name": "Fremde", "description": "Intensive Begegnung ohne Vorgeschichte"},
            {"id": "reunited", "name": "Wiedersehen", "description": "Alte Flamme, neues Feuer"},
            {"id": "forbidden", "name": "Verbotene Frucht", "description": "Tabubruch als Reiz"},
            {"id": "awakening", "name": "Erwachen", "description": "Entdeckung der eigenen Lust"},
        ],
        pov_options=[
            {"id": "single_female", "name": "Single POV (Sie)", "description": "Intime weibliche Perspektive"},
            {"id": "single_male", "name": "Single POV (Er)", "description": "Intime männliche Perspektive"},
            {"id": "dual_alternating", "name": "Dual POV", "description": "Beide Perspektiven erleben"},
        ],
        default_pov="single_female",
        has_spice_levels=True,
        spice_descriptions={
            3: "Ästhetisch: Kunstvolle, metaphorische Darstellung. Mehr Atmosphäre als Explizitheit.",
            4: "Leidenschaftlich: Detailliert und sinnlich. Körperlichkeit als Ausdruck von Emotionen.",
            5: "Ungehemmt: Sehr explizit und detailliert. Keine stilistischen Einschränkungen.",
        },
        recommended_chapter_count=(8, 14),
        recommended_words_per_chapter=(2000, 3000),
        emotional_arc_template="Verlangen/Neugier → Annäherung → Erste Begegnung → Vertiefung → Erkundung → Höhepunkt → Reflexion",
        style_hints=[
            "Sinnliche Sprache mit allen fünf Sinnen",
            "Rhythmischer Satzbau: langsam aufbauend, dann drängend",
            "Metaphern aus Natur und Elementen (Feuer, Wasser, Sturm)",
            "Innerliche Spannung zwischen Verlangen und Zurückhaltung",
        ],
        chapter_ending_strategy="varied"
    ),
    
    "Thriller": GenreProfile(
        id="thriller",
        name="Thriller",
        description="Hochspannung, Bedrohung und atemlose Wendungen",
        available_tropes=[
            {"id": "ticking_clock", "name": "Tickende Uhr", "description": "Zeitdruck als Spannungstreiber"},
            {"id": "unreliable_narrator", "name": "Unzuverlässiger Erzähler", "description": "Dem Erzähler kann man nicht trauen"},
            {"id": "conspiracy", "name": "Verschwörung", "description": "Verborgene Mächte im Hintergrund"},
            {"id": "cat_and_mouse", "name": "Katz und Maus", "description": "Jäger und Gejagter"},
            {"id": "identity_crisis", "name": "Identitätskrise", "description": "Wer bin ich wirklich?"},
            {"id": "locked_room", "name": "Geschlossener Raum", "description": "Begrenzter Schauplatz, maximaler Druck"},
            {"id": "double_cross", "name": "Doppeltes Spiel", "description": "Verrat aus den eigenen Reihen"},
            {"id": "missing_person", "name": "Vermisst", "description": "Suche nach einer verschwundenen Person"},
        ],
        pov_options=[
            {"id": "single_protagonist", "name": "Single POV (Protagonist)", "description": "Leser weiß nur, was der Held weiß"},
            {"id": "multiple", "name": "Multiple POV", "description": "Verschiedene Perspektiven"},
            {"id": "antagonist_glimpses", "name": "Antagonist-Einblicke", "description": "Gelegentlich Sicht des Gegners"},
        ],
        default_pov="single_protagonist",
        recommended_chapter_count=(16, 24),
        recommended_words_per_chapter=(1800, 2500),
        emotional_arc_template="Normalität → Auslöser → Eskalation → Wendepunkt → Jagd → Konfrontation → Auflösung",
        style_hints=[
            "Kurze Kapitel, die zum Weiterblättern zwingen",
            "Cliffhanger an jedem Kapitelende",
            "Sensorische Details bei Verfolgungsjagden und Bedrohungen",
            "Innerer Monolog unter Stress: fragmentiert, atemlos",
            "Red Herrings (falsche Fährten) einbauen",
            "Pacing: Ruhige Momente als Kontrastmittel zur Hochspannung",
        ],
        chapter_ending_strategy="cliffhanger"
    ),
    
    "Fantasy": GenreProfile(
        id="fantasy",
        name="Fantasy",
        description="Epische Welten, Magie-Systeme und heldenhafte Quests",
        available_tropes=[
            {"id": "chosen_one", "name": "Der Auserwählte", "description": "Schicksal ruft den unerwarteten Helden"},
            {"id": "found_family", "name": "Found Family", "description": "Zusammengewürfelte Gruppe wird Familie"},
            {"id": "magic_system", "name": "Magiesystem", "description": "Klare Regeln für übernatürliche Kräfte"},
            {"id": "dark_lord", "name": "Der dunkle Lord", "description": "Übermächtiger Antagonist"},
            {"id": "quest", "name": "Die große Suche", "description": "Reise zu einem wichtigen Ziel/Artefakt"},
            {"id": "prophecy", "name": "Prophezeiung", "description": "Altes Schicksal bestimmt den Weg"},
            {"id": "mentor", "name": "Der Mentor", "description": "Weiser Lehrer führt den Helden"},
            {"id": "hidden_heritage", "name": "Verborgenes Erbe", "description": "Protagonist entdeckt seine wahre Herkunft"},
        ],
        pov_options=[
            {"id": "single_hero", "name": "Single POV (Held)", "description": "Durch die Augen des Helden"},
            {"id": "multiple", "name": "Multiple POV", "description": "Mehrere Perspektiven der Gefährten"},
            {"id": "omniscient", "name": "Allwissend", "description": "Auktorialer Erzähler über allen Figuren"},
        ],
        default_pov="single_hero",
        recommended_chapter_count=(16, 24),
        recommended_words_per_chapter=(2500, 3500),
        emotional_arc_template="Ruf des Abenteuers → Weigerung → Mentor → Schwellenübertritt → Prüfungen → Tiefster Punkt → Belohnung → Rückkehr",
        style_hints=[
            "Lebendiges Worldbuilding mit allen Sinnen",
            "Eigenständige Begriffe für Magie und Kulturen",
            "Epische Schlachtszenen mit klarer Choreografie",
            "Ruhige Lagerfeuer-Momente für Charaktertiefe",
            "Naturbilder, die die Stimmung spiegeln",
        ],
        chapter_ending_strategy="varied"
    ),
    
    "Krimi": GenreProfile(
        id="krimi",
        name="Krimi",
        description="Rätsel, Ermittlung, falsche Fährten und die Suche nach Wahrheit",
        available_tropes=[
            {"id": "whodunnit", "name": "Whodunnit", "description": "Klassisches Rätsel: Wer war es?"},
            {"id": "locked_room", "name": "Locked Room Mystery", "description": "Unmögliches Verbrechen"},
            {"id": "cold_case", "name": "Cold Case", "description": "Alter, ungelöster Fall"},
            {"id": "amateur_detective", "name": "Amateur-Detektiv", "description": "Laie ermittelt"},
            {"id": "police_procedural", "name": "Polizeiarbeit", "description": "Realistische Ermittlung"},
            {"id": "cozy_mystery", "name": "Cozy Mystery", "description": "Gemütlich-skurrile Ermittlung"},
        ],
        pov_options=[
            {"id": "detective", "name": "Detektiv-POV", "description": "Aus Sicht des Ermittlers"},
            {"id": "multiple", "name": "Multiple POV", "description": "Verschiedene Verdächtige"},
        ],
        default_pov="detective",
        recommended_chapter_count=(12, 20),
        recommended_words_per_chapter=(2000, 2500),
        emotional_arc_template="Tatort/Fund → Verdächtige → Ermittlung → Falsche Fährte → Wendung → Konfrontation → Auflösung",
        style_hints=[
            "Detaillierte Umgebungsbeschreibungen als Hinweisgeber",
            "Subtile Hinweise (Chekhov's Gun) in jeder Szene",
            "Verhöre als spannungsgeladene Dialogszenen",
            "Innere Logik: Jeder Hinweis muss fair spielen",
        ],
        chapter_ending_strategy="cliffhanger"
    ),
}

# Fallback-Profil für Genres ohne spezifisches Profil
DEFAULT_PROFILE = GenreProfile(
    id="default",
    name="Standard",
    description="Allgemeines Genre ohne spezifische Vorgaben",
    available_tropes=[],
    pov_options=[
        {"id": "single", "name": "Single POV", "description": "Eine Erzählperspektive"},
        {"id": "multiple", "name": "Multiple POV", "description": "Mehrere Perspektiven"},
        {"id": "omniscient", "name": "Allwissend", "description": "Auktorialer Erzähler"},
    ],
    default_pov="single",
    recommended_chapter_count=(8, 16),
    recommended_words_per_chapter=(2000, 2500),
    emotional_arc_template="",
    style_hints=[],
    chapter_ending_strategy="varied"
)

def get_genre_profile(genre: str) -> GenreProfile:
    """Get the genre profile for a given genre name, or default."""
    # Check case-insensitive match or direct dictionary key
    for name, profile in GENRE_PROFILES.items():
        if name.lower() == genre.lower():
            return profile
    return DEFAULT_PROFILE

def build_genre_prompt_section(
    genre: str,
    selected_tropes: list[str] = None,
    pov: str = None,
    spice_level: int = None,
) -> str:
    """Build the genre-specific section of the writing prompt."""
    profile = get_genre_profile(genre)
    sections = []
    
    # Genre-Grundinfo
    sections.append(f"Genre: {profile.name} – {profile.description}")
    
    # Emotional Arc
    if profile.emotional_arc_template:
        sections.append(f"Emotionaler Bogen des gesamten Buches:\n{profile.emotional_arc_template}")
    
    # Tropes
    if selected_tropes:
        trope_map = {t["id"]: t for t in profile.available_tropes}
        active = [trope_map[tid] for tid in selected_tropes if tid in trope_map]
        if active:
            trope_str = "\n".join([f"- {t['name']}: {t['description']}" for t in active])
            sections.append(f"Aktive Tropes (diese narrativen Elemente MÜSSEN im Buch vorkommen):\n{trope_str}")
    
    # POV
    if pov:
        pov_map = {p["id"]: p for p in profile.pov_options}
        if pov in pov_map:
            pov_info = pov_map[pov]
            pov_instruction = f"Erzählperspektive: {pov_info['name']} – {pov_info['description']}"
            if pov == "dual_alternating":
                pov_instruction += "\nWICHTIG: Wechsle die Erzählperspektive kapitelweise ab. Kapitel 1 = Sie (weiblicher Hauptcharakter), Kapitel 2 = Er (männlicher Hauptcharakter), usw."
            sections.append(pov_instruction)
    
    # Spice Level
    if profile.has_spice_levels and spice_level:
        spice_desc = profile.spice_descriptions.get(spice_level, "")
        if spice_desc:
            sections.append(f"Intimitäts-Level ({spice_level}/5): {spice_desc}")
    
    # Style Hints
    if profile.style_hints:
        hints_str = "\n".join([f"- {h}" for h in profile.style_hints])
        sections.append(f"Genre-spezifische Stil-Anweisungen:\n{hints_str}")
    
    # Chapter Ending Strategy
    if profile.chapter_ending_strategy == "cliffhanger":
        sections.append("Kapitelenden: Beende JEDES Kapitel mit einem Cliffhanger oder einer offenen Frage, die zum Weiterlesen zwingt.")
    
    return "\n\n".join(sections)
