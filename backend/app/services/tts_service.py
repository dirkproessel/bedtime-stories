"""
Text-to-Speech service supporting Edge TTS and Google Cloud TTS.
Generates MP3 chunks per chapter.
"""

import edge_tts
import random
from pathlib import Path
from app.config import settings
from app.services.rate_limiter import rate_limiter

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
    "Abenteuer": "„Erzähle mit viel Energie und Vorwärtsbewegung. Nutze einen dynamischen Rhythmus.“",
    "Science-Fiction": "„Lies mit kühler Präzision. Deine Artikulation ist extrem sauber und technisch-distanziert.“",
    "Märchen": "„Nutze einen weiten Melodiebogen. Erzähle warm und geborgen mit sanften, fließenden Übergängen (Legato).“",
    "Komödie": "„Sprich dynamisch mit hoher Varianz in der Tonhöhe. Nutze präzise Pausen für Pointen. Sei lebhaft und präsent.“",
    "Thriller": "„Erzähle gehetzt und mit akustischem Druck. Verringere die Pausen zwischen den Worten deutlich.“",
    "Drama": "„Lass die Stimme am Satzende schwer absinken. Erzähle mit einer melancholischen Resonanz und einem getragenen Rhythmus.“",
    "Grusel": "„Erzähle leise und hauchend. Dehne die Pausen zwischen den Sätzen aus, um eine unheimliche Atmosphäre zu schaffen.“",
    "Fantasy": "„Sprich erhaben und mit viel Volumen. Nutze einen feierlichen, langsamen Rhythmus.“",
    "Satire": "„Erzähle mit einem spöttischen, bewusst arroganten Unterton. Nutze eine scharfe Artikulation. Betone Pointen trocken und präzise.“",
    "Dystopie": "„Erzähle flach und hoffnungslos. Reduziere die Dynamik und Melodie auf ein Minimum.“",
    "Historisch": "„Sprich mit aristokratischer Ruhe und perfekter Artikulation. Nutze einen würdevollen, langsamen Rhythmus.“",
    "Mythologie": "„Lies wie ein Orakel: Langsam, gewichtig und mit großer Ernsthaftigkeit.“",
    "Roadtrip": "„Erzähle locker und beiläufig, wie in einem entspannten Gespräch. Nutze eine ganz natürliche Intonation.“",
    "Gute Nacht": "„Lies extrem leise, monoton und ohne Akzente. Werde zum Ende hin immer langsamer und weicher. Minimale Energie.“",
    "Fabel": "„Sprich wie ein gütiger Lehrer. Betone die Lehrsätze am Ende deutlicher und mit mehr Gewicht.“",
    "Modern Romanze": "„Erzähle locker, urban und mit einem Lächeln in der Stimme. Nutze eine helle, moderne Satzmelodie.“",
    "Sinnliche Romanze": "„Sprich sehr nah am Mikrofon, tief und langsam. Erzeuge Nähe durch sanfte, fließende Übergänge (Legato).“",
    "Erotik": "„Lies hauchig, langsam und mit vielen kleinen Atemphasen. Erzeuge eine vibrierende, knisternde Atmosphäre.“",
    "Dark Romance": "„Erzähle fordernd, intensiv und mit einer unterdrückten emotionalen Schärfe.“",
}



