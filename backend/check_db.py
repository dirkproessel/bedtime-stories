import sqlite3
import os

paths = [
    r"c:\Dirk\Codings\bedtime-stories\backend\audio_output\bedtime_stories.db",
    r"c:\Dirk\Codings\bedtime-stories\backend\audio_output_staging\bedtime_stories.db"
]

for p in paths:
    if os.path.exists(p):
        conn = sqlite3.connect(p)
        c = conn.cursor()
        try:
            c.execute("SELECT count(*) FROM storymeta")
            count = c.fetchone()[0]
            print(f"File: {p}, Count: {count}")
        except Exception as e:
            print(f"File: {p}, Error: {e}")
        conn.close()
    else:
        print(f"File: {p} does not exist")
