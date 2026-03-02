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

# Google Cloud TTS Neural2 voices
GOOGLE_VOICES = {
    "eliza": {"id": "de-DE-Neural2-G", "name": "Eliza", "gender": "female"},
    "percy": {"id": "de-DE-Neural2-H", "name": "Percy", "gender": "male"},
}

# OpenAI TTS voices (Temporarily Disabled)
# OPENAI_VOICES = {
#     "shimmer": {"id": "shimmer", "name": "Shimmer", "gender": "female"},
#     "onyx": {"id": "onyx", "name": "Onyx", "gender": "male"},
#     "alloy": {"id": "alloy", "name": "Alloy", "gender": "neutral"},
#     "echo": {"id": "echo", "name": "Echo", "gender": "male"},
#     "fable": {"id": "fable", "name": "Fable", "gender": "neutral"},
#     "nova": {"id": "nova", "name": "Nova", "gender": "female"},
# }

# Gemini TTS voices
GEMINI_VOICES = {
    "aoede": {"id": "Aoede", "name": "Aoede", "gender": "female"},
    "enceladus": {"id": "Enceladus", "name": "Enceladus", "gender": "male"},
    "puck": {"id": "Puck", "name": "Puck", "gender": "male"},
    "charon": {"id": "Charon", "name": "Charon", "gender": "male"},
    "kore": {"id": "Kore", "name": "Kore", "gender": "female"},
}


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
        
    # Google Voices
    for key, v in GOOGLE_VOICES.items():
        voices.append({
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "google",
        })

    # OpenAI Voices (Temporarily Disabled)
    # for key, v in OPENAI_VOICES.items():
    #     voices.append({
    #         "key": key,
    #         "name": v["name"],
    #         "gender": v["gender"],
    #         "engine": "openai",
    #     })

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
) -> Path:
    """
    Convert text to speech and save as MP3.
    Supports Edge TTS, Google Cloud TTS, and OpenAI TTS.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Determine which engine to use
    if voice_key in GOOGLE_VOICES:
        voice_config = GOOGLE_VOICES[voice_key]
        engine = "google"
    # elif voice_key in OPENAI_VOICES:
    #     voice_config = OPENAI_VOICES[voice_key]
    #     engine = "openai"
    elif voice_key in GEMINI_VOICES:
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
        elif engine == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API Key is missing.")
            
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY.strip()}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "tts-1",
                "input": clean_text,
                "voice": voice_config["id"],
                "speed": 0.95 if rate == "-5%" else 1.0,
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                with open(output_path, "wb") as out:
                    out.write(response.content)

        elif engine == "gemini":
            from google import genai
            from google.genai import types
            import asyncio
            import wave
            import io
            
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Rate adjustment hint for Gemini
            speed_hint = " (Sprich ruhig und langsam)" if "-15%" in rate else ""
            
            # Split text into chunks < 4000 bytes (safety limit for Gemini API)
            def split_text(t, max_bytes=4000):
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

            for i, chunk in enumerate(text_chunks):
                logger.info(f"TTS Gemini: Processing chunk {i+1}/{len(text_chunks)} ({len(chunk.encode('utf-8'))} bytes)")
                
                response = await asyncio.to_thread(
                    client.models.generate_content,
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
                )
                
                pcm_data = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        pcm_data = part.inline_data.data
                        break
                        
                if not pcm_data:
                    raise RuntimeError(f"No audio data returned from Gemini TTS for voice {voice_key} on chunk {i+1}")
                
                all_pcm_data.extend(pcm_data)
                
            # Use native Python 'wave' module to write the fully accumulated valid WAV to the output_path 
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(1)      # Mono
                wav_file.setsampwidth(2)      # 16-bit
                wav_file.setframerate(24000)  # 24 kHz
                wav_file.writeframes(bytes(all_pcm_data))


        # Verify file was created and has content
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"TTS generated empty file for voice {voice_key}")

        logger.info(f"TTS: Generated {output_path.stat().st_size} bytes")
    except Exception as e:
        logger.error(f"TTS Error: {e}")
        raise

    return output_path


async def generate_voice_preview(
    voice_key: str,
    output_path: Path,
) -> Path:
    """Generate a short preview clip for a voice."""
    # Delete existing empty preview files so they get regenerated
    if output_path.exists() and output_path.stat().st_size == 0:
        output_path.unlink()

    preview_text = (
        "Hallo! Ich bin deine Gute-Nacht-Geschichte-Stimme. "
        "Komm, lass uns zusammen in ein Abenteuer eintauchen."
    )
    return await generate_tts_chunk(preview_text, output_path, voice_key)


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
    audio_files = []

    for i, chapter in enumerate(chapters):
        if on_progress:
            # TTS is 30% to 80%
            pct = 30 + int((i / len(chapters)) * 50)
            await on_progress(
                "tts",
                f"Vertone Kapitel {i + 1}/{len(chapters)}: {chapter['title']}",
                pct
            )

        filename = f"chapter_{i + 1:02d}.mp3"
        output_path = output_dir / filename

        # No title announcement as per user request, just the text.
        # AudioProcessor will handle the pause/merge.
        full_text = chapter["text"]

        await generate_tts_chunk(full_text, output_path, voice_key, rate)
        audio_files.append(output_path)

    return audio_files
