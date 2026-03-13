import sqlite3
from pathlib import Path

def check_db(name):
    db_path = Path(name)
    if not db_path.exists():
        return
    print(f"--- {name} ---")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, email, is_admin FROM user")
    rows = cur.fetchall()
    for row in rows:
        print(f"ID: {row[0]} | Email: {row[1]} | IsAdmin: {row[2]}")
    conn.close()

check_db("audio_output_staging/bedtime_stories.db")
check_db("audio_output/bedtime_stories.db")
