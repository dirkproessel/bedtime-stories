import sqlite3
from pathlib import Path

def check_db(name):
    db_path = Path(name)
    if not db_path.exists():
        return
    print(f"--- {name} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM storymeta")
    count = cur.fetchone()[0]
    print(f"Stories count: {count}")
    cur.execute("SELECT DISTINCT user_id FROM storymeta")
    user_ids = cur.fetchall()
    print(f"User IDs: {user_ids}")
    conn.close()

check_db("audio_output/bedtime_stories.db")
