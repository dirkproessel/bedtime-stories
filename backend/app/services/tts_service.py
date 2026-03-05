"""
Text-to-Speech service supporting Edge TTS and Google Cloud TTS.
Generates MP3 chunks per chapter.
"""

import edge_tts
from pathlib import Path
from app.config import settings

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
    "aoede": {"id": "Aoede", "name": "Aoede", "gender": "female"},
    "enceladus": {"id": "Enceladus", "name": "Enceladus", "gender": "male"},
    "puck": {"id": "Puck", "name": "Puck", "gender": "male"},
    "charon": {"id": "Charon", "name": "Charon", "gender": "male"},
    "kore": {"id": "Kore", "name": "Kore", "gender": "female"},
}


DEFAULT_VOICE = "seraphina"

# Global flag to track if the daily Gemini Flash TTS quota is exhausted.
# If True, all subsequent requests in the current session will immediately fall back to Edge TTS.
GEMINI_QUOTA_EXHAUSTED = False


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

        
    return voices


async def generate_tts_chunk(
    text: str,
    output_path: Path,
    voice_key: str = DEFAULT_VOICE,
    rate: str = "-5%",
    is_title: bool = False,
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
        global GEMINI_QUOTA_EXHAUSTED
        if GEMINI_QUOTA_EXHAUSTED:
            logger.warning(f"Global Gemini quota flag is set. Immediately falling back to Edge TTS for voice {voice_key}.")
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
            
            # Rate adjustment hint for Gemini (but skip for titles as it distorts short sentences)
            speed_hint = " (Sprich ruhig und langsam)" if ("-15%" in rate and not is_title) else ""
            
            # Split text into chunks < 2000 bytes (unified with OpenAI chunk size)
            def split_text(t, max_bytes=2000):
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

            text_chunks = split_text(clean_text)
            all_pcm_data = bytearray()

            async def process_chunk(i, chunk):
                logger.info(f"TTS Gemini: Processing chunk {i+1}/{len(text_chunks)} ({len(chunk.encode('utf-8'))} bytes)")
                try:
                    # Added wait_for to prevent infinite network hangs
                    response = await asyncio.wait_for(
                        client.aio.models.generate_content(
                            model='models/gemini-2.5-flash-preview-tts',
                            contents=chunk + speed_hint,
                            config=types.GenerateContentConfig(
                                speech_config=types.SpeechConfig(
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice_config["id"]
                                        )
                                    )
                                ),
                                response_modalities=["AUDIO"]
                            )
                        ),
                        timeout=90.0
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Gemini API timed out on chunk {i+1}. Triggering Fallback...")
                    raise RuntimeError("GEMINI_TIMEOUT_FALLBACK")
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        logger.warning(f"Gemini API rate limit hit (429) on chunk {i+1}. Triggering Edge TTS Fallback...")
                        global GEMINI_QUOTA_EXHAUSTED
                        GEMINI_QUOTA_EXHAUSTED = True
                        raise RuntimeError("GEMINI_429_FALLBACK")
                    raise e

                pcm_data = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        pcm_data = part.inline_data.data
                        break
                        
                if not pcm_data:
                    raise RuntimeError(f"No audio data returned from Gemini TTS for voice {voice_key} on chunk {i+1}")
                
                return pcm_data

            try:
                # Process chunks sequentially to prevent RPM (Requests Per Minute) spikes 
                # which can quickly trigger the daily quota and rate limits.
                for i, chunk in enumerate(text_chunks):
                    pcm_data = await process_chunk(i, chunk)
                    all_pcm_data.extend(pcm_data)
                    # Add a very small delay between chunks to further smooth out the RPM
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                # If any chunk hit the quota limit, fall back for the entire chapter
                if str(e) in ["GEMINI_429_FALLBACK", "GEMINI_TIMEOUT_FALLBACK"]:
                    logger.warning(f"Chapter fallback triggered due to Gemini API limits. Using Edge TTS.")
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
    rate: str = "-5%",
    on_progress: callable = None,
) -> list[Path]:
    """
    Convert all chapters to individual MP3 files.

    Args:
        chapters: List of {"title": str, "text": str}
        output_dir: Directory for the MP3 chunks
        voice_key: Voice profile key
        rate: Speaking rate
        on_progress: Async callback(status_type, message)

    Returns:
        List of paths to generated MP3 files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = [output_dir / f"chapter_{i + 1:02d}.mp3" for i in range(len(chapters))]
    actual_voice = voice_key

    if on_progress:
        await on_progress(
            "tts",
            f"Vertone {len(chapters)} Kapitel parallel...",
            40
        )

    async def process_chapter(i: int, chapter: dict):
        nonlocal actual_voice
        full_text = chapter["text"]
        _, realized_voice = await generate_tts_chunk(full_text, audio_files[i], voice_key, rate)
        if realized_voice != voice_key:
            actual_voice = realized_voice

    # Run chapter generations concurrently
    # Premium voices (Gemini, OpenAI) are rate-limited: max 2 parallel chapters
    # Edge has no API limits: allow up to 10
    import asyncio
    is_premium = (voice_key in GEMINI_VOICES and not GEMINI_QUOTA_EXHAUSTED) or voice_key in OPENAI_VOICES
    concurrency_limit = 2 if is_premium else 10
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async def run_with_semaphore(i: int, ch: dict):
        async with semaphore:
            await process_chapter(i, ch)
            
    await asyncio.gather(*(run_with_semaphore(i, ch) for i, ch in enumerate(chapters)))

    return audio_files, actual_voice
