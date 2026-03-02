import asyncio
import os
import wave
from pathlib import Path
from dotenv import load_dotenv

async def main():
    load_dotenv("c:/Dirk/Codings/bedtime-stories/backend/.env")
    
    from app.services.tts_service import generate_tts_chunk
    from app.services.audio_processor import merge_audio_files
    
    # 1. Create a dummy long text (approx 2000 words, which would be ~10 minutes)
    chunk1_text = "Hallo dies ist ein Test. " * 500
    chunk2_text = "Ein zweiter Teil des Tests. " * 500
    
    print(f"Text length: Chunk 1 ({len(chunk1_text)} chars), Chunk 2 ({len(chunk2_text)} chars)")
    
    out1 = Path("c:/tmp/test_gTTS_chunk1.wav")
    out2 = Path("c:/tmp/test_gTTS_chunk2.wav")
    out_merged = Path("c:/tmp/test_gTTS_merged.mp3")
    
    try:
        print("Generating chunk 1...")
        await generate_tts_chunk(chunk1_text, out1, voice_key="aoede")
        print(f"Chunk 1 generated: {out1.stat().st_size} bytes")
        
        print("Generating chunk 2...")
        await generate_tts_chunk(chunk2_text, out2, voice_key="aoede")
        print(f"Chunk 2 generated: {out2.stat().st_size} bytes")
        
        print("Merging chunks...")
        await merge_audio_files([out1, out2], out_merged)
        print(f"Merged audio generated: {out_merged.stat().st_size} bytes")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
