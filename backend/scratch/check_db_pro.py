import sqlite3
import os

dbs = [
    "audio_output/bedtime_stories.db",
    "audio_output_staging/bedtime_stories.db",
    "bedtime_stories.db"
]

for db in dbs:
    if os.path.exists(db):
        print(f"\n--- Database: {db} ---")
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        for table in tables:
            cur.execute(f"SELECT count(*) FROM {table}")
            print(f"  Table {table}: {cur.fetchone()[0]} rows")
        
        if 'bookproject' in tables:
            cur.execute("SELECT id, title, status, progress FROM bookproject")
            projects = cur.fetchall()
            if projects:
                print("  Book projects:")
                for p in projects:
                    print(f"    {p}")
        conn.close()
    else:
        print(f"\nDatabase {db} does not exist.")
