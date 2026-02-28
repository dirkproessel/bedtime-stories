"""
Audio post-processing: merge MP3 chunks, add silence between chapters,
normalize loudness via FFmpeg.
"""

import subprocess
import tempfile
from pathlib import Path


def _create_silence(duration_ms: int, output_path: Path) -> Path:
    """Generate a silent MP3 of given duration."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=24000:cl=mono",
            "-t", str(duration_ms / 1000),
            "-c:a", "libmp3lame",
            "-q:a", "5",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    return output_path


def merge_audio_files(
    audio_files: list[Path],
    output_path: Path,
    intro_path: Path | None = None,
    outro_path: Path | None = None,
    title_path: Path | None = None,
    silence_between_ms: int = 2500,
    fade_out_ms: int = 3000,
) -> Path:
    """
    Merge multiple MP3 files with optional intro/outro, title announcement and normalization.

    Args:
        audio_files: List of MP3 file paths (in order)
        output_path: Final output MP3 path
        intro_path: Path to Intro MP3 (optional)
        outro_path: Path to Outro MP3 (optional)
        title_path: Path to Title TTS MP3 (optional)
        silence_between_ms: Milliseconds of silence between chapters
        fade_out_ms: Fade-out duration at the end in ms
    """
    if not audio_files:
        raise ValueError("No audio files provided")

    if len(audio_files) == 1:
        # Single file: just normalize
        _normalize_audio(audio_files[0], output_path, fade_out_ms)
        return output_path

    # Create a temporary concat file and silence file
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        silence_path = tmpdir / "silence.mp3"
        _create_silence(silence_between_ms, silence_path)

        # Create FFmpeg concat list
        concat_list = tmpdir / "concat.txt"
        lines = []

        # 1. Intro
        if intro_path and intro_path.exists():
            lines.append(f"file '{intro_path.resolve()}'")
            lines.append(f"file '{silence_path.resolve()}'")

        # 1.5 Title Announcement
        if title_path and title_path.exists():
            lines.append(f"file '{title_path.resolve()}'")
            lines.append(f"file '{silence_path.resolve()}'")

        # 2. Chapters
        for i, af in enumerate(audio_files):
            lines.append(f"file '{af.resolve()}'")
            if i < len(audio_files) - 1:
                lines.append(f"file '{silence_path.resolve()}'")
            elif outro_path and outro_path.exists():
                # Silence before outro if it exists
                lines.append(f"file '{silence_path.resolve()}'")

        # 3. Outro
        if outro_path and outro_path.exists():
            lines.append(f"file '{outro_path.resolve()}'")

        concat_list.write_text("\n".join(lines), encoding="utf-8")

        # Concatenate
        merged_raw = tmpdir / "merged_raw.mp3"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c:a", "libmp3lame",
                "-q:a", "2",
                str(merged_raw),
            ],
            capture_output=True,
            check=True,
        )

        # Normalize + fade out
        _normalize_audio(merged_raw, output_path, fade_out_ms)

    return output_path


def _normalize_audio(input_path: Path, output_path: Path, fade_out_ms: int = 3000):
    """Normalize loudness and optionally apply fade-out."""
    # Get duration for fade-out calculation
    probe = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        capture_output=True,
        text=True,
    )
    duration = float(probe.stdout.strip())
    fade_start = max(0, duration - (fade_out_ms / 1000))

    # Normalize loudness (EBU R128) + fade out
    filter_chain = (
        f"loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"afade=t=out:st={fade_start}:d={fade_out_ms / 1000}"
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", filter_chain,
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )


def get_audio_duration(file_path: Path) -> float:
    """Get duration of an audio file in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())
