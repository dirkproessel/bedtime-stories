import logging
from pathlib import Path
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

async def generate_story_image(synopsis: str, output_path: Path, genre: str = "Realismus", style: str = "Douglas Adams"):
    """
    Generate a square cover image for the story using Google's Imagen 3.
    Target format: 1024x1024 (Spotify-friendly).
    """
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Skipping image generation.")
        return None

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    try:
        logger.info(f"Generating image. Genre: {genre}, Style: {style}. Prompt length: {len(synopsis)}")
        
        # Professional Artistic Style Mapping
        style_hints = {
            "Sci-Fi": "Futuristic, cinematic concept art, neon accents, detailed textures",
            "Fantasy": "Epic oil painting, ethereal lighting, rich colors, intricate details",
            "Krimi": "Neo-noir, high contrast, dramatic shadows, moody atmosphere",
            "Abenteuer": "Vibrant exploration art, dynamic composition, warm light",
            "Realismus": "Fine art photography style, natural lighting, sharp focus",
            "Grusel": "Dark gothic art, misty, psychological horror aesthetic",
            "Dystopie": "Gritty, industrial, muted tones, post-apocalyptic vibe",
            "Satire": "Stylized editorial illustration, bold colors, ironic composition"
        }
        
        genre_hint = style_hints.get(genre, "Artistic illustration")
        
        enhanced_prompt = (
            f"Anspruchsvolles Buchcover-Artwork (ohne Text): {synopsis}. "
            f"Genre: {genre}. Visueller Stil: {genre_hint}, literarisch, hochwertig, ästhetisch ansprechend, keine Klischees. "
            f"Passend zum Schreibstil von {style}. Minimalistisch und modern."
        )

        # Note: generate_images is synchronous in the current google-genai SDK 
        # but we wrap it in a thread if needed, or just call it directly if it's not a heavy load.
        # For simplicity in this script, we call it directly.
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=enhanced_prompt,
            config=types.GenerateImagesConfig(
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
            logger.error(f"Google Imagen 3 returned no images. RAI: {getattr(response, 'rai_reason', 'N/A')}")
            return None

    except Exception as e:
        logger.error(f"CRITICAL: Google Imagen 3 error: {type(e).__name__}: {str(e)}", exc_info=True)
        return None
