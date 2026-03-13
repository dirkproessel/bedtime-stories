import sqlite3
from pathlib import Path

def inspect_db(name):
    db_path = Path(name)
    if not db_path.exists():
        print(f"{name} does not exist.")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]
    print(f"--- {name} ---")
    print(f"Tables: {tables}")
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"Table '{table}' has {count} rows.")
    conn.close()

inspect_db("../audio_output/bedtime_stories.db")
inspect_db("audio_output/bedtime_stories.db")
inspect_db("audio_output_staging/bedtime_stories.db")
