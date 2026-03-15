import sqlite3
import os
import sys
from pathlib import Path

# Tentative DB path
DB_PATH = Path("audio_output/bedtime_stories.db")

def diagnostic():
    print("=== BEDTIME STORIES VPS DIAGNOSTIC ===")
    
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        # Search for it
        print("Searching for bedtime_stories.db...")
        matches = list(Path(".").glob("**/bedtime_stories.db"))
        if matches:
            print(f"Found at: {matches[0]}")
            db_to_use = matches[0]
        else:
            print("Could not find database anywhere.")
            return
    else:
        db_to_use = DB_PATH

    print(f"Using database: {db_to_use}")
    conn = sqlite3.connect(db_to_use)
    cur = conn.cursor()
    
    try:
        # 1. Check Schema
        print("\n--- Schema (storymeta) ---")
        cur.execute("PRAGMA table_info(storymeta)")
        columns = cur.fetchall()
        for col in columns:
            print(f"Column: {col[1]} ({col[2]})")
            
        # 2. Check Counts
        print("\n--- Data Counts ---")
        cur.execute("SELECT COUNT(*) FROM storymeta")
        story_count = cur.fetchone()[0]
        print(f"Stories: {story_count}")
        
        cur.execute("SELECT COUNT(*) FROM user")
        user_count = cur.fetchone()[0]
        print(f"Users: {user_count}")
        
        # 3. Check Visibility/Ownership distribution
        if story_count > 0:
            print("\n--- Story Distribution ---")
            cur.execute("SELECT is_public, COUNT(*) FROM storymeta GROUP BY is_public")
            pub_dist = cur.fetchall()
            print(f"Public distribution (0=Private, 1=Public): {pub_dist}")
            
            cur.execute("SELECT user_id, COUNT(*) FROM storymeta GROUP BY user_id")
            user_dist = cur.fetchall()
            print(f"Ownership (user_id): {user_dist}")
            
            # List first few stories
            print("\n--- Sample Stories (Recent 5) ---")
            cur.execute("SELECT id, title, user_id, is_public FROM storymeta ORDER BY created_at DESC LIMIT 5")
            samples = cur.fetchall()
            for s in samples:
                print(f"ID: {s[0]} | Public: {s[3]} | Owner: {s[2]} | Title: {s[1]}")

        # 4. Repair Option
        if len(sys.argv) > 1 and sys.argv[1] == "--repair-visibility":
            print("\n--- EMERGENCY REPAIR: Marking all stories as PUBLIC ---")
            cur.execute("UPDATE storymeta SET is_public = 1")
            conn.commit()
            print("Done.")
            
    except Exception as e:
        print(f"\nDIAGNOSTIC ERROR: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    diagnostic()
