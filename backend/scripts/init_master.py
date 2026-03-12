import sys
import os
import uuid
from pathlib import Path

# Add app to path
sys.path.append(os.getcwd())

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models import User
from app.auth_utils import get_password_hash

def init_master():
    print("Initializing database...")
    create_db_and_tables()
    
    with Session(engine) as session:
        email = "dirk.proessel@web.de"
        existing = session.exec(select(User).where(User.email == email)).first()
        
        if existing:
            print(f"User {email} already exists.")
            existing.is_admin = True
            session.add(existing)
            session.commit()
            print("Ensured admin status.")
        else:
            print(f"Creating master user: {email}")
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                hashed_password=get_password_hash("Dornrose25!!"),
                is_admin=True,
                is_active=True
            )
            session.add(user)
            session.commit()
            print("Master user created successfully.")

if __name__ == "__main__":
    init_master()
