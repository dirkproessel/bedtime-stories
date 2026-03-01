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
    INTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "Intro.mp3"
    OUTRO_MUSIC_PATH: Path = Path(__file__).parent / "static" / "Outro.mp3"

    def __init__(self):
        self.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
