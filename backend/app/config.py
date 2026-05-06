import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Text model: Gemini 3 Flash Preview (upgraded 2026-04-15 for better quality at same price)
    GEMINI_TEXT_MODEL: str = os.getenv("GEMINI_TEXT_MODEL", "gemini-3-flash-preview")
    # Image model: Nano Banana 2 (upgraded 2026-04-15, 512px output for cost efficiency)
    GEMINI_IMAGE_MODEL: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    # Detect old/new admin credentials with explicit logging
    _env_admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("POCKETBASE_ADMIN_EMAIL")
    _env_admin_pass = os.getenv("ADMIN_PASSWORD") or os.getenv("POCKETBASE_ADMIN_PASSWORD")
    
    # Debug: Log what keys are actually found (sanitized)
    _all_keys = os.environ.keys()
    _found_keys = [k for k in _all_keys if "ADMIN" in k or "POCKETBASE" in k or "KINDLE" in k]
    print(f"DEBUG ENV: Found keys: {_found_keys}")
    
    ADMIN_EMAIL: str = (_env_admin_email or "").strip()
    ADMIN_PASSWORD: str = (_env_admin_pass or "").strip()
    
    # Emergency Fallback: If environment is misconfigured, ensure Dirk still has access
    if not ADMIN_EMAIL:
        print("CRITICAL: ADMIN_EMAIL not found in environment! Using safety fallback.")
        ADMIN_EMAIL = "dirk.proessel@web.de"
    
    if not ADMIN_PASSWORD:
        # We don't hardcode the password, but we warn loudly. 
        # The store.py seeding will skip if password is missing.
        print("WARNING: ADMIN_PASSWORD not found in environment!")
    
    AUDIO_OUTPUT_DIR: Path = Path(os.getenv("AUDIO_OUTPUT_DIR", "./audio_output"))
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    FISH_API_KEY: str = os.getenv("FISH_API_KEY", "")
    XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
    INTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "intro_storyja.mp3"
    OUTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "outro_storyja.mp3"

    # SMTP Settings (Gmail)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "dirk.proessel@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # Needs App Password
    SMTP_FROM: str = os.getenv("SMTP_FROM", "stories@storyja.com")
    KINDLE_EMAIL: str = os.getenv("KINDLE_EMAIL", "dirk.proessel.runthaler@kindle.com")

    # Alexa Settings
    ALEXA_CLIENT_ID: str = os.getenv("ALEXA_CLIENT_ID", "")
    ALEXA_CLIENT_SECRET: str = os.getenv("ALEXA_CLIENT_SECRET", "")
    ALEXA_DEFAULT_USER_ID: str = os.getenv("ALEXA_DEFAULT_USER_ID", "") # Fallback Admin ID
    ALEXA_ALLOW_GUESTS: bool = os.getenv("ALEXA_ALLOW_GUESTS", "true").lower() == "true"
    ALEXA_SKILL_STAGE: str = os.getenv("ALEXA_SKILL_STAGE", "development") # 'development' or 'live'
    ALEXA_NOTIFICATION_STYLE: str = os.getenv("ALEXA_NOTIFICATION_STYLE", "media") # 'media', 'message', or 'occasion'

    def __init__(self):
        self.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
