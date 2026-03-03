import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    POCKETBASE_URL: str = os.getenv("POCKETBASE_URL", "http://localhost:8090")
    POCKETBASE_ADMIN_EMAIL: str = os.getenv("POCKETBASE_ADMIN_EMAIL", "")
    POCKETBASE_ADMIN_PASSWORD: str = os.getenv("POCKETBASE_ADMIN_PASSWORD", "")
    AUDIO_OUTPUT_DIR: Path = Path(os.getenv("AUDIO_OUTPUT_DIR", "./audio_output"))
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    INTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "intro_new.mp3"
    OUTRO_MUSIC_PATH: Path | None = None

    # SMTP Settings (Gmail)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "dirk.proessel@gmail.com")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # Needs App Password
    KINDLE_EMAIL: str = os.getenv("KINDLE_EMAIL", "dirk.proessel.runthaler@kindle.com")

    def __init__(self):
        self.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
