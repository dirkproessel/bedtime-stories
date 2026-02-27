"""
Text-to-Speech service supporting Edge TTS and Google Cloud TTS.
Generates MP3 chunks per chapter.
"""

import edge_tts
from pathlib import Path

# Available Edge TTS German voices (DE, AT, CH)
EDGE_VOICES = {
    # Deutschland – Multilingual (natürlicher)
    "seraphina": {"id": "de-DE-SeraphinaMultilingualNeural", "name": "Seraphina", "gender": "female", "accent": "DE", "style": "Multilingual"},
    "florian": {"id": "de-DE-FlorianMultilingualNeural", "name": "Florian", "gender": "male", "accent": "DE", "style": "Multilingual"},
    # Deutschland – Standard
    "amala": {"id": "de-DE-AmalaNeural", "name": "Amala", "gender": "female", "accent": "DE", "style": "Standard"},
    "conrad": {"id": "de-DE-ConradNeural", "name": "Conrad", "gender": "male", "accent": "DE", "style": "Standard"},
    "katja": {"id": "de-DE-KatjaNeural", "name": "Katja", "gender": "female", "accent": "DE", "style": "Standard"},
    "killian": {"id": "de-DE-KillianNeural", "name": "Killian", "gender": "male", "accent": "DE", "style": "Standard"},
    # Österreich
    "ingrid": {"id": "de-AT-IngridNeural", "name": "Ingrid", "gender": "female", "accent": "AT", "style": "Österreichisch"},
    "jonas": {"id": "de-AT-JonasNeural", "name": "Jonas", "gender": "male", "accent": "AT", "style": "Österreichisch"},
    # Schweiz
    "leni": {"id": "de-CH-LeniNeural", "name": "Leni", "gender": "female", "accent": "CH", "style": "Schweizerdeutsch"},
    "jan": {"id": "de-CH-JanNeural", "name": "Jan", "gender": "male", "accent": "CH", "style": "Schweizerdeutsch"},
}

DEFAULT_VOICE = "katja"


def get_available_voices() -> list[dict]:
    """Return list of available voice profiles."""
    return [
        {
            "key": key,
            "name": v["name"],
            "gender": v["gender"],
            "engine": "edge",
            "accent": v.get("accent", "DE"),
            "style": v.get("style", "Standard"),
        }
        for key, v in EDGE_VOICES.items()
    ]


async def generate_tts_chunk(
    text: str,
    output_path: Path,
    voice_key: str = DEFAULT_VOICE,
    rate: str = "-5%",
) -> Path:
    """
    Convert text to speech and save as MP3.
    """
    import logging
    logger = logging.getLogger(__name__)

    voice = EDGE_VOICES.get(voice_key, EDGE_VOICES[DEFAULT_VOICE])
    logger.info(f"TTS: Generating audio with voice {voice['id']} -> {output_path}")

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice["id"],
            rate=rate,
        )
        await communicate.save(str(output_path))

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

        # Add chapter title announcement before text
        full_text = f"Kapitel {i + 1}. {chapter['title']}. ... {chapter['text']}"

        await generate_tts_chunk(full_text, output_path, voice_key, rate)
        audio_files.append(output_path)

    return audio_files
