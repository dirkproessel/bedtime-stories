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
    "seraphina": {"id": "de-DE-SeraphinaMultilingualNeural", "name": "Seraphina", "gender": "female"},
    "florian": {"id": "de-DE-FlorianMultilingualNeural", "name": "Florian", "gender": "male"},
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
    "aoede":      {"id": "Aoede",      "name": "Aoede",      "gender": "female"},   # Breezy, klar
    "kore":       {"id": "Kore",       "name": "Kore",        "gender": "female"},   # Firm, energetisch
    "sulafat":    {"id": "Sulafat",    "name": "Sulafat",     "gender": "female"},   # Warm, überzeugend
    "gacrux":     {"id": "Gacrux",     "name": "Gacrux",      "gender": "male"},     # Smooth, tief-resonant
    "charon":     {"id": "Charon",     "name": "Charon",      "gender": "male"},     # Informative, smooth
    "fenrir":     {"id": "Fenrir",     "name": "Fenrir",      "gender": "male"},     # Excitable, warm
    "orus":       {"id": "Orus",       "name": "Orus",        "gender": "male"},     # Firm, klar
    "zephyr":     {"id": "Zephyr",     "name": "Zephyr",      "gender": "neutral"},  # Bright, frisch
    # --- Weitere 8 (Show More) ---
    "enceladus":  {"id": "Enceladus",  "name": "Enceladus",   "gender": "male"},     # Breathy, sanft
    "puck":       {"id": "Puck",       "name": "Puck",        "gender": "male"},     # Upbeat, lebendig
    "schedar":    {"id": "Schedar",    "name": "Schedar",     "gender": "male"},     # Even, entspannt
    "iapetus":    {"id": "Iapetus",    "name": "Iapetus",     "gender": "male"},     # Clear, Everyman
    "algenib":    {"id": "Algenib",    "name": "Algenib",     "gender": "female"},   # Gravelly, charakterstark
    "laomedeia":  {"id": "Laomedeia", "name": "Laomedeia",   "gender": "female"},   # Upbeat, inquisitiv
    "despina":    {"id": "Despina",    "name": "Despina",     "gender": "female"},   # Smooth, fließend
    "umbriel":    {"id": "Umbriel",    "name": "Umbriel",     "gender": "neutral"},  # Easy-going, vielseitig
}


# Fish Audio (Cloned Voices)
FISH_VOICES = {
    # Custom User Voices are added dynamically below
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


def get_available_voices() -> list[dict]:
    """Return list of available voice profiles."""
    voices = []
    
    # Edge Voices
    for key, v in EDGE_VOICES.items():
        voices.append({
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "edge",
        })
        
    # Google Voices (Temporarily Disabled)
    # for key, v in GOOGLE_VOICES.items():
    #     voices.append({
    #         "key": key,
    #         "name": v["name"],
    #         "gender": v["gender"],
    #         "engine": "google",
    #     })

    # OpenAI Voices
    for key, v in OPENAI_VOICES.items():
        voices.append({
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "openai",
        })

    # Gemini Voices
    for key, v in GEMINI_VOICES.items():
        voices.append({
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "gemini",
        })

    # Fish Audio Voices (Static)
    for key, v in FISH_VOICES.items():
        voices.append({
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "fish",
        })

    # Fish Audio Voices (Dynamic from User DB)
    try:
        with Session(db_engine) as db_session:
            db_users = db_session.exec(select(User).where(User.custom_voice_id != None)).all()
            for u in db_users:
                # Avoid duplicates if already in static list
                if any(v["key"] == u.custom_voice_id for v in voices):
                    continue
                voices.append({
                    "key": u.custom_voice_id,
                    "name": u.custom_voice_name or f"Stimme von {u.username or u.email}",
                    "gender": "neutral",
                    "engine": "fish",
                })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error fetching dynamic voices: {e}")

    # Virtual Voices (like 'none')
    voices.append({
        "key": "none",
        "name": "Keine Stimme (nur Text)",
        "gender": "neutral",
        "engine": "virtual",
    })

    return voices


async def generate_tts_chunk(
    text: str,
    output_path: Path,
    voice_key: str = DEFAULT_VOICE,
    rate: str = "0%",
    is_title: bool = False,
    genre: str | None = None,
    previous_text: str | None = None,
    on_chunk_progress: callable = None,
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
    elif voice_key in FISH_VOICES:
        voice_config = FISH_VOICES[voice_key]
        engine = "fish"
    else:
        # Check if it's a dynamic Fish voice ID
        engine = "edge" # Fallback
        voice_config = None
        
        # Look up in DB if the key looks like a Fish UUID (32 chars)
        if len(voice_key) >= 30:
            try:
                # Use the 'db_engine' imported from app.database
                with Session(db_engine) as db_session:
                    user_with_voice = db_session.exec(select(User).where(User.custom_voice_id == voice_key)).first()
                    if user_with_voice:
                        engine = "fish"
                        voice_config = {"id": voice_key}
            except Exception as e:
                logger.error(f"Error checking dynamic voice ID: {e}")

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
            voice_config = EDGE_VOICES.get(voice_key, EDGE_VOICES[DEFAULT_VOICE])
            engine = "edge"

    logger.info(f"TTS: Generating audio with {engine} voice {voice_config['id']} -> {output_path}")

    # Cleanup text: remove markdown formatting
    clean_text = text.replace("*", "").replace("_", "").replace("#", "")

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

        elif engine == "fish":
            if not settings.FISH_API_KEY:
                raise ValueError("Fish Audio API Key is missing.")
            
            from fish_audio_sdk import Session, TTSRequest
            
            # Note: We use a simple session-based request here.
            # For 1000 words, we might want to split into sentences internally
            # if the API has a strict single-request limit.
            
            with open(output_path, "wb") as f:
                session = Session(apikey=settings.FISH_API_KEY)
                # We use the sync-ish wrapper or direct byte output for simplicity in this chunk-based service
                # The tts_service already handles chunking at a higher level (per chapter).
                for chunk in session.tts(TTSRequest(
                    text=clean_text,
                    reference_id=voice_config["id"],
                    format="mp3"
                )):
                    f.write(chunk)
            
            return output_path, voice_key

    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise

    return output_path, voice_key


async def generate_voice_preview(
    voice_key: str,
    output_path: Path,
) -> Path:
    """Generate a short preview clip for a voice."""
    import hashlib
    preview_text = "Hallo! Willkommen im Labor für Kurzgeschichten. Lass uns gemeinsam in ein neues Abenteuer starten."
    text_hash = hashlib.md5(preview_text.encode()).hexdigest()[:8]
    hash_marker = output_path.parent / f".{output_path.stem}.hash"

    if output_path.exists() and output_path.stat().st_size > 1000:
        if hash_marker.exists() and hash_marker.read_text().strip() == text_hash:
            return output_path
        output_path.unlink(missing_ok=True)

    res_path, _ = await generate_tts_chunk(preview_text, output_path, voice_key)
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
                genre=genre
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
                genre=genre
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
