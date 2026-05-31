"""
Text-to-Speech service supporting Edge TTS and Google Cloud TTS.
Generates MP3 chunks per chapter.
"""

import edge_tts
import random
import asyncio
from pathlib import Path
from app.config import settings
from app.services.rate_limiter import rate_limiter
from sqlmodel import Session, select
from app.database import engine as db_engine
from app.models import User

# Available Edge TTS German voices (Simplified)
EDGE_VOICES = {
    "seraphina": {"id": "de-DE-SeraphinaMultilingualNeural", "name": "Seraphina", "gender": "female", "description": "Warm & melodisch"},
    "florian": {"id": "de-DE-FlorianMultilingualNeural", "name": "Florian", "gender": "male", "description": "Klar & natürlich"},
}

# Google Cloud TTS Neural2 voices (Temporarily Disabled)
# GOOGLE_VOICES = {
#     "eliza": {"id": "de-DE-Neural2-G", "name": "Eliza", "gender": "female"},
#     "percy": {"id": "de-DE-Neural2-H", "name": "Percy", "gender": "male"},
# }

# OpenAI TTS voices
OPENAI_VOICES = {
    # "shimmer": {"id": "shimmer", "name": "Shimmer", "gender": "female"},
    # "onyx": {"id": "onyx", "name": "Onyx", "gender": "male"},
    # "alloy": {"id": "alloy", "name": "Alloy", "gender": "neutral"},
    # "echo": {"id": "echo", "name": "Echo", "gender": "male"},
    # "fable": {"id": "fable", "name": "Fable", "gender": "neutral"},
    # "nova": {"id": "nova", "name": "Nova", "gender": "female"},
}

# Gemini TTS voices
GEMINI_VOICES = {
    # --- Standard / Top 8 ---
    "aoede":      {"id": "Aoede",      "name": "Aoede",      "gender": "female",  "description": "Leicht & klar"},
    "kore":       {"id": "Kore",       "name": "Kore",        "gender": "female",  "description": "Fest & energetisch"},
    "sulafat":    {"id": "Sulafat",    "name": "Sulafat",     "gender": "female",  "description": "Warm & überzeugend"},
    "gacrux":     {"id": "Gacrux",     "name": "Gacrux",      "gender": "male",    "description": "Tief & resonant"},
    "charon":     {"id": "Charon",     "name": "Charon",      "gender": "male",    "description": "Smooth & sachlich"},
    "fenrir":     {"id": "Fenrir",     "name": "Fenrir",      "gender": "male",    "description": "Warm & lebendig"},
    "orus":       {"id": "Orus",       "name": "Orus",        "gender": "male",    "description": "Fest & klar"},
    "zephyr":     {"id": "Zephyr",     "name": "Zephyr",      "gender": "neutral", "description": "Hell & frisch"},
    # --- Weitere 8 (Show More) ---
    "enceladus":  {"id": "Enceladus",  "name": "Enceladus",   "gender": "male",    "description": "Sanft & hauchend"},
    "puck":       {"id": "Puck",       "name": "Puck",        "gender": "male",    "description": "Aufgeweckt & lebhaft"},
    "schedar":    {"id": "Schedar",    "name": "Schedar",     "gender": "male",    "description": "Gleichmäßig & ruhig"},
    "iapetus":    {"id": "Iapetus",    "name": "Iapetus",     "gender": "male",    "description": "Bodenständig & klar"},
    "algenib":    {"id": "Algenib",    "name": "Algenib",     "gender": "female",  "description": "Rau & charakterstark"},
    "laomedeia":  {"id": "Laomedeia", "name": "Laomedeia",   "gender": "female",  "description": "Aufgeweckt & neugierig"},
    "despina":    {"id": "Despina",    "name": "Despina",     "gender": "female",  "description": "Sanft & fließend"},
    "umbriel":    {"id": "Umbriel",    "name": "Umbriel",     "gender": "neutral", "description": "Entspannt & vielseitig"},
}# Fish Audio (Cloned Voices)
FISH_VOICES = {
    "jenny": {"id": "cb55f2fc1a144c74b70ea7fdeb6b9f95", "name": "Jenny", "gender": "female", "description": "Freundlich & entspannt"},
    "christoph": {"id": "3ee58b7440a04e468868eab1a7fff651", "name": "Christoph Maria Herbst", "gender": "male", "description": "Ironisch & charakterstark"},
    "katharina": {"id": "53c3de1d063f4ce4a027eab5497b2f11", "name": "Katharina Thalbach", "gender": "female", "description": "Knorrig & ausdrucksstark"},
}

# xAI Grok TTS voices
# Native German voices (language=de)
XAI_VOICES = {
    "xai_clara":  {"id": "458705c07139", "name": "Clara (xAI)",  "gender": "female", "language": "de", "description": "Klar & natürlich"},
    "xai_moritz": {"id": "41321eb41295", "name": "Moritz (xAI)", "gender": "male",   "language": "de", "description": "Freundlich & markant"},
    "xai_niklas": {"id": "40f31906b23d", "name": "Niklas (xAI)", "gender": "male",   "language": "de", "description": "Jung & engagiert"},
    "xai_lena":   {"id": "3a7889066fa2", "name": "Lena (xAI)",   "gender": "female", "language": "de", "description": "Ausdrucksstark & warm"},
}


