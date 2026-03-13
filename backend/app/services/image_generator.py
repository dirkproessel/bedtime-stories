import logging
from pathlib import Path
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

async def get_visual_prompt(client: genai.Client, synopsis: str, genre: str, style: str) -> str:
    """
    Use Gemini to transform a German synopsis into a visually descriptive English image prompt.
    """
    prompt = f"""
    You are an expert at creating visual prompts for AI image generators.
    Convert the following story synopsis into a high-quality, visually descriptive English prompt.

    STORY SYNOPSIS (German):
    {synopsis}

    GENRE: {genre}
    STYLE HINTS: {style}

    RULES for the output:
    1. Output ONLY the English visual description. No introductory text.
    2. Focus on: Composition, lighting, colors, mood, and specific key elements from the story.
    3. ABSOLUTELY NO TEXT: Do not include words like "text", "letters", "title", "written", "signature" or anything that might lead the generator to put typography in the image.
    4. SAFETY: Avoid any controversial, sensitive, or protected terms. Use pure artistic metaphors if necessary.
    5. Language: English.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        visual_desc = response.text.strip()
        logger.info(f"Gemini generated visual description (first 100 chars): {visual_desc[:100]}...")
        return visual_desc
    except Exception as e:
        logger.error(f"Error generating visual prompt with Gemini: {e}")
        return "A high-quality, atmospheric and artistic illustration representing the story's theme."

async def generate_story_image(synopsis: str, output_path: Path, genre: str = "Realismus", style: str = "Douglas Adams"):
    """
    Generate a square cover image for the story using Google's Imagen.
    Uses Gemini to optimize the prompt for the best visual results.
    """
    logger.info(f"ENTERING generate_story_image for {output_path.name}")
    
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set in settings. Skipping image generation.")
        return None

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Step 1: Use LLM to generate a safe, visual English prompt
        visual_description = await get_visual_prompt(client, synopsis, genre, style)
        
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
        
        # Construct the final prompt for Imagen
        enhanced_prompt = (
            f"STRICT RULE: NO TEXT, NO WORDS, NO LETTERS, NO SIGNATURES, NO TITLES, NO WATERMARKS. "
            f"Style: {genre_hint}. {visual_description}. "
            f"Minimalist and modern aesthetic, matching the tone of {style}. "
            f"Focus on pure visual storytelling without any typography."
        )

        model_id = 'imagen-4.0-fast-generate-001'
        logger.info(f"Using Google Image model: {model_id}")
        logger.info(f"Final Enhanced Prompt: {enhanced_prompt}")
        
        async def call_imagen(prompt_text):
            return client.models.generate_images(
                model=model_id,
                prompt=prompt_text,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    include_rai_reason=True,
                    output_mime_type='image/png'
                )
            )

        # Attempt 1: Full optimized prompt
        response = await call_imagen(enhanced_prompt)
        
        # Attempt 2: Fallback if attempt 1 was filtered
        if not response.generated_images or not response.generated_images[0].image or not response.generated_images[0].image.image_bytes:
            rai_info = getattr(response, 'rai_reason', 'None/Unknown')
            logger.warning(f"Imagen 4.0 attempt 1 filtered/failed (RAI: {rai_info}). Retrying with simplified fallback...")
            
            fallback_prompt = (
                f"STRICT RULE: NO TEXT, NO WORDS, NO LETTERS, NO SIGNATURES. "
                f"{visual_description}. Aesthetic artistic illustration, high quality, no text."
            )
            response = await call_imagen(fallback_prompt)

        if response.generated_images:
            generated_image = response.generated_images[0]
            
            if not generated_image.image or not generated_image.image.image_bytes:
                rai_info = getattr(response, 'rai_reason', 'None/Unknown')
                logger.error(f"Imagen 4.0 fully blocked (RAI: {rai_info}) even after retry.")
                return None

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(generated_image.image.image_bytes)
            logger.info(f"Image saved successfully to {output_path} (Size: {len(generated_image.image.image_bytes)} bytes)")
            return output_path
        else:
            logger.error("Imagen 4.0 returned NO images after all attempts.")
            return None

    except Exception as e:
        logger.error(f"CRITICAL: Image generation exception: {type(e).__name__}: {str(e)}", exc_info=True)
        return None
