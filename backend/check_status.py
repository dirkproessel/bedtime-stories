import sqlite3
import os

def check_db(path, label):
    if os.path.exists(path):
        try:
            conn = sqlite3.connect(path)
            c = conn.cursor()
            c.execute("SELECT count(*) FROM storymeta")
            count = c.fetchone()[0]
            conn.close()
            print(f"{label} count: {count}")
        except Exception as e:
            print(f"{label} error: {e}")
    else:
        print(f"{label} DB missing")

check_db(r"c:\Dirk\Codings\bedtime-stories\backend\audio_output\bedtime_stories.db", "Main")
check_db(r"c:\Dirk\Codings\bedtime-stories\backend\audio_output_staging\bedtime_stories.db", "Staging")

json_path_main = r"c:\Dirk\Codings\bedtime-stories\backend\audio_output\stories.json"
json_path_staging = r"c:\Dirk\Codings\bedtime-stories\backend\audio_output_staging\stories.json"

print(f"Main JSON exists: {os.path.exists(json_path_main)}")
print(f"Staging JSON exists: {os.path.exists(json_path_staging)}")
