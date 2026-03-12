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
        logger.warning("GEMINI_API_KEY not set in settings. Skipping image generation.")
        return None

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info(f"Generating image for story. Genre: {genre}, Style: {style}. Prompt length: {len(synopsis)}")
        
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
            f"Anspruchsvolles Szene-Artwork: {synopsis}. "
            f"Genre: {genre}. Visueller Stil: {genre_hint}, literarisch, hochwertig, ästhetisch ansprechend, keine Klischees. "
            f"Passend zum Schreibstil von {style}. Minimalistisch und modern. "
            f"WICHTIGE REGEL: KEIN TEXT! Generiere absolut keine Buchstaben, keine Wörter, keine Signaturen und keine Titel im Bild. Verwende ausschließlich reine Bildsprache."
        )

        # Use high-quality Imagen 3.0 Standard for better reliability
        model_id = 'imagen-3.0-generate-001'
        logger.info(f"Using Google Image model: {model_id}")
        
        response = client.models.generate_images(
            model=model_id,
            prompt=enhanced_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                include_rai_reason=True,
                output_mime_type='image/png'
            )
        )

        if response.generated_images:
            generated_image = response.generated_images[0]
            output_path.write_bytes(generated_image.image.image_bytes)
            logger.info(f"Image saved successfully to {output_path}")
            return output_path
        else:
            # Enhanced RAI logging
            rai_info = "Unknown"
            if hasattr(response, 'rai_reason'):
                rai_info = response.rai_reason
            
            logger.error(f"Imagen returned no images. Potential RAI filter block? Reason: {rai_info}")
            
            # Detailed response debugging
            try:
                import json
                # Try to log as much as possible about the failure
                resp_dict = str(response)
                logger.debug(f"Full response metadata: {resp_dict}")
            except Exception as e_log:
                logger.debug(f"Could not log full response: {e_log}")
            return None

    except Exception as e:
        logger.error(f"CRITICAL: Image generation error: {type(e).__name__}: {str(e)}")
        # Check for specific error types like permissions or quota
        if "quota" in str(e).lower():
            logger.error("Quota exceeded for Image generation.")
        elif "permission" in str(e).lower():
            logger.error("Permission denied for Image generation. Check API Key/Project.")
        return None
