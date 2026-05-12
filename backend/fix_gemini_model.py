import os
import sys

# Add the backend directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select
from app.database import engine
from app.models import SystemSetting

def fix_model():
    with Session(engine) as session:
        statement = select(SystemSetting).where(SystemSetting.key == "gemini_text_model")
        setting = session.exec(statement).first()
        if setting:
            print(f"Current value: {setting.value}")
            if setting.value == "gemini-3.1-flash-lite-preview":
                print("Updating to gemini-3.1-flash-lite")
                setting.value = "gemini-3.1-flash-lite"
                session.add(setting)
                session.commit()
                print("Database updated.")
            else:
                print("No update needed.")
        else:
            print("No gemini_text_model setting found in DB. It will use defaults.")

if __name__ == "__main__":
    fix_model()
