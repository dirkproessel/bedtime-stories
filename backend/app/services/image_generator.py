import logging
from pathlib import Path
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

async def generate_story_image(prompt: str, output_path: Path):
    """
    Generate a square cover image for the story using Google's Imagen 3.
    Target format: 1024x1024 (Spotify-friendly).
    Uses the free Google AI Studio (Gemini) API.
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Skipping image generation.")
        return None

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    try:
        logger.info(f"Generating image via Google Imagen 3 for: {prompt[:100]}...")
        
        # Optimize prompt for cover art
        enhanced_prompt = (
            f"Bilderbuch-Illustration für eine Kinder-Gute-Nacht-Geschichte: {prompt}. "
            f"Stil: märchenhaft, sanfte Farben, verträumt, hochwertig, warmes Licht. "
            f"Quadratisches Format ohne Text."
        )

        # Note: generate_image is synchronous in the current google-genai SDK 
        # but we wrap it in a thread if needed, or just call it directly if it's not a heavy load.
        # For simplicity in this script, we call it directly.
        response = client.models.generate_image(
            model='imagen-3.0-generate-001',
            prompt=enhanced_prompt,
            config=types.GenerateImageConfig(
                number_of_images=1,
                include_rai_reason=True,
                output_mime_type='image/png'
            )
        )

        if response.generated_images:
            # The SDK returns a list of GeneratedImage objects
            generated_image = response.generated_images[0]
            # Save the image bytes to path
            output_path.write_bytes(generated_image.image.image_bytes)
            logger.info(f"Google Imagen 3 image saved to {output_path}")
            return output_path
        else:
            logger.error("Google Imagen 3 returned no images.")
            return None

    except Exception as e:
        logger.error(f"Error generating image with Google Imagen 3: {e}")
        return None