# 1a. Voice Basis-Regieanweisungen (User-Defined)
VOICE_INSTRUCTIONS = {
    "aoede": "„Du bist eine Frau mit einer hellen, klaren und einladenden Stimme. Deine Ausstrahlung ist freundlich und neugierig.“",
    "kore": "„Du bist eine Frau mit einer festen, souveränen und entschlossenen Stimme. Du klingst kompetent und direkt.“",
    "sulafat": "„Du bist eine Frau mit einer warmen, mütterlichen und sanften Grundstimme. Du klingst vertrauenserweckend und fürsorglich.“",
    "gacrux": "„Du bist ein Mann mit einer tiefen, voluminösen Resonanz. Deine Stimme ist kraftvoll und autoritär.“",
    "charon": "„Du bist ein sachlicher, distanzierter Beobachter. Deine Stimme ist neutral, ruhig und ohne emotionale Schwankungen.“",
    "fenrir": "„Du bist ein Mann mit einer energiegeladenen, begeisterungsfähigen Stimme. Deine Ausstrahlung ist herzlich und lebendig.“",
    "orus": "„Du bist ein Mann mit einer ernsten, festen und seriösen Stimme. Du sprichst direkt und ohne Schnörkel.“",
    "zephyr": "„Deine Stimme ist frisch, modern und hat eine jugendliche Leichtigkeit. Du klingst wie ein aufgeweckter Erzähler von heute.“",
    "enceladus": "„Deine Stimme ist extrem sanft, leise und hat einen hohen Luftanteil (hauchend). Du erzeugst eine starke Intimität.“",
    "puck": "„Deine Stimme ist quirlig, verspielt und voller Tatendrang. Du klingst wie ein flinker, lebhafter Charakter.“",
    "schedar": "„Deine Stimme ist vollkommen unaufgeregt, entspannt und stetig. Du strahlst souveräne Gelassenheit aus.“",
    "iapetus": "„Du bist ein bodenständiger Erzähler mit einer ehrlichen, direkten Alltagsstimme. Du klingst wie ein ganz normaler Mensch im Gespräch.“",
    "algenib": "„Deine Stimme hat eine raue, markante Textur. Du klingst charakterstark, tief und kantig.“",
    "laomedeia": "„Deine Stimme ist neugierig, aktiv und präsent. Du klingst stets wach und interessiert an der Geschichte.“",
    "despina": "„Du hast eine kultivierte, elegante und gehobene Stimme. Deine Ausstrahlung ist aristokratisch und fließend.“",
    "umbriel": "„Deine Stimme ist locker, unkompliziert und flexibel. Du klingst wie jemand, der eine Geschichte ganz entspannt nebenbei erzählt.“",
    "jenny": "„Du bist eine Frau mit einer freundlichen und entspannten Stimme. Du klingst herzlich und gelassen.“",
    "christoph": "„Du bist ein männlicher Erzähler mit einer ironischen, charakterstarken und pointierten Ausdrucksweise. Du sprichst deutlich und lebendig.“",
    "katharina": "„Du bist eine weibliche Erzählerin mit einer knorrigen, sehr ausdrucksstarken und lebhaften Stimme. Du betonst theatralisch und intensiv.“",
    # xAI voices - kein system-prompt-Konzept fur TTS
    "xai_clara":  "",
    "xai_moritz": "",
    "xai_niklas": "",
    "xai_lena":   "",
}

# 1b. Genre Tweaks (User-Defined)
GENRE_INSTRUCTIONS = {
    "Krimi": "„Erzähle analytisch und trocken. Achte auf eine scharfe Artikulation der Konsonanten, um Spannung zu erzeugen.“",
    "Abenteuer": "„Erzähle mit viel Energie. Nutze einen lebendigen, dynamischen Rhythmus.“",
    "Science-Fiction": "„Lies mit kühler Präzision. Deine Artikulation ist extrem sauber und technisch-distanziert.“",
    "Märchen": "„Nutze einen weiten Melodiebogen. Erzähle warm und geborgen mit sanften, fließenden Übergängen (Legato).“",
    "Komödie": "„Sprich dynamisch mit hoher Varianz in der Tonhöhe. Nutze präzise Pausen für Pointen. Sei lebhaft und präsent.“",
    "Thriller": "„Erzähle mit akustischem Druck und hoher innerer Spannung. Nutze eine intensive Artikulation.“",
    "Drama": "„Lass die Stimme am Satzende schwer absinken. Erzähle mit einer melancholischen Resonanz.“",
    "Grusel": "„Erzähle leise und hauchend. Betone die unheimliche Atmosphäre durch eine scharfe Artikulation der Wisper-Laute.“",
    "Fantasy": "„Sprich erhaben und mit viel Volumen. Nutze einen feierlichen, stetigen Rhythmus.“",
    "Satire": "„Erzähle mit einem spöttischen, bewusst arroganten Unterton. Nutze eine scharfe Artikulation. Betone Pointen trocken und präzise.“",
    "Dystopie": "„Erzähle flach und hoffnungslos. Reduziere die Dynamik und Melodie auf ein Minimum.“",
    "Historisch": "„Sprich mit aristokratischer Ruhe und perfekter Artikulation. Nutze einen würdevollen, gleichmäßigen Rhythmus.“",
    "Mythologie": "„Lies wie ein Orakel: Gewichtig, bedeutungsvoll und mit großer Ernsthaftigkeit.“",
    "Roadtrip": "„Erzähle locker and beiläufig, wie in einem entspannten Gespräch. Nutze eine ganz natürliche Intonation.“",
    "Gute Nacht": "„Lies extrem leise, monoton und ohne Akzente. Werde zum Ende hin immer weicher. Minimale Energie.“",
    "Fabel": "„Sprich wie ein gütiger Lehrer. Betone die Lehrsätze am Ende deutlicher und mit mehr Gewicht.“",
    "Modern Romanze": "„Erzähle locker, urban und mit einem Lächeln in der Stimme. Nutze eine helle, moderne Satzmelodie.“",
    "Sinnliche Romanze": "„Sprich sehr nah am Mikrofon, tief und warm. Erzeuge Nähe durch sanfte, fließende Übergänge (Legato).“",
    "Erotik": "„Lies hauchig und mit vielen kleinen Atemphasen. Erzeuge eine vibrierende, knisternde Atmosphäre.“",
    "Dark Romance": "„Erzähle fordernd, intensiv und mit einer unterdrückten emotionalen schärfe.“",
}



