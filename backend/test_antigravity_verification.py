import asyncio
from pathlib import Path
import logging
import sys
import os

# Add backend to sys.path to import app
sys.path.append(os.getcwd())

from app.services.image_generator import generate_story_image
from app.config import settings

logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing Antigravity Image Generation...")
    output = Path("test_antigravity_final.png")
    if output.exists():
        output.unlink()
        
    res = await generate_story_image(
        synopsis="Eine kleine Maus fliegt zum Mond in einem Käse-Raumschiff.",
        output_path=output,
        genre="Fantasy",
        style="Pixar"
    )
    
    if res and output.exists():
        print(f"SUCCESS: Image saved to {res}")
    else:
        print("FAILED: Image generation did not produce a file.")

if __name__ == "__main__":
    asyncio.run(test())
