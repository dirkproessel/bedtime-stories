import os
from google import genai
from google.genai import types
from pydub import AudioSegment

try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        from dotenv import load_dotenv
        load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
    client = genai.Client(api_key=api_key)
    print("Generating audio...")
    response = client.models.generate_content(
        model='models/gemini-2.5-flash-preview-tts',
        contents='Dies ist ein Funktionstest für die MP3 Konvertierung.',
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
            print(f"Got {len(pcm_data)} bytes of PCM data.")
            break
            
    if pcm_data:
        # L16 means 16-bit (2 bytes sample width), little-endian. 
        # Usually API returns raw PCM. 
        audio = AudioSegment(
            data=pcm_data,
            sample_width=2,
            frame_rate=24000,
            channels=1
        )
        audio.export("c:/tmp/test_gemini.mp3", format="mp3")
        print("Successfully exported test_gemini.mp3")
        
except Exception as e:
    print(f"Error: {e}")
