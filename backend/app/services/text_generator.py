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
    prompt: str | list, 
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
        # DeepSeek only supports text
        prompt_text = prompt if isinstance(prompt, str) else str(prompt)
        return await _generate_deepseek(prompt_text, model, temperature, max_tokens, response_mime_type, system_instruction, presence_penalty, frequency_penalty)
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
        # prompt can be a simple string or a list of parts
        # If it's a string, we wrap it in a list as the SDK expects
        formatted_contents = prompt if isinstance(prompt, list) else [prompt]

        # Using to_thread because the SDK might be blocking
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=model,
            contents=formatted_contents,
            config=config
        )
        
        # Diagnostic check for safety cutoffs or token budget limits
        if response.candidates:
            cand = response.candidates[0]
            finish_reason = getattr(cand, "finish_reason", None)
            if finish_reason:
                fr_str = str(finish_reason)
                # "1" or "STOP" is normal completion
                if fr_str not in ["STOP", "FinishReason.STOP", "1", "FinishReason.STOP_SEQUENCE"]:
                    logger.warning(
                        f"TEXT_GEN: Gemini model '{model}' finished with status: {fr_str}. "
                        f"If this is 'SAFETY' or 'MAX_TOKENS', the text was truncated mid-generation. "
                        f"Generated text length: {len(response.text or '')} characters."
                    )
        
        if response.text is not None:
            return response.text.strip()

        # Gather diagnostic info for None response.text
        finish_reason = "UNKNOWN"
        safety_info = ""
        if response.candidates:
            cand = response.candidates[0]
            if cand.finish_reason:
                finish_reason = str(cand.finish_reason)
            if cand.safety_ratings:
                blocked = [f"{r.category}: {r.probability}" for r in cand.safety_ratings if getattr(r, "blocked", False) or r.probability in ["MEDIUM", "HIGH"]]
                if blocked:
                    safety_info = f" | Blocked: {', '.join(blocked)}"
        
        err_msg = f"Gemini API returned empty/None text (Finish Reason: {finish_reason}{safety_info})"
        logger.error(f"{err_msg}. Full candidates structure: {response.candidates}")
        raise ValueError(err_msg)
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}")
        raise e

async def _generate_deepseek(prompt, model, temperature, max_tokens, response_mime_type, system_instruction, presence_penalty, frequency_penalty):
    """DeepSeek API call (OpenAI compatible) with automatic retry and error checks"""
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is missing in settings")

    # Map frontend model names to actual DeepSeek API model names
    if "pro" in model.lower() or "reasoner" in model.lower():
        api_model = "deepseek-reasoner"
    elif "flash" in model.lower() or "chat" in model.lower():
        api_model = "deepseek-chat"
    elif model.startswith("deepseek-v4"):
        api_model = model
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
        "stream": False
    }

    if api_model == "deepseek-reasoner":
        # DeepSeek Reasoner does NOT support temperature, presence_penalty, frequency_penalty
        # It also needs a high max_tokens budget (e.g. 8192) to fit CoT reasoning tokens + prose
        payload["max_tokens"] = 8192
    else:
        payload["temperature"] = temperature
        payload["max_tokens"] = max_tokens
        payload["presence_penalty"] = presence_penalty
        payload["frequency_penalty"] = frequency_penalty

    if response_mime_type == "application/json":
        # DeepSeek supports json_object for deepseek-chat
        if api_model == "deepseek-chat":
            payload["response_format"] = {"type": "json_object"}
        if "json" not in prompt.lower():
            prompt += " (Respond in JSON format)"
            messages[-1]["content"] = prompt

    max_retries = 3
    initial_delay = 5.0
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                choices = data.get("choices")
                if not choices:
                    raise ValueError(f"DeepSeek response contains no choices: {data}")
                
                message = choices[0].get("message")
                if not message:
                    raise ValueError(f"DeepSeek response choice contains no message: {data}")
                
                content = message.get("content")
                if content is None:
                    reasoning = message.get("reasoning_content", "")
                    raise ValueError(
                        f"DeepSeek returned reasoning but empty prose content. "
                        f"Reasoning length: {len(reasoning)} chars. "
                        f"Finish reason: {choices[0].get('finish_reason')}"
                    )
                
                return content.strip()
            except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as e:
                is_server_error = isinstance(e, httpx.HTTPStatusError) and e.response.status_code in [429, 500, 502, 503, 504]
                is_network_error = isinstance(e, httpx.RequestError)
                is_empty_content = isinstance(e, ValueError)
                
                if (is_server_error or is_network_error or is_empty_content) and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    logger.warning(f"DeepSeek attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"DeepSeek generation failed after {attempt + 1} attempts: {e}")
                    if hasattr(e, 'response') and e.response:
                        logger.error(f"Response: {e.response.text}")
                    raise e

