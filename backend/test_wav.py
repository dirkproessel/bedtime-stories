import asyncio
import os
import wave
from pathlib import Path
from google import genai
from google.genai import types

async def test_native_wav():
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
            api_key = os.environ.get("GEMINI_API_KEY", "")
            
        client = genai.Client(api_key=api_key)
        print("Generating audio via Gemini...")
        response = await asyncio.to_thread(
            client.models.generate_content,
            model='models/gemini-2.5-flash-preview-tts',
            contents='Dies ist ein Direkt-Test für die native WAV-Erzeugung im Browser.',
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
            out_path = Path("c:/tmp/test_native.wav")
            # Gemini returns 24kHz, 16-bit, Mono PCM
            with wave.open(str(out_path), 'wb') as wav_file:
                wav_file.setnchannels(1)      # Mono
                wav_file.setsampwidth(2)      # 16-bit
                wav_file.setframerate(24000)  # 24 kHz
                wav_file.writeframes(pcm_data)
                
            print(f"Success! Native WAV created: {out_path.stat().st_size} bytes.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_native_wav())