# ── Text Chunking for Gemini TTS ──
MIN_CHUNK_BYTES = 750
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
    # if voice_key in GOOGLE_VOICES:
    #     voice_config = GOOGLE_VOICES[voice_key]
    #     engine = "google"
    if voice_key in OPENAI_VOICES:
        voice_config = OPENAI_VOICES[voice_key]
        engine = "openai"
    elif voice_key in GEMINI_VOICES:
        if not rate_limiter.has_daily_quota("tts"):
            logger.warning(f"Rate Limiter: Daily Gemini quota reached. Immediately falling back to Edge TTS for voice {voice_key}.")
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
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=voice_config["id"],
                rate=rate,
            )
            await communicate.save(str(output_path))
        elif engine == "google":
            # Google Cloud TTS (Paid/Premium)
            from google.cloud import texttospeech
            
            # Initialize async client
            client = texttospeech.TextToSpeechAsyncClient(
                client_options={"api_key": settings.GEMINI_API_KEY}
            )
            
            # Split text into chunks < 5000 bytes (safety margin at 4500)
            def split_text(t, max_bytes=4500):
                chunks = []
                current_chunk = ""
                # Split by sentences (rough approximation)
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

            text_chunks = split_text(clean_text)
            audio_contents = []

            for i, chunk in enumerate(text_chunks):
                logger.info(f"TTS Google: Processing chunk {i+1}/{len(text_chunks)} ({len(chunk.encode('utf-8'))} bytes)")
                synthesis_input = texttospeech.SynthesisInput(text=chunk)
                
                # Select the voice
                voice = texttospeech.VoiceSelectionParams(
                    language_code="de-DE",
                    name=voice_config["id"]
                )
                
                try:
                    if rate.startswith("-") and rate.endswith("%"):
                        val = int(rate[1:-1])
                        speaking_rate = 1.0 - (val / 100.0)
                    elif rate.startswith("+") and rate.endswith("%"):
                        val = int(rate[1:-1])
                        speaking_rate = 1.0 + (val / 100.0)
                    else:
                        speaking_rate = 0.95 if rate == "-5%" else 1.0
                except:
                    speaking_rate = 0.95 if rate == "-5%" else 1.0

                if voice_key == "percy":
                    speaking_rate *= 0.92

                audio_config = texttospeech.AudioConfig(
                    audio_encoding=texttospeech.AudioEncoding.MP3,
                    speaking_rate=speaking_rate,
                    pitch=-1.5 if voice_key == "eliza" else 0.0
                )
                
                response = await client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                audio_contents.append(response.audio_content)
            
            with open(output_path, "wb") as out:
                for content in audio_contents:
                    out.write(content)
            return output_path, voice_key
        elif engine == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API Key is missing.")
            
            import httpx
            import asyncio

            # OpenAI TTS limit: ~4096 chars, we split to 2000 bytes for uniform chunking with Gemini
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
                    logger.info(f"TTS OpenAI: Processing chunk {i+1}/{len(text_chunks)} ({len(chunk)} chars)")
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

            # Merge all MP3 chunks with pydub
            from pydub import AudioSegment
            import io
            combined = AudioSegment.empty()
            for mp3_data in audio_segments:
                seg = AudioSegment.from_mp3(io.BytesIO(mp3_data))
                combined += seg
            combined = combined.set_frame_rate(44100).set_channels(2)
            await asyncio.to_thread(combined.export, str(output_path), format="mp3", bitrate="192k")

        elif engine == "gemini":
            from google import genai
            from google.genai import types
            import asyncio
            import subprocess
            import tempfile
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            text_chunks = split_text_paragraphs(clean_text)
            all_pcm_data = bytearray()

            async def process_chunk(i, chunk, chunk_previous_text=None):
                max_retries = 3
                for attempt in range(max_retries):
                    logger.info(f"TTS Gemini: Processing chunk {i+1}/{len(text_chunks)} ({len(chunk.encode('utf-8'))} bytes) - Attempt {attempt+1}")
                    try:
                        # Build prompt following Google's TTS Prompting Guide:
                        # Director's Notes + Sample Context + Transcript
                        voice_basis = VOICE_INSTRUCTIONS.get(voice_key, "")
                        genre_tweak = GENRE_INSTRUCTIONS.get(genre, "") if genre else ""
                        
                        prompt_parts = []
                        
                        # Instructions Block (Voice, Genre, Rate, and Continuity)
                        instr = "### AUDIO_INSTRUCTIONS\n"
                        if voice_basis: instr += f"STIMME_CHARAKTER: {voice_basis}\n"
                        if genre_tweak: instr += f"ERZÄHL_STIL: {genre_tweak}\n"
                        if rate: instr += f"SPEAKING_RATE: Sprich mit einer Geschwindigkeit von {rate} im Vergleich zum Standard.\n"
                        
                        instr += "CONTINUITY: Halte exakt dieselbe Stimme, Tonhöhe und Energie wie im vorangegangenen Kontext bei. Es darf keine hörbaren Sprünge zwischen den Aufnahmen geben."
                        prompt_parts.append(instr)
                        
                        # Sample Context (to keep the voice consistent)
                        if chunk_previous_text:
                            import re
                            sentences = re.split(r'(?<=[.!?]) +', chunk_previous_text.strip())
                            last_context = " ".join(sentences[-2:])
                            prompt_parts.append(f"### AUDIO_CONTEXT_REFERENCE\n{last_context}")
                        
                        # Transcript
                        prompt_parts.append(f"### TRANSCRIPT\n{chunk}")
                        
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
                                    tools=[],  # Disable AFC (Automatic Function Calling)
                                )
                            ),
                            timeout=90.0
                        )
                        
                        # Record successful request towards daily quota
                        rate_limiter.increment_daily_quota("tts")
                    except asyncio.TimeoutError:
                        if attempt == max_retries - 1:
                            logger.error(f"Gemini API timed out on chunk {i+1} after {max_retries} attempts. Triggering Fallback...")
                            raise RuntimeError("GEMINI_TIMEOUT_FALLBACK")
                        retry_delay = 2 * (1 + random.random())  # Jitter: 2-4s
                        logger.warning(f"Timeout on chunk {i+1}. Retrying in {retry_delay:.1f}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    except Exception as e:
                        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                            logger.warning(f"Gemini API rate limit hit (429) on chunk {i+1}. Triggering Edge TTS Fallback...")
                            raise RuntimeError("GEMINI_429_FALLBACK")
                        elif "500" in str(e) or "INTERNAL" in str(e).upper():
                            if attempt == max_retries - 1:
                                logger.error(f"Gemini API 500 Internal Error on chunk {i+1} after {max_retries} attempts. Triggering Fallback...")
                                raise RuntimeError("GEMINI_500_FALLBACK")
                            retry_delay = 2 * (1 + random.random())  # Jitter: 2-4s
                            logger.warning(f"500 Internal Error on chunk {i+1}. Retrying in {retry_delay:.1f}s... ({e})")
                            await asyncio.sleep(retry_delay)
                            continue
                        raise e

                    pcm_data = None
                    try:
                        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                            for part in response.candidates[0].content.parts:
                                if part.inline_data:
                                    pcm_data = part.inline_data.data
                                    break
                    except Exception as parse_error:
                        logger.warning(f"Error parsing Gemini response on chunk {i+1}: {parse_error}")

                    if not pcm_data:
                        if attempt == max_retries - 1:
                            logger.error(f"No audio data returned from Gemini TTS (Max retries reached) for chunk {i+1}. Result: {response.candidates[0].finish_reason if response.candidates else 'No candidates'}")
                            raise RuntimeError(f"No audio data returned from Gemini TTS for voice {voice_key} on chunk {i+1}")
                        
                        retry_delay = 2 * (1 + random.random())  # Jitter: 2-4s
                        logger.warning(f"No audio data in response for chunk {i+1} (Attempt {attempt+1}/{max_retries}). Retrying in {retry_delay:.1f}s...")
                        await asyncio.sleep(retry_delay)
                        continue
                    
                    return pcm_data


            try:
                # Process chunks sequentially to prevent RPM (Requests Per Minute) spikes 
                # and to allow context carry-over between chunks.
                last_chunk_text = previous_text
                for i, chunk in enumerate(text_chunks):
                    pcm_data = await process_chunk(i, chunk, last_chunk_text)
                    all_pcm_data.extend(pcm_data)
                    last_chunk_text = chunk
                    # Report per-chunk progress
                    if on_chunk_progress:
                        await on_chunk_progress(i + 1, len(text_chunks))
                    
            except Exception as e:
                # If any chunk hit the quota limit, fall back for the entire chapter
                if str(e) in ["GEMINI_429_FALLBACK", "GEMINI_TIMEOUT_FALLBACK", "GEMINI_500_FALLBACK"]:
                    logger.warning(f"Chapter fallback triggered due to Gemini API limits/errors. Using Edge TTS.")
                    return await generate_tts_chunk(text, output_path, voice_key="seraphina", rate=rate, is_title=is_title)
                raise e

            # Convert raw PCM byte array to MP3 directly using FFmpeg subprocess instead of pydub.
            # Avoids Popen buffering hangs on Windows common with pydub.
            def _export_mp3(data, out_path):
                # We pipe the 16-bit Mono 24kHz PCM to stdin, encode to 44.1kHz Stereo MP3.
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "s16le",       # 16-bit signed little-endian PCM
                    "-ar", "24000",      # 24kHz sample rate (Gemini default)
                    "-ac", "1",          # Mono
                    "-i", "pipe:0",      # Read from stdin
                    "-ar", "44100",      # Target 44.1kHz
                    "-ac", "2",          # Target stereo
                    "-c:a", "libmp3lame",
                    "-b:a", "192k",
                    str(out_path)
                ]
                
                process = subprocess.run(
                    cmd,
                    input=bytes(data),
                    capture_output=True,
                    check=False
                )
                
                if process.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed to convert Gemini PCM to MP3:\n{process.stderr.decode(errors='replace')}")

            await asyncio.to_thread(_export_mp3, all_pcm_data, output_path)

            return output_path, voice_key


        # Verify file was created and has content
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"TTS generated empty file for voice {voice_key}")

        logger.info(f"TTS: Generated {output_path.stat().st_size} bytes")
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
    import logging
    logger = logging.getLogger(__name__)

    preview_text = (
        "Hallo! Willkommen im Labor für Kurzgeschichten. "
        "Lass uns gemeinsam in ein neues Abenteuer starten."
    )

    # Hash-based cache invalidation: if preview_text changes the hash changes
    # and the old mp3 is automatically deleted before regenerating.
    text_hash = hashlib.md5(preview_text.encode()).hexdigest()[:8]
    hash_marker = output_path.parent / f".{output_path.stem}.hash"

    if output_path.exists() and output_path.stat().st_size > 1000:
        stored_hash = hash_marker.read_text().strip() if hash_marker.exists() else ""
        if stored_hash == text_hash:
            logger.info(f"Using cached preview for {voice_key}")
            return output_path
        logger.info(f"Preview text changed for {voice_key} – regenerating.")
        output_path.unlink(missing_ok=True)

    if output_path.exists():
        output_path.unlink()

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
) -> list[Path]:
    """
    Convert all chapters to individual MP3 files.

    Args:
        chapters: List of {"title": str, "text": str}
        output_dir: Directory for the MP3 chunks
        voice_key: Voice profile key
        rate: Speaking rate
        on_progress: Async callback(status_type, message, extra_data)
            Called with "tts_chunk_done" after each text chunk completes.
            extra_data = {"completed": int, "total": int}

    Returns:
        Tuple of (list of MP3 paths, actual voice key used)
    """
    import asyncio
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = [output_dir / f"chapter_{i + 1:02d}.mp3" for i in range(len(chapters))]
    actual_voice = voice_key

    # Pre-compute previous_text for each chapter (deterministic, no API needed)
    chapter_contexts = [None] * len(chapters)
    for i in range(1, len(chapters)):
        chapter_contexts[i] = chapters[i - 1]["text"]

    # Pre-count total text chunks across all chapters (for Gemini voices)
    is_gemini = voice_key in GEMINI_VOICES
    total_all_chunks = 0
    if is_gemini:
        for ch in chapters:
            clean = ch["text"].replace("*", "").replace("_", "").replace("#", "")
            total_all_chunks += len(split_text_paragraphs(clean))
    else:
        total_all_chunks = len(chapters)  # 1 "chunk" per chapter for other engines

    completed_chunks = 0

    if on_progress:
        await on_progress(
            "tts",
            f"Vertone {len(chapters)} Kapitel ({total_all_chunks} Chunks)...",
            {"completed": 0, "total": total_all_chunks}
        )

    async def process_chapter(i: int, chapter: dict):
        nonlocal actual_voice, completed_chunks
        full_text = chapter["text"]

        async def chunk_done_cb(chunk_done: int, chunk_total: int):
            nonlocal completed_chunks
            completed_chunks += 1
            if on_progress:
                await on_progress(
                    "tts_chunk_done",
                    f"Kapitel {i+1} Chunk {chunk_done}/{chunk_total}",
                    {"completed": completed_chunks, "total": total_all_chunks}
                )

        _, realized_voice = await generate_tts_chunk(
            full_text,
            audio_files[i],
            voice_key,
            rate,
            genre=genre,
            previous_text=chapter_contexts[i],
            on_chunk_progress=chunk_done_cb,
        )
        if realized_voice != voice_key:
            actual_voice = realized_voice

        # For non-Gemini engines (no chunk callback), report chapter as one chunk
        if not is_gemini and on_progress:
            completed_chunks += 1
            await on_progress(
                "tts_chunk_done",
                f"Kapitel {i+1} vertont",
                {"completed": completed_chunks, "total": total_all_chunks}
            )

    # Run chapter generations concurrently with semaphore
    is_premium = voice_key in GEMINI_VOICES or voice_key in OPENAI_VOICES
    concurrency_limit = 3 if is_premium else 10
    semaphore = asyncio.Semaphore(concurrency_limit)

    async def run_with_semaphore(i: int, ch: dict):
        async with semaphore:
            await process_chapter(i, ch)

    tasks = [run_with_semaphore(i, ch) for i, ch in enumerate(chapters)]
    await asyncio.gather(*tasks)

    return audio_files, actual_voice
