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
    logger.info(f"ENTERING generate_story_image for {output_path.name}")
    logger.info(f"Target path: {output_path.absolute()}")
    
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set in settings. Skipping image generation.")
        return None

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info(f"Generating image for story. Genre: {genre}, Style: {style}. Prompt length: {len(synopsis)}")
        
        # ... (style_hints and prompt logic remains same) ...
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
        clean_synopsis = synopsis.strip() or "A beautiful and magical scene based on the story theme"
        
        enhanced_prompt = (
            f"Anspruchsvolles Szene-Artwork: {clean_synopsis}. "
            f"Genre: {genre}. Visueller Stil: {genre_hint}, literarisch, hochwertig, ästhetisch ansprechend, keine Klischees. "
            f"Passend zum Schreibstil von {style}. Minimalistisch und modern. "
            f"WICHTIGE REGEL: KEIN TEXT! Generiere absolut keine Buchstaben, keine Wörter, keine Signaturen und keine Titel im Bild. Verwende ausschließlich reine Bildsprache."
        )

        model_id = 'imagen-4.0-fast-generate-001'
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

        logger.info(f"Imagen response received. Status: {getattr(response, 'status', 'N/A')}")

        if response.generated_images:
            logger.info("Success: Imagen generated at least one image.")
            generated_image = response.generated_images[0]
            
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            output_path.write_bytes(generated_image.image.image_bytes)
            logger.info(f"Image saved successfully to {output_path} (Size: {len(generated_image.image.image_bytes)} bytes)")
            return output_path
        else:
            rai_info = getattr(response, 'rai_reason', 'None/Unknown')
            logger.error(f"Imagen returned NO images. RAI reason: {rai_info}")
            return None

    except Exception as e:
        logger.error(f"CRITICAL: Image generation exception: {type(e).__name__}: {str(e)}", exc_info=True)
        return None
