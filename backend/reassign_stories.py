import sqlite3
import os
import sys

# Update this path if the DB is somewhere else in production
DB_PATH = os.environ.get("BEDTIME_DB_PATH", "audio_output/bedtime_stories.db")

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run this from the 'backend' directory or set BEDTIME_DB_PATH.")
        return False
    return True

def list_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("\n--- Current Users ---")
    cursor.execute("SELECT id, email, is_admin FROM user")
    users = cursor.fetchall()
    for u in users:
        cursor.execute("SELECT COUNT(*) FROM storymeta WHERE user_id = ?", (u[0],))
        count = cursor.fetchone()[0]
        print(f"ID: {u[0]} | Email: {u[1]} | Admin: {u[2]} | Stories: {count}")
    print("----------------------\n")
    conn.close()

def reassign_all_stories(from_user_id, to_user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM storymeta WHERE user_id = ?", (from_user_id,))
    stories = cursor.fetchall()
    if not stories:
        print(f"No stories found for user {from_user_id}")
    else:
        print(f"Moving {len(stories)} stories from {from_user_id} to {to_user_id}...")
        cursor.execute("UPDATE storymeta SET user_id = ?, user_email = NULL WHERE user_id = ?", (to_user_id, from_user_id))
        conn.commit()
        print("Done!")
    conn.close()

def reassign_single_story(story_id, to_user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM storymeta WHERE id = ?", (story_id,))
    story = cursor.fetchone()
    if not story:
        print(f"Story {story_id} not found.")
    else:
        print(f"Moving story '{story[0]}' to {to_user_id}...")
        cursor.execute("UPDATE storymeta SET user_id = ?, user_email = NULL WHERE id = ?", (to_user_id, story_id))
        conn.commit()
        print("Done!")
    conn.close()

def list_stories():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("\n--- Current Stories ---")
    cursor.execute("SELECT id, title, user_id FROM storymeta ORDER BY created_at DESC")
    stories = cursor.fetchall()
    for s in stories:
        print(f"ID: {s[0]} | Owner: {s[2]} | Title: {s[1]}")
    print("----------------------\n")
    conn.close()

if __name__ == "__main__":
    if not check_db():
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  List users:    python reassign_stories.py list")
        print("  List stories:  python reassign_stories.py list-stories")
        print("  Move all:      python reassign_stories.py move-all <FROM_ID> <TO_ID>")
        print("  Move one:      python reassign_stories.py move-one <STORY_ID> <TO_ID>")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "list":
        list_users()
    elif cmd == "list-stories":
        list_stories()
    elif cmd == "move-all" and len(sys.argv) == 4:
        reassign_all_stories(sys.argv[2], sys.argv[3])
    elif cmd == "move-one" and len(sys.argv) == 4:
        reassign_single_story(sys.argv[2], sys.argv[3])
    else:
        print("Invalid command or arguments.")
