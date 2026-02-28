import logging
import asyncio
from pathlib import Path
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

async def generate_story_image(prompt: str, output_path: Path):
    """
    Generate a square cover image for the story using OpenAI's DALL-E 3.
    Target format: 1024x1024 (Spotify-friendly).
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. Skipping image generation.")
        return None

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    try:
        logger.info(f"Generating image for prompt: {prompt[:100]}...")
        
        # Optimize prompt for cover art
        enhanced_prompt = (
            f"Bilderbuch-Illustration für eine Kinder-Gute-Nacht-Geschichte: {prompt}. "
            f"Stil: märchenhaft, sanfte Farben, verträumt, hochwertig, warmes Licht. "
            f"Quadratisches Format ohne Text."
        )

        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="url"
        )

        image_url = response.data[0].url
        
        # Download image
        import httpx
        async with httpx.AsyncClient() as http_client:
            res = await http_client.get(image_url)
            if res.status_code == 200:
                output_path.write_bytes(res.content)
                logger.info(f"Image saved to {output_path}")
                return output_path
            else:
                logger.error(f"Failed to download generated image: {res.status_code}")
                return None

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None
