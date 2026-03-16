import asyncio
import subprocess
import tempfile
from pathlib import Path


async def _create_silence(duration_ms: int, output_path: Path) -> Path:
    """Generate a silent MP3 of given duration."""
    await asyncio.to_thread(
        subprocess.run,
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration_ms / 1000),
            "-c:a", "libmp3lame",
            "-b:a", "64k",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    return output_path


async def merge_audio_files(
    audio_files: list[Path],
    output_path: Path,
    intro_path: Path | None = None,
    outro_path: Path | None = None,
    title_path: Path | None = None,
    silence_between_ms: int = 1000,
    fade_out_ms: int = 0,
) -> Path:
    """
    Merge multiple MP3 files with optional intro/outro, title announcement and normalization.
    """
    if not audio_files:
        raise ValueError("No audio files provided")

    if len(audio_files) == 1:
        # Single file: just normalize
        await _normalize_audio(audio_files[0], output_path, fade_out_ms)
        return output_path

    # We will use FFmpeg's filter_complex concat which is much more robust
    # against different sample rates and formats than the concat demuxer.
    # ignore_cleanup_errors=True is critical on Windows to prevent WinError 32
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        tmpdir = Path(tmpdir)
        silence_path = tmpdir / "silence.mp3"
        await _create_silence(silence_between_ms, silence_path)

        # ... (rest of input gathering logic) ...
        # [Merging logic continues here as before] ...
        
        # [I will keep the logic same but nested in the new TemporaryDirectory]
        # Build list of input files in exact order
        inputs = []
        
        # 1. Intro
        if intro_path and intro_path.exists():
            inputs.append(intro_path)
            inputs.append(silence_path)

        # 1.5 Title Announcement
        if title_path and title_path.exists():
            inputs.append(title_path)
            inputs.append(silence_path)

        # 2. Chapters
        for i, af in enumerate(audio_files):
            inputs.append(af)
            if i < len(audio_files) - 1:
                inputs.append(silence_path)
            elif outro_path and outro_path.exists():
                inputs.append(silence_path)

        # 3. Outro
        if outro_path and outro_path.exists():
            inputs.append(silence_path) # Extrapause vor dem Outro
            inputs.append(outro_path)

        # 4. Final pause
        inputs.append(silence_path)

        # Construct FFmpeg command
        cmd = ["ffmpeg", "-y"]
        for inp in inputs:
            cmd.extend(["-i", str(inp.resolve())])
            
        # Build filter_complex string: standardize each input individually first
        filter_str = ""
        for i in range(len(inputs)):
            filter_str += f"[{i}:a]aresample=44100,aformat=sample_fmts=s16:channel_layouts=stereo[a{i}];"
            
        # Then concatenate the normalized streams
        concat_inputs = "".join([f"[a{i}]" for i in range(len(inputs))])
        filter_str += f"{concat_inputs}concat=n={len(inputs)}:v=0:a=1[outa]"
        
        cmd.extend(["-filter_complex", filter_str, "-map", "[outa]"])
        
        merged_raw = tmpdir / "merged_raw.mp3"
        cmd.extend([
            "-c:a", "libmp3lame",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "64k",
            str(merged_raw)
        ])

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg merging failed with exit status {result.returncode}:\n{result.stderr}")

        # Normalize + fade out
        await _normalize_audio(merged_raw, output_path, fade_out_ms)

        # On Windows, give the OS a moment to release file handles before cleanup starts
        await asyncio.sleep(0.5)

    return output_path


async def _normalize_audio(input_path: Path, output_path: Path, fade_out_ms: int = 0):
    """Normalize loudness and optionally apply fade-out."""
    if fade_out_ms > 0:
        # Get duration for fade-out calculation
        probe = await asyncio.to_thread(
            subprocess.run,
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
    else:
        filter_chain = f"loudnorm=I=-16:TP=-1.5:LRA=11"

    await asyncio.to_thread(
        subprocess.run,
        [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-af", filter_chain,
            "-c:a", "libmp3lame",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", "64k",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )


async def get_audio_duration(file_path: Path) -> float:
    """Get duration of an audio file in seconds."""
    result = await asyncio.to_thread(
        subprocess.run,
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
