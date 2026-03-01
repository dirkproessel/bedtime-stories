import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to sys.path so we can import app.services
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.services.image_generator import generate_story_image

async def main():
    load_dotenv(dotenv_path="backend/.env")
    tmp_path = Path("tmp/test_image.png")
    tmp_path.parent.mkdir(exist_ok=True)
    
    print("Testing image generation...")
    prompt = "A cute little dragon sleeping on a cloud"
    result = await generate_story_image(prompt, tmp_path)
    
    if result:
        print(f"Success! Image saved to {result}")
    else:
        print("Failed to generate image. Check logs/stdout.")

if __name__ == "__main__":
    asyncio.run(main())
