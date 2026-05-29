import sys
import os
from sqlmodel import Session, select

# Ensure app directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.database import engine
from app.models import UserVoice

def cleanup():
    # Promoted Fish Audio voice IDs for Stromberg (Christoph) and Katharina Thalbach
    target_ids = ["3ee58b7440a04e468868eab1a7fff651", "53c3de1d063f4ce4a027eab5497b2f11"]
    print("Running DB cleanup for promoted voices...")
    
    with Session(engine) as session:
        statement = select(UserVoice).where(UserVoice.fish_voice_id.in_(target_ids))
        results = session.exec(statement).all()
        if results:
            print(f"Found {len(results)} private voice entries to delete.")
            for v in results:
                print(f"Deleting UserVoice: {v.name} (id: {v.id}, fish_voice_id: {v.fish_voice_id})")
                session.delete(v)
            session.commit()
            print("Cleanup completed successfully.")
        else:
            print("No matching private voice entries found in this database. Already cleaned or empty.")

if __name__ == "__main__":
    cleanup()
