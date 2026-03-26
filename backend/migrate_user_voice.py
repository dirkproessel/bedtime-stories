import asyncio
from sqlmodel import Session, select
import sys
import os

# Add the app directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.models import User

async def migrate_user_voice():
    print("--- User Voice Migration ---")
    email = "dirk.proessel@web.de"
    voice_id = "e9013b9646b64fa19b902a52237fd1cf"
    voice_name = "Dirk (Geklont)"
    
    with Session(engine) as session:
        statement = select(User).where(User.email == email)
        user = session.exec(statement).first()
        
        if user:
            print(f"Found user: {user.email}")
            user.custom_voice_id = voice_id
            user.custom_voice_name = voice_name
            session.add(user)
            session.commit()
            print(f"Successfully assigned voice {voice_id} to {email}")
        else:
            print(f"ERROR: User with email {email} not found in database.")

if __name__ == "__main__":
    asyncio.run(migrate_user_voice())
