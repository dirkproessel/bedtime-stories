import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
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
    INTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "intro_storyja.mp3"
    OUTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "outro_storyja.mp3"

    # SMTP Settings (Gmail)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "dirk.proessel@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # Needs App Password
    KINDLE_EMAIL: str = os.getenv("KINDLE_EMAIL", "dirk.proessel.runthaler@kindle.com")

    # Central Model Configuration
    # GEMINI 3.0 FLASH (LATEST PREVIEW)
    GEMINI_TEXT_MODEL: str = "models/gemini-3-flash-preview"
    # GEMINI 2.5 FLASH IMAGE (NANO BANANA)
    GEMINI_IMAGE_MODEL: str = "gemini-2.5-flash-image"

    def __init__(self):
        self.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
