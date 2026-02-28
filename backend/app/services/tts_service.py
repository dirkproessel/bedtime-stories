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

# OpenAI TTS voices
OPENAI_VOICES = {
    "shimmer": {"id": "shimmer", "name": "Shimmer", "gender": "female"},
    "onyx": {"id": "onyx", "name": "Onyx", "gender": "male"},
    "alloy": {"id": "alloy", "name": "Alloy", "gender": "neutral"},
    "echo": {"id": "echo", "name": "Echo", "gender": "male"},
    "fable": {"id": "fable", "name": "Fable", "gender": "neutral"},
    "nova": {"id": "nova", "name": "Nova", "gender": "female"},
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

    # OpenAI Voices
    for key, v in OPENAI_VOICES.items():
        voices.append({
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "openai",
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
    elif voice_key in OPENAI_VOICES:
        voice_config = OPENAI_VOICES[voice_key]
        engine = "openai"
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
            
            # Initialize client with API Key from settings
            client = texttospeech.TextToSpeechClient(
                client_options={"api_key": settings.GEMINI_API_KEY}
            )
            
            synthesis_input = texttospeech.SynthesisInput(text=clean_text)
            
            # Select the voice
            voice = texttospeech.VoiceSelectionParams(
                language_code="de-DE",
                name=voice_config["id"]
            )
            
            # Select the type of audio file you want returned
            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.95 if rate == "-5%" else 1.0,
                # Eliza (Neural2-G) slightly deeper if requested
                pitch=-1.5 if voice_key == "eliza" else 0.0
            )
            
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
        elif engine == "openai":
            # Direct OpenAI TTS API call via httpx to avoid library version/proxy issues
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "tts-1",
                "input": clean_text,
                "voice": voice_config["id"],
                "speed": 0.95 if rate == "-5%" else 1.0,
            }
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                with open(output_path, "wb") as out:
                    out.write(response.content)

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
            await on_progress(
                "tts",
                f"Vertone Kapitel {i + 1}/{len(chapters)}: {chapter['title']}",
            )

        filename = f"chapter_{i + 1:02d}.mp3"
        output_path = output_dir / filename

        # No title announcement as per user request, just the text.
        # AudioProcessor will handle the pause/merge.
        full_text = chapter["text"]

        await generate_tts_chunk(full_text, output_path, voice_key, rate)
        audio_files.append(output_path)

    return audio_files
