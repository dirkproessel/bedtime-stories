import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    AUDIO_OUTPUT_DIR: Path = Path(os.getenv("AUDIO_OUTPUT_DIR", "./audio_output"))

settings = Settings()
_stories_db_path = settings.AUDIO_OUTPUT_DIR / "stories.json"
print(f"STORIES_DB_PATH: {_stories_db_path.absolute()}")
print(f"EXISTS: {_stories_db_path.exists()}")
