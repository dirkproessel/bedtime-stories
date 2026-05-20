import requests
import time
import sys
import json
import os

def main():
    api_base = "https://api.storyja.com"
    print(f"Registering guest user on {api_base}...")
    
    # 1. Register guest
    try:
        r = requests.post(f"{api_base}/api/auth/guest")
        r.raise_for_status()
        auth_data = r.json()
        token = auth_data["access_token"]
        print("Guest user registered successfully!")
    except Exception as e:
        print(f"Failed to register guest user: {e}")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Start generation
    payload = {
        "prompt": "Ein kleiner Roboter sucht seinen Schlüssel. Er begibt sich auf ein großes Abenteuer und durchsucht verschiedene Science-Fiction Welten.",
        "genre": "Science-Fiction",
        "style": "Douglas Adams",
        "target_minutes": 5,
        "voice_key": "seraphina"
    }

    print(f"Starting story generation with prompt: '{payload['prompt']}'...")
    try:
        r = requests.post(f"{api_base}/api/stories/generate", json=payload, headers=headers)
        r.raise_for_status()
        gen_data = r.json()
        story_id = gen_data["id"]
        print(f"Story generation started! Story ID: {story_id}")
    except Exception as e:
        print(f"Failed to start story generation: {e}")
        sys.exit(1)

    # 3. Poll status
    print("Polling story generation status...")
    max_attempts = 60
    for attempt in range(max_attempts):
        time.sleep(5)
        try:
            r = requests.get(f"{api_base}/api/status/{story_id}", headers=headers)
            r.raise_for_status()
            status_data = r.json()
            status = status_data.get("status")
            progress = status_data.get("progress")
            pct = status_data.get("progress_pct", 0)
            print(f" [{attempt*5}s] Status: {status} | Progress: {progress} ({pct}%)")
            
            if status == "done":
                print("Story generated successfully!")
                break
            elif status == "error":
                print(f"Error during story generation: {progress}")
                sys.exit(1)
        except Exception as e:
            print(f"Error checking status: {e}")
    else:
        print("Timeout waiting for story generation to complete.")
        sys.exit(1)

    # 4. Fetch completed story details
    print("Fetching story content...")
    try:
        r = requests.get(f"{api_base}/api/stories/{story_id}", headers=headers)
        r.raise_for_status()
        story = r.json()
        
        # Save story to file
        os.makedirs("tmp", exist_ok=True)
        filepath = "tmp/generated_story_api.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(story, f, indent=2, ensure_ascii=False)
            
        print(f"Saved completed story to {filepath}")
        
        # Print info
        print("\n==========================================")
        print(f"Title: {story.get('title')}")
        print(f"Description: {story.get('description')}")
        print(f"URL on Storyja: https://storyja.com/stories/{story_id}")
        print("==========================================\n")
        
        for ch in story.get("chapters", []):
            print(f"\nKapitel: {ch.get('title')}")
            print(ch.get('text'))
            print("-" * 20)
            
    except Exception as e:
        print(f"Failed to fetch completed story: {e}")

if __name__ == "__main__":
    main()
