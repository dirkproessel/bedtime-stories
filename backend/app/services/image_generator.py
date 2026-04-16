import asyncio
import logging
from pathlib import Path
from google import genai
from google.genai import types
from app.config import settings
from app.services.store import store

logger = logging.getLogger(__name__)

SAFETY_SETTINGS_CONFIG = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
]

async def get_visual_prompt(client: genai.Client, synopsis: str, genre: str, style: str, image_hints: str | None = None) -> str:
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
    {f"USER SPECIFIC HINTS: {image_hints} (Incorporate these hints into the visual description if they are provided, but maintain the overall style and rules.)" if image_hints else ""}

    RULES for the output:
    1. Output ONLY the English visual description. No introductory text.
    2. Focus on: Composition, lighting, colors, mood, and specific key elements from the story.
    3. ABSOLUTELY NO TEXT: Do not include words like "text", "letters", "title", "written", "signature" or anything that might lead the generator to put typography in the image.
    4. SAFETY: Avoid any controversial, sensitive, or protected terms. Use pure artistic metaphors if necessary.
    5. Language: English.
    """
    
    try:
        # Get current model from DB or fallback to config
        text_model = store.get_system_setting("gemini_text_model", settings.GEMINI_TEXT_MODEL)
        
        response = client.models.generate_content(
            model=text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=SAFETY_SETTINGS_CONFIG,
            )
        )
        visual_desc = response.text.strip()
        logger.info(f"Gemini generated visual description (first 100 chars): {visual_desc[:100]}...")
        return visual_desc
    except Exception as e:
        logger.error(f"Error generating visual prompt with Gemini: {e}")
        # Fallback to something that includes context if possible
        return f"A high-quality, atmospheric artistic illustration in the {genre} genre, reflecting the mood of {style}."

async def generate_story_image(synopsis: str, output_path: Path, genre: str = "Realismus", style: str = "Douglas Adams", image_hints: str | None = None):
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
        visual_description = await get_visual_prompt(client, synopsis, genre, style, image_hints)
        
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
            f"Focus on pure visual storytelling without any typography. "
            f"Seamless edge-to-edge full-bleed artwork. The composition must fill the entire canvas completely."
        )

        # Get current model from DB or fallback to config
        model_id = store.get_system_setting("gemini_image_model", settings.GEMINI_IMAGE_MODEL)
        logger.info(f"Using Google Image model: {model_id}")
        logger.info(f"Final Enhanced Prompt: {enhanced_prompt}")
        
        async def call_nano_banana(prompt_text):
            return await asyncio.to_thread(
                client.models.generate_content,
                model=model_id,
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        image_size="512",  # 512px output = 747 tokens vs 1120 tokens at 1K
                    ),
                    safety_settings=SAFETY_SETTINGS_CONFIG,
                )
            )

        # Attempt 1: Full optimized prompt
        response = await call_nano_banana(enhanced_prompt)
        
        # Helper to extract image from response
        def get_image_bytes(resp):
            if resp.candidates:
                for candidate in resp.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.inline_data and part.inline_data.data:
                                return part.inline_data.data
            return None

        image_bytes = get_image_bytes(response)
        
        # Attempt 2: Fallback if attempt 1 was filtered or failed
        if not image_bytes:
            logger.warning(f"{model_id} attempt 1 failed to return an image. Retrying with simplified fallback...")
            
            fallback_prompt = (
                f"STRICT RULE: NO TEXT, NO WORDS, NO LETTERS, NO SIGNATURES. "
                f"{visual_description}. Aesthetic artistic illustration, high quality, no text. "
                f"Seamless edge-to-edge full-bleed artwork. The composition must fill the entire canvas completely."
            )
            response = await call_nano_banana(fallback_prompt)
            image_bytes = get_image_bytes(response)

        if image_bytes:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image_bytes)
            logger.info(f"Image saved successfully to {output_path} (Size: {len(image_bytes)} bytes)")
            return output_path
        else:
            logger.error(f"{model_id} returned NO images after all attempts.")
            return None

    except Exception as e:
        logger.error(f"CRITICAL: Image generation exception: {type(e).__name__}: {str(e)}", exc_info=True)
        return None
