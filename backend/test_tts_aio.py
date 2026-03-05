import asyncio
import os
from pathlib import Path
import sys

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO)

async def main():
    from app.config import settings
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    text = "Dies ist ein Test für die Google Flash TTS."
    print("Starting generation...")
    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model='models/gemini-2.5-flash-preview-tts',
                contents=text,
                config=types.GenerateContentConfig(
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Aoede"
                            )
                        )
                    ),
                    response_modalities=["AUDIO"]
                )
            ),
            timeout=15
        )
        print("Generation finished successfully.")
        pcm_data = bytearray()
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                pcm_data.extend(part.inline_data.data)

        # Process with ffmpeg directly
        print("Processing with ffmpeg...")
        output_path = Path("test_aio_output.mp3")
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "s16le",
            "-ar", "24000",
            "-ac", "1",
            "-i", "pipe:0",
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate(input=bytes(pcm_data))
        
        if process.returncode != 0:
            print(f"FFmpeg failed: {stderr.decode('utf-8', errors='replace')}")
        else:
            print("Export finished successfully.")

    except Exception as e:
        print(f"Generation/Export failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
