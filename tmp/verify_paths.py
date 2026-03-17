import sys
from pathlib import Path

# Add backend to path to import config
sys.path.append(str(Path.cwd() / "backend"))

try:
    from app.config import settings
    
    intro = settings.INTRO_MUSIC_PATH
    outro = settings.OUTRO_MUSIC_PATH
    
    print(f"Intro Path: {intro}")
    print(f"Intro Exists: {intro.exists()}")
    
    print(f"Outro Path: {outro}")
    print(f"Outro Exists: {outro.exists()}")
    
    if intro.exists() and outro.exists():
        print("SUCCESS: Both files found!")
    else:
        print("FAILURE: One or both files missing!")
        sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