# ── Text Chunking for Gemini TTS ──
MIN_CHUNK_BYTES = 700
MAX_CHUNK_BYTES = 1000

def split_text_paragraphs(t: str, min_bytes=MIN_CHUNK_BYTES, max_bytes=MAX_CHUNK_BYTES):
    """Split text into paragraph-aware chunks for Gemini TTS."""
    chunks = []
    current_chunk = ""
    
    paragraphs = [p.strip() for p in t.replace("\r\n", "\n").split("\n\n") if p.strip()]
    
    for p in paragraphs:
        p_bytes = len(p.encode("utf-8"))
        curr_bytes = len(current_chunk.encode("utf-8"))
        
        if p_bytes > max_bytes:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
                
            sentences = p.replace("\n", " ").split(". ")
            temp_chunk = ""
            for s in sentences:
                s = s.strip()
                if not s: continue
                s_mit_punkt = s + ". " if not s.endswith(".") else s + " "
                
                if len(temp_chunk.encode("utf-8")) + len(s_mit_punkt.encode("utf-8")) > max_bytes:
                    if temp_chunk:
                        chunks.append(temp_chunk.strip())
                    temp_chunk = s_mit_punkt
                else:
                    temp_chunk += s_mit_punkt
                    
            if temp_chunk:
                chunks.append(temp_chunk.strip())
            continue
            
        if curr_bytes + p_bytes <= max_bytes:
            current_chunk = current_chunk + "\n\n" + p if current_chunk else p
        else:
            if curr_bytes >= min_bytes:
                chunks.append(current_chunk.strip())
                current_chunk = p
            else:
                current_chunk = current_chunk + "\n\n" + p if current_chunk else p
                
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks


DEFAULT_VOICE = "seraphina"


def get_available_voices(user_id: str | None = None) -> list[dict]:
    """Return list of available voice profiles from the database."""
    voices = []
    
    try:
        from app.models import UserVoice, SystemVoice
        from sqlmodel import or_
        
        with Session(db_engine) as db_session:
            # 1. System Voices (only active ones)
            sys_query = select(SystemVoice).where(SystemVoice.is_active == True)
            sys_voices = db_session.exec(sys_query).all()
            
            for v in sys_voices:
                voices.append({
                    "key": v.id,
                    "name": v.name,
                    "gender": v.gender,
                    "engine": v.engine,
                    "description": v.description,
                })
            
            # 2. Cloned Voices (public or owned by user)
            clones_query = select(UserVoice).where(UserVoice.is_public == True)
            if user_id:
                clones_query = select(UserVoice).where(or_(UserVoice.is_public == True, UserVoice.user_id == user_id))
            
            db_voices = db_session.exec(clones_query).all()
            for v_obj in db_voices:
                # Avoid duplicates
                if any(vox["key"] == v_obj.id for vox in voices):
                    continue
                voices.append({
                    "key": v_obj.id,
                    "name": v_obj.name,
                    "gender": v_obj.gender or "neutral",
                    "engine": "fish",
                    "description": v_obj.description,
                })
                
        if not voices:
            # Table might be empty during first startup/seeding
            raise Exception("No voices found in DB, using fallback")

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Using hardcoded voice fallback: {e}")
        # Fallback to hardcoded lists if DB fails or is empty
        for key, v in EDGE_VOICES.items():
            voices.append({"key": key, "name": v["name"], "gender": v["gender"], "engine": "edge"})
        for key, v in GEMINI_VOICES.items():
            voices.append({"key": key, "name": v["name"], "gender": v["gender"], "engine": "gemini"})
        for key, v in FISH_VOICES.items():
            voices.append({"key": key, "name": v["name"], "gender": v["gender"], "engine": "fish"})

    # Virtual Voices (like 'none')
    voices.append({
        "key": "none",
        "name": "Keine Stimme (nur Text)",
        "gender": "neutral",
        "engine": "virtual",
    })

    return voices


import re

def strip_emotion_tags(text: str) -> str:
    """Remove bracketed emotion tags like [whispering] or [excited]."""
    text = re.sub(r'\[[^\]]+\]', '', text)
    # Remove XML-like emotion tags but keep their contents e.g. <whisper>text</whisper> -> text
    text = re.sub(r'<([^>|]+)>([\s\S]*?)<\/\1>', r'\2', text)
    text = re.sub(r'<[^>|]+>', '', text)
    return text

def strip_speaker_tags(text: str) -> str:
    """Remove speaker tags like <|speaker:0|>."""
    return re.sub(r'<\|speaker:\d+\|>', '', text)

def get_fish_voice_id(voice_key: str, user_id: str | None = None) -> str:
    """Resolve a voice key to the actual Fish voice ID string."""
    if voice_key in FISH_VOICES:
        return FISH_VOICES[voice_key]["id"]
    try:
        with Session(db_engine) as db_session:
            from app.models import UserVoice, SystemVoice
            vk_clean = str(voice_key).strip().lower()
            voice_obj = db_session.get(UserVoice, vk_clean)
            if not voice_obj and user_id:
                voice_obj = db_session.exec(
                    select(UserVoice).where(UserVoice.fish_voice_id == vk_clean)
                ).first()
            if voice_obj:
                return voice_obj.fish_voice_id
            sys_voice = db_session.get(SystemVoice, voice_key)
            if sys_voice and sys_voice.fish_voice_id:
                return sys_voice.fish_voice_id
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error resolving Fish ID: {e}")
    return voice_key

