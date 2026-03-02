import asyncio
import os
import tempfile
import subprocess
from pathlib import Path
from google import genai
from google.genai import types

async def test_ffmpeg():
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
            api_key = os.environ.get("GEMINI_API_KEY", "")
            
        client = genai.Client(api_key=api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='models/gemini-2.5-flash-preview-tts',
            contents='Dies ist ein Direkt-Test für FFmpeg.',
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
        )
        
        pcm_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                pcm_data = part.inline_data.data
                break
                
        if pcm_data:
            out = Path("c:/tmp/test_ffmpeg.mp3")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pcm") as tmp:
                tmp.write(pcm_data)
                tmp_path = tmp.name
                
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-f", "s16le",
                        "-ar", "24000",
                        "-ac", "1",
                        "-i", tmp_path,
                        "-c:a", "libmp3lame",
                        "-q:a", "2",
                        str(out),
                    ],
                    capture_output=True,
                    check=True,
                )
                print(f"Success! FFmpeg created MP3: {out.stat().st_size} bytes.")
            finally:
                os.unlink(tmp_path)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ffmpeg())
