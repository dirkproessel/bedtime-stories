import logging
import asyncio
import httpx
import json
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Gemini Client
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Safety settings for Gemini
SAFETY_SETTINGS_CONFIG = [
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
]

async def generate_text(
    prompt: str, 
    model: str = None, 
    temperature: float = 0.8, 
    max_tokens: int = 4096, 
    response_mime_type: str = "text/plain",
    system_instruction: str = None,
    response_schema: dict = None,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0
) -> str:
    """
    Unified text generation function supporting Gemini and DeepSeek.
    """
    if not model:
        model = settings.GEMINI_TEXT_MODEL
    
    logger.info(f"TEXT_GEN: Using model {model} (Temp: {temperature}, MIME: {response_mime_type})")

    if model.startswith("gemini"):
        return await _generate_gemini(prompt, model, temperature, max_tokens, response_mime_type, system_instruction, response_schema, presence_penalty, frequency_penalty)
    elif model.startswith("deepseek"):
        return await _generate_deepseek(prompt, model, temperature, max_tokens, response_mime_type, system_instruction, presence_penalty, frequency_penalty)
    else:
        logger.warning(f"Unknown model prefix for '{model}'. Falling back to Gemini.")
        return await _generate_gemini(prompt, settings.GEMINI_TEXT_MODEL, temperature, max_tokens, response_mime_type, system_instruction, response_schema, presence_penalty, frequency_penalty)

async def _generate_gemini(prompt, model, temperature, max_tokens, response_mime_type, system_instruction, response_schema, presence_penalty, frequency_penalty):
    config = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "safety_settings": SAFETY_SETTINGS_CONFIG,
    }
    if response_mime_type == "application/json":
        config["response_mime_type"] = "application/json"
    
    if response_schema:
        config["response_schema"] = response_schema
    
    if system_instruction:
        config["system_instruction"] = system_instruction

    try:
        # Using to_thread because the SDK might be blocking
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=model,
            contents=prompt,
            config=config
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        raise e

async def _generate_deepseek(prompt, model, temperature, max_tokens, response_mime_type, system_instruction, presence_penalty, frequency_penalty):
    """DeepSeek API call (OpenAI compatible)"""
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is missing in settings")

    # Map frontend model names to actual DeepSeek API model names
    api_model = "deepseek-chat"
    if "pro" in model.lower() or "reasoner" in model.lower():
        api_model = "deepseek-reasoner"
    elif "flash" in model.lower():
        api_model = "deepseek-chat"
    else:
        api_model = model

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
    }
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": api_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "stream": False
    }

    if response_mime_type == "application/json":
        # DeepSeek supports json_object for deepseek-chat
        if api_model == "deepseek-chat":
            payload["response_format"] = {"type": "json_object"}
        if "json" not in prompt.lower():
            prompt += " (Respond in JSON format)"
            messages[-1]["content"] = prompt

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise e
