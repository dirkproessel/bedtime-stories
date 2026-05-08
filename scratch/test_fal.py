import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import fal_client
import httpx

# Load env from backend
load_dotenv(dotenv_path=Path("../backend/.env"))

async def test_fal():
    print(f"FAL_KEY: {os.getenv('FAL_KEY')[:4]}...")
    prompt = "A cute little dragon sleeping on a cloud, fairytale style, high quality"
    output_path = Path("test_fal.png")
    
    print("Generating image with fal.ai...")
    try:
        result = await fal_client.run_async(
            "fal-ai/flux/schnell",
            arguments={
                "prompt": prompt,
                "image_size": "square_hd"
            }
        )
        
        if result and "images" in result and len(result["images"]) > 0:
            image_url = result["images"][0]["url"]
            print(f"Image URL: {image_url}")
            async with httpx.AsyncClient() as client:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    output_path.write_bytes(resp.content)
                    print(f"Image saved to {output_path}")
                else:
                    print(f"Failed to download image: {resp.status_code}")
        else:
            print(f"No image returned: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_fal())