def get_multi_voice_refs(primary_voice_key: str, text: str, user_id: str | None = None, speaker_voices: dict[str, str] | None = None) -> list[str]:
    """Find unique speaker indices in text and map them to appropriate Fish voice IDs."""
    speaker_indices = [int(x) for x in re.findall(r'<\|speaker:(\d+)\|>', text)]
    if not speaker_indices:
        return [get_fish_voice_id((speaker_voices or {}).get("0", primary_voice_key), user_id)]
    max_speaker_idx = max(speaker_indices)
    
    primary_key = (speaker_voices or {}).get("0", primary_voice_key)
    primary_id = get_fish_voice_id(primary_key, user_id)
    ref_ids = [primary_id] * (max_speaker_idx + 1)
    
    # Resolve all other fish voices for fallback
    all_voices = get_available_voices(user_id=user_id)
    other_fish_voices = [
        v for v in all_voices 
        if v.get("engine") == "fish" and v.get("key") != primary_key and v.get("key") != "none"
    ]
    
    for idx in range(0, max_speaker_idx + 1):
        if speaker_voices and str(idx) in speaker_voices:
            chosen_key = speaker_voices[str(idx)]
            ref_ids[idx] = get_fish_voice_id(chosen_key, user_id)
        else:
            if idx == 0:
                ref_ids[idx] = primary_id
            else:
                if other_fish_voices:
                    chosen_voice = other_fish_voices[(idx - 1) % len(other_fish_voices)]
                    ref_ids[idx] = get_fish_voice_id(chosen_voice["key"], user_id)
                else:
                    ref_ids[idx] = primary_id

    # Enforce safety limit of at most 3 unique voice IDs to prevent "Reference audio too long"
    if len(set(ref_ids)) > 3:
        unique_ids = []
        mapped_ids = []
        for voice_id in ref_ids:
            if voice_id not in unique_ids:
                if len(unique_ids) < 3:
                    unique_ids.append(voice_id)
                    mapped_ids.append(voice_id)
                else:
                    fallback_idx = 1 if len(unique_ids) > 1 else 0
                    mapped_ids.append(unique_ids[fallback_idx])
            else:
                mapped_ids.append(voice_id)
        ref_ids = mapped_ids

    return ref_ids


_fish_semaphore = None

def get_fish_semaphore():
    global _fish_semaphore
    if _fish_semaphore is None:
        _fish_semaphore = asyncio.Semaphore(2)  # Limit concurrent Fish API calls to 2 to prevent 429
    return _fish_semaphore


async def generate_fish_audio(text: str, output_path: Path, reference_ids: list[str], use_s2_pro: bool = False):
    """Generate audio using Fish Audio API directly via httpx with retry and rate limiting."""
    import httpx
    import logging
    logger = logging.getLogger(__name__)

    headers = {
        "Authorization": f"Bearer {settings.FISH_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    if use_s2_pro:
        headers["model"] = "s2-pro"
    payload = {
        "text": text,
        "format": "mp3",
        "mp3_bitrate": 128,
    }
    if len(reference_ids) == 1:
        payload["reference_id"] = reference_ids[0]
    else:
        payload["reference_id"] = reference_ids

    max_retries = 5
    base_delay = 2.0

    async with get_fish_semaphore():
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream("POST", "https://api.fish.audio/v1/tts", headers=headers, json=payload) as response:
                        if response.status_code == 429:
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Fish API returned 429 Too Many Requests. Retrying in {delay:.1f}s (Attempt {attempt + 1}/{max_retries})...")
                            await asyncio.sleep(delay)
                            continue

                        try:
                            response.raise_for_status()
                        except httpx.HTTPStatusError as e:
                            try:
                                err_body = await response.aread()
                                logger.error(f"Fish API Error Details: {err_body.decode('utf-8', errors='ignore')}")
                            except Exception:
                                pass
                            
                            if attempt == max_retries - 1:
                                raise e
                            
                            delay = base_delay * (2 ** attempt)
                            logger.warning(f"Fish API error: {e}. Retrying in {delay:.1f}s...")
                            await asyncio.sleep(delay)
                            continue

                        with open(output_path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                f.write(chunk)
                        return # Success
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Network error or exception during Fish API call: {e}. Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)



async def generate_tts_chunk(
    text: str,
    output_path: Path,
    voice_key: str = DEFAULT_VOICE,
    rate: str = "0%",
    is_title: bool = False,
    genre: str | None = None,
    previous_text: str | None = None,
    on_chunk_progress: callable = None,
    direct_fish_id: str | None = None,
    multi_voice: bool = False,
    speaker_voices: dict[str, str] | None = None,
) -> tuple[Path, str]:
    """
    Convert text to speech and save as MP3.
    Supports Edge TTS, Google Cloud TTS, and OpenAI TTS.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Determine which engine to use
    if voice_key in OPENAI_VOICES:
        voice_config = OPENAI_VOICES[voice_key]
        engine = "openai"
    elif voice_key in XAI_VOICES:
        voice_config = XAI_VOICES[voice_key]
        engine = "xai"
    elif voice_key in FISH_VOICES:
        voice_config = FISH_VOICES[voice_key]
        engine = "fish"
    else:
        # Check if it's a dynamic Fish voice ID
        engine = "edge" # Fallback
        voice_config = None
        
        # Look up in DB if the key looks like a UUID (32+ chars)
        if direct_fish_id:
            voice_config = {"id": direct_fish_id, "name": "Custom", "gender": "neutral"}
            engine = "fish"
        elif len(voice_key) >= 30:
            try:
                from app.models import UserVoice
                with Session(db_engine) as db_session:
                    vk_clean = str(voice_key).strip().lower()
                    # It could be UserVoice.id or legacy fish_voice_id directly 
                    voice_obj = db_session.get(UserVoice, vk_clean) # Try primary key first
                    
                    if not voice_obj:
                        # Fallback try checking fish_voice_id or case-insensitive
                        voice_obj = db_session.exec(select(UserVoice).where(UserVoice.fish_voice_id == vk_clean)).first()
                    if not voice_obj:
                        voice_obj = db_session.exec(select(UserVoice).where(UserVoice.fish_voice_id == voice_key)).first()
                    if not voice_obj:
                        voice_obj = db_session.exec(select(UserVoice).where(UserVoice.id == voice_key)).first()
                        
                    if voice_obj:
                        engine = "fish"
                        voice_config = {"id": voice_obj.fish_voice_id}
                        logger.info(f"TTS: Found custom Fish voice {voice_config['id']} for user {voice_obj.user_id}")
                    else:
                        logger.debug(f"TTS: Key {voice_key} looks like UUID but no UserVoice found.")
            except Exception as e:
                logger.error(f"Error checking dynamic voice ID: {e}")

    # Check database for custom system voice if not hardcoded
    if voice_config is None:
        try:
            from app.models import SystemVoice
            with Session(db_engine) as db_session:
                sys_voice = db_session.get(SystemVoice, voice_key)
                if sys_voice and sys_voice.is_active:
                    engine = sys_voice.engine
                    voice_config = {
                        "id": sys_voice.fish_voice_id or sys_voice.id,
                        "name": sys_voice.name,
                        "gender": sys_voice.gender,
                        "description": sys_voice.description
                    }
                    logger.info(f"TTS: Found system voice {sys_voice.name} ({engine}) in DB.")
        except Exception as e:
            logger.error(f"Error checking SystemVoice from DB: {e}")

    # Final engine check if not found yet
    if voice_config is None:
        if voice_key in GEMINI_VOICES:
            if not rate_limiter.has_daily_quota("tts"):
                logger.warning(f"Rate Limiter: Daily Gemini quota reached (marked as exhausted). Falling back to Edge TTS for voice {voice_key}.")
                voice_config = EDGE_VOICES.get(DEFAULT_VOICE, EDGE_VOICES["seraphina"])
                engine = "edge"
            else:
                voice_config = GEMINI_VOICES[voice_key]
                engine = "gemini"
        else:
            # Check if it was supposed to be a Fish voice but we couldn't find it in DB
            if len(voice_key) >= 30:
                logger.warning(f"TTS: Voice key {voice_key} looks like a UUID but was not found in static FISH_VOICES or User DB. Falling back to {DEFAULT_VOICE}.")
            
            voice_config = EDGE_VOICES.get(voice_key, EDGE_VOICES[DEFAULT_VOICE])
            engine = "edge"

    logger.info(f"TTS: [Engine: {engine}] Voice: {voice_config.get('id', 'N/A')} (Key: {voice_key}) -> {output_path}")

    # Cleanup text: remove markdown formatting
    clean_text = text.replace("*", "").replace("_", "").replace("#", "")

    # Cleanup emotion and speaker tags based on engine support
    if engine not in ["fish", "xai"]:
        clean_text = strip_emotion_tags(clean_text)
    if engine != "fish" or not multi_voice:
        clean_text = strip_speaker_tags(clean_text)

    try:
        if engine == "edge":
            # Edge TTS (Free)
            edge_rate = rate
            if edge_rate and not (edge_rate.startswith("+") or edge_rate.startswith("-")):
                edge_rate = "+" + edge_rate
                
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=voice_config["id"],
                rate=edge_rate,
            )
            await communicate.save(str(output_path))
            return output_path, voice_key

        elif engine == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API Key is missing.")
            
            import httpx
            from pydub import AudioSegment
            import io

            def split_text_openai(t, max_bytes=2000):
                chunks = []
                current_chunk = ""
                sentences = t.replace("\n", " ").split(". ")
                for s in sentences:
                    test_chunk = (current_chunk + ". " + s).strip() if current_chunk else s
                    if len(test_chunk.encode("utf-8")) > max_bytes:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = s
                    else:
                        current_chunk = test_chunk
                if current_chunk:
                    chunks.append(current_chunk)
                return chunks

            text_chunks = split_text_openai(clean_text)
            speed = 0.85 if "-15%" in rate else (0.95 if "-5%" in rate else 1.0)

            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY.strip()}",
                "Content-Type": "application/json",
            }

            audio_segments = []
            async with httpx.AsyncClient(timeout=90.0) as client:
                for i, chunk in enumerate(text_chunks):
                    payload = {
                        "model": "tts-1",
                        "input": chunk,
                        "voice": voice_config["id"],
                        "speed": speed,
                    }
                    response = await client.post(
                        "https://api.openai.com/v1/audio/speech",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    audio_segments.append(response.content)

            combined = AudioSegment.empty()
            for mp3_data in audio_segments:
                seg = AudioSegment.from_mp3(io.BytesIO(mp3_data))
                combined += seg
            combined = combined.set_frame_rate(44100).set_channels(2)
            await asyncio.to_thread(combined.export, str(output_path), format="mp3", bitrate="192k")
            return output_path, voice_key

        elif engine == "gemini":
            from google import genai
            from google.genai import types
            import subprocess
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            text_chunks = split_text_paragraphs(clean_text)
            all_pcm_data = bytearray()

            async def process_chunk(i, chunk, chunk_previous_text=None):
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        voice_basis = VOICE_INSTRUCTIONS.get(voice_key, "")
                        prompt_parts = []
                        
                        instr = "### AUDIO_REQUIREMENTS\n"
                        instr += "LANGUAGE: German (Deutsch)\n"
                        instr += "PRONUNCIATION: Standard German (Hochdeutsch), no foreign accent.\n"
                        if voice_basis: instr += f"VOICE_CHARACTER: {voice_basis}\n"
                        if rate: instr += f"SPEAKING_RATE: Use a speaking rate of {rate} relative to standard.\n"
                        instr += "CONTINUITY: The text under 'AUDIO_CONTEXT_REFERENCE' is for voice, pitch, and energy reference ONLY. DO NOT SPEAK the reference text. ONLY speak the text under 'TRANSCRIPT'."
                        prompt_parts.append(instr)
                        
                        if chunk_previous_text:
                            import re
                            sentences = re.split(r'(?<=[.!?]) +', chunk_previous_text.strip())
                            last_context = " ".join(sentences[-3:])
                            prompt_parts.append(f"### AUDIO_CONTEXT_REFERENCE (DO NOT SPEAK THIS)\n{last_context}")
                        
                        prompt_parts.append(f"### TRANSCRIPT (SPEAK ONLY THIS)\n{chunk}")
                        full_contents = "\n\n".join(prompt_parts)
                        
                        await rate_limiter.wait_for_capacity("tts")
                        response = await asyncio.wait_for(
                            client.aio.models.generate_content(
                                model='models/gemini-2.5-flash-preview-tts',
                                contents=full_contents,
                                config=types.GenerateContentConfig(
                                    speech_config=types.SpeechConfig(
                                        voice_config=types.VoiceConfig(
                                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                                voice_name=voice_config["id"]
                                            )
                                        )
                                    ),
                                    response_modalities=["AUDIO"],
                                )
                            ),
                            timeout=90.0
                        )
                        rate_limiter.increment_daily_quota("tts")
                        
                        pcm_data = None
                        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                            for part in response.candidates[0].content.parts:
                                if part.inline_data:
                                    pcm_data = part.inline_data.data
                                    break
                        if pcm_data: return pcm_data
                    except Exception as e:
                        if attempt == max_retries - 1: raise e
                        await asyncio.sleep(2 * (1 + random.random()))
                raise RuntimeError("Failed to generate Gemini TTS after retries")

            try:
                last_chunk_text = previous_text
                for i, chunk in enumerate(text_chunks):
                    pcm_data = await process_chunk(i, chunk, last_chunk_text)
                    all_pcm_data.extend(pcm_data)
                    last_chunk_text = chunk
                    if on_chunk_progress: await on_chunk_progress(i + 1, len(text_chunks))
            except Exception as e:
                err_msg = str(e).upper()
                # Catch Quota/Rate Limit errors specifically
                if any(err in err_msg for err in ["429", "QUOTA", "LIMIT"]):
                    # Differentiate between RPM and RPD if possible
                    is_daily = any(x in err_msg for x in ["DAY", "DAILY"])
                    is_minute = any(x in err_msg for x in ["MINUTE", "RPM"])
                    
                    if is_daily or (not is_minute):
                        logger.warning(f"Gemini TTS Daily Quota exceeded (API error): {e}. Marking service as exhausted.")
                        rate_limiter.mark_service_exhausted("tts")
                    else:
                        logger.warning(f"Gemini TTS Minute Rate Limit exceeded (API error): {e}. Falling back for this request.")
                    
                    return await generate_tts_chunk(text, output_path, voice_key="seraphina", rate=rate, is_title=is_title)
                
                if any(err in err_msg for err in ["TIMEOUT", "500", "INTERNAL"]):
                    return await generate_tts_chunk(text, output_path, voice_key="seraphina", rate=rate, is_title=is_title)
                raise e

            def _export_mp3(data, out_path):
                cmd = ["ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "pipe:0", "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k", str(out_path)]
                subprocess.run(cmd, input=bytes(data), capture_output=True, check=True)

            await asyncio.to_thread(_export_mp3, all_pcm_data, output_path)
            return output_path, voice_key

        elif engine == "xai":
            if not settings.XAI_API_KEY:
                raise ValueError("xAI API Key is missing.")

            import httpx
            from pydub import AudioSegment
            import io

            def _split_text_xai(t: str, max_bytes: int = 4000) -> list[str]:
                """Split text into chunks ≤ max_bytes for xAI TTS (max 15k chars)."""
                chunks: list[str] = []
                current = ""
                for sentence in t.replace("\n", " ").split(". "):
                    candidate = (current + ". " + sentence).strip() if current else sentence
                    if len(candidate.encode("utf-8")) > max_bytes:
                        if current:
                            chunks.append(current)
                        current = sentence
                    else:
                        current = candidate
                if current:
                    chunks.append(current)
                return chunks

            text_chunks = _split_text_xai(clean_text)
            headers = {
                "Authorization": f"Bearer {settings.XAI_API_KEY.strip()}",
                "Content-Type": "application/json",
            }
            audio_segments: list[bytes] = []

            async with httpx.AsyncClient(timeout=120.0) as client:
                for chunk in text_chunks:
                    payload = {
                        "text": chunk,
                        "voice_id": voice_config["id"],
                        "language": voice_config.get("language", "de"),
                        "output_format": {
                            "codec": "mp3"
                        }
                    }
                    response = await client.post(
                        "https://api.x.ai/v1/tts",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    audio_segments.append(response.content)

            combined = AudioSegment.empty()
            for mp3_data in audio_segments:
                combined += AudioSegment.from_mp3(io.BytesIO(mp3_data))
            combined = combined.set_frame_rate(44100).set_channels(2)
            await asyncio.to_thread(combined.export, str(output_path), format="mp3", bitrate="192k")
            return output_path, voice_key

        elif engine == "fish":
            if not settings.FISH_API_KEY:
                raise ValueError("Fish Audio API Key is missing.")
            
            # Check if text contains speaker tags for S2-Pro multi-speaker
            has_speaker_tags = bool(re.search(r'<\|speaker:\d+\|>', clean_text))
            
            if has_speaker_tags:
                user_id = None
                try:
                    story_id = output_path.parent.name
                    if story_id == "chunks":
                        story_id = output_path.parent.parent.name
                    with Session(db_engine) as db_session:
                        from app.models import StoryMeta
                        story_obj = db_session.get(StoryMeta, story_id)
                        if story_obj:
                            user_id = story_obj.user_id
                except Exception as db_err:
                    logger.debug(f"Could not resolve user_id for multi-voice references: {db_err}")

                # Split text into paragraphs and dynamically group them to avoid exceeding 4 unique voices
                paragraphs = [p.strip() for p in clean_text.replace("\r\n", "\n").split("\n\n") if p.strip()]
                sub_chunks = []
                current_chunk_paragraphs = []
                current_chunk_speakers = set()

                for p in paragraphs:
                    p_speakers = set(int(x) for x in re.findall(r'<\|speaker:(\d+)\|>', p))
                    potential_speakers = current_chunk_speakers.union(p_speakers)
                    if len(potential_speakers) > 3 and current_chunk_paragraphs:
                        sub_chunks.append(("\n\n".join(current_chunk_paragraphs), current_chunk_speakers))
                        current_chunk_paragraphs = [p]
                        current_chunk_speakers = p_speakers
                    else:
                        current_chunk_paragraphs.append(p)
                        current_chunk_speakers = potential_speakers

                if current_chunk_paragraphs:
                    sub_chunks.append(("\n\n".join(current_chunk_paragraphs), current_chunk_speakers))

                # Resolve all other fish voices for fallback
                all_voices = get_available_voices(user_id=user_id)
                primary_key = (speaker_voices or {}).get("0", voice_key)
                other_fish_voices = [
                    v for v in all_voices 
                    if v.get("engine") == "fish" and v.get("key") != primary_key and v.get("key") != "none"
                ]

                # Process each sub-chunk
                sub_chunks_to_process = []
                for sc_text, sc_speakers in sub_chunks:
                    # Sort speakers with 0 first
                    sorted_speakers = sorted(list(sc_speakers), key=lambda x: (x != 0, x))
                    speaker_map = {old_idx: new_idx for new_idx, old_idx in enumerate(sorted_speakers)}

                    def replace_tag(match):
                        old_idx = int(match.group(1))
                        return f"<|speaker:{speaker_map[old_idx]}|>"

                    rewritten_text = re.sub(r'<\|speaker:(\d+)\|>', replace_tag, sc_text)

                    # Resolve reference IDs for this sub-chunk
                    sc_ref_ids = []
                    for old_idx in sorted_speakers:
                        if speaker_voices and str(old_idx) in speaker_voices:
                            chosen_key = speaker_voices[str(old_idx)]
                            sc_ref_ids.append(get_fish_voice_id(chosen_key, user_id))
                        else:
                            if old_idx == 0:
                                sc_ref_ids.append(get_fish_voice_id(primary_key, user_id))
                            else:
                                if other_fish_voices:
                                    chosen_voice = other_fish_voices[(old_idx - 1) % len(other_fish_voices)]
                                    sc_ref_ids.append(get_fish_voice_id(chosen_voice["key"], user_id))
                                else:
                                    sc_ref_ids.append(get_fish_voice_id(primary_key, user_id))

                    # Enforce safety limit of 3 unique voice IDs (fallback)
                    if len(set(sc_ref_ids)) > 3:
                        unique_ids = []
                        mapped_ids = []
                        for voice_id in sc_ref_ids:
                            if voice_id not in unique_ids:
                                if len(unique_ids) < 3:
                                    unique_ids.append(voice_id)
                                    mapped_ids.append(voice_id)
                                else:
                                    fallback_idx = 1 if len(unique_ids) > 1 else 0
                                    mapped_ids.append(unique_ids[fallback_idx])
                            else:
                                mapped_ids.append(voice_id)
                        sc_ref_ids = mapped_ids

                    sub_chunks_to_process.append((rewritten_text, sc_ref_ids))

                if len(sub_chunks_to_process) == 1:
                    # Single chunk - run directly
                    rewritten_text, sc_ref_ids = sub_chunks_to_process[0]
                    logger.info(f"TTS Fish S2-Pro: single-chunk. Mapping references: {sc_ref_ids}")
                    await generate_fish_audio(rewritten_text, output_path, sc_ref_ids, use_s2_pro=True)
                else:
                    # Multi-chunk - run in parallel and concatenate
                    logger.info(f"TTS Fish S2-Pro: multi-chunk partitioning into {len(sub_chunks_to_process)} chunks.")

                    async def process_sub_chunk(idx, text, ref_ids):
                        sub_path = output_path.with_name(f"{output_path.stem}_sub_{idx}.mp3")
                        await generate_fish_audio(text, sub_path, ref_ids, use_s2_pro=True)
                        return sub_path

                    tasks = [process_sub_chunk(idx, text, ref_ids) for idx, (text, ref_ids) in enumerate(sub_chunks_to_process)]
                    sub_paths = await asyncio.gather(*tasks)

                    from pydub import AudioSegment
                    import io

                    combined = AudioSegment.empty()
                    for sub_path in sub_paths:
                        seg = AudioSegment.from_mp3(str(sub_path))
                        combined += seg
                        try:
                            sub_path.unlink(missing_ok=True)
                        except Exception:
                            pass

                    combined = combined.set_frame_rate(44100).set_channels(2)
                    await asyncio.to_thread(combined.export, str(output_path), format="mp3", bitrate="192k")
            else:
                # Use S2 Pro for single voice as well to support [bracket] emotion tags
                logger.info(f"TTS Fish S2-Pro: single-voice enabled. Reference: {voice_config['id']}")
                await generate_fish_audio(clean_text, output_path, [voice_config["id"]], use_s2_pro=True)
            return output_path, voice_key


    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise

    return output_path, voice_key


async def generate_voice_preview(
    voice_key: str,
    output_path: Path,
    direct_fish_id: str | None = None,
) -> Path:
    """Generate a short preview clip for a voice."""
    import hashlib
    preview_text = "Hallo! Willkommen im Labor für Kurzgeschichten. Lass uns gemeinsam in ein neues Abenteuer starten."
    # Include voice_key and a version prefix to force regeneration of cached fallbacks
    print(f"Generating preview for voice {voice_key}...")
    # Use v4 for xAI voices to force refresh, v3 for others
    version = "v4" if voice_key.startswith("xai_") else "v3"
    text_hash = hashlib.md5(f"{version}:{preview_text}:{voice_key}".encode()).hexdigest()[:8]
    hash_marker = output_path.parent / f".{output_path.stem}.hash"

    if output_path.exists() and output_path.stat().st_size > 1000:
        if hash_marker.exists() and hash_marker.read_text().strip() == text_hash:
            return output_path
        output_path.unlink(missing_ok=True)

    res_path, _ = await generate_tts_chunk(preview_text, output_path, voice_key, direct_fish_id=direct_fish_id)
    hash_marker.write_text(text_hash)
    return res_path


async def chapters_to_audio(
    chapters: list[dict],
    output_dir: Path,
    voice_key: str = DEFAULT_VOICE,
    rate: str = "0%",
    genre: str | None = None,
    on_progress: callable = None,
    synopsis: str | None = None,
    title: str | None = None,
    multi_voice: bool = False,
    speaker_voices: dict[str, str] | None = None,
) -> tuple[list[Path], str]:
    """
    Convert all chapters to individual MP3 chunks.
    Consolidates text for Gemini TTS to save API calls.
    """
    is_gemini = voice_key in GEMINI_VOICES
    actual_voice = voice_key
    output_dir.mkdir(parents=True, exist_ok=True)

    if is_gemini:
        # Build the full story text stream: Title + pause + All Chapters
        full_story_text = ""
        if title:
            # We add dots with spaces and newlines for a strong, natural title pause
            full_story_text += f"{title}. . . \n\n"
        
        full_story_text += "\n\n".join([ch["text"] for ch in chapters])
        clean_text = full_story_text.replace("*", "").replace("_", "").replace("#", "")
        
        all_chunks = split_text_paragraphs(clean_text)
        total_all_chunks = len(all_chunks)
        chunk_files = [output_dir / f"chunk_{i}.mp3" for i in range(total_all_chunks)]
        
        if on_progress:
            await on_progress("tts", f"Vertone Geschichte in {total_all_chunks} optimierten Chunks...", {"completed": 0, "total": total_all_chunks})

        completed_chunks = 0
        
        async def process_gemini_chunk(i: int):
            nonlocal actual_voice, completed_chunks
            chunk = all_chunks[i]
            # Continuity: use synopsis for first chunk, previous chunk text for others
            prev = synopsis if i == 0 else all_chunks[i-1]
            
            _, realized_voice = await generate_tts_chunk(
                chunk,
                chunk_files[i],
                voice_key,
                rate,
                genre=genre,
                previous_text=prev,
                multi_voice=multi_voice,
                speaker_voices=speaker_voices,
            )
            if realized_voice != voice_key: actual_voice = realized_voice
            completed_chunks += 1
            if on_progress:
                await on_progress("tts_chunk_done", f"Chunk {i+1} fertig", {"completed": completed_chunks, "total": total_all_chunks})

        # Throttle to 2 parallel chunks as per user requirement (safe for 10 RPM)
        semaphore = asyncio.Semaphore(2)
        async def run_with_semaphore(idx):
            async with semaphore: await process_gemini_chunk(idx)

        await asyncio.gather(*[run_with_semaphore(i) for i in range(total_all_chunks)])
        
        return chunk_files, actual_voice

    else:
        # Fallback for non-Gemini engines: process per chapter + title
        audio_files = []
        if title:
            audio_files.append(output_dir / "title.mp3")
        
        audio_files.extend([output_dir / f"chapter_{i+1}.mp3" for i in range(len(chapters))])
        
        total_all_chunks = len(audio_files)
        completed_chunks = 0
        if on_progress:
            msg = f"Vertone Titel und {len(chapters)} Kapitel..." if title else f"Vertone {len(chapters)} Kapitel..."
            await on_progress("tts", msg, {"completed": 0, "total": total_all_chunks})

        # Process title if exists
        if title:
            _, realized_voice = await generate_tts_chunk(
                f"{title}. . . ", 
                audio_files[0], 
                voice_key, 
                rate, 
                is_title=True, 
                genre=genre,
                speaker_voices=speaker_voices,
            )
            if realized_voice != voice_key: actual_voice = realized_voice
            completed_chunks += 1
            if on_progress:
                await on_progress("tts_chunk_done", "Titel vertont", {"completed": completed_chunks, "total": total_all_chunks})

        # Process chapters in parallel
        async def process_chapter(chapter_idx: int):
            nonlocal actual_voice, completed_chunks
            # Index in audio_files is (chapter_idx + 1) if title exists
            file_idx = chapter_idx + (1 if title else 0)
            _, realized_voice = await generate_tts_chunk(
                chapters[chapter_idx]["text"], 
                audio_files[file_idx], 
                voice_key, 
                rate, 
                genre=genre,
                multi_voice=multi_voice,
                speaker_voices=speaker_voices,
            )
            if realized_voice != voice_key: actual_voice = realized_voice
            completed_chunks += 1
            if on_progress:
                await on_progress("tts_chunk_done", f"Kapitel {chapter_idx+1} vertont", {"completed": completed_chunks, "total": total_all_chunks})

        # Use a conservative semaphore of 2 for all engines (safe for RPM and stability)
        semaphore = asyncio.Semaphore(2)
        async def run_with_semaphore(idx):
            async with semaphore: await process_chapter(idx)

        # Only process chapters here, title was handled above
        await asyncio.gather(*[run_with_semaphore(i) for i in range(len(chapters))])
        return audio_files, actual_voice
