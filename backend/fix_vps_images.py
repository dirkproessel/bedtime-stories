import asyncio
import json
import sqlite3
import os
from pathlib import Path

# --- KONFIGURATION (Bitte prüfen) ---
DB_PATH = Path("audio_output/bedtime_stories.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
# BEACHTE: Sollte der API Key nicht im Environment sein, hier direkt einfügen:
# GEMINI_API_KEY = "DEIN_KEY_HIER"

# --- LOGIK ---
async def generate_image_vps(synopsis, output_path, genre, style):
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    model_id = 'imagen-4.0-fast-generate-001'
    
    style_hints = {
        "Sci-Fi": "Futuristic, cinematic concept art, neon accents, detailed textures",
        "Fantasy": "Epic oil painting, ethereal lighting, rich colors, intricate details",
        "Krimi": "Neo-noir, high contrast, dramatic shadows, moody atmosphere",
        "Abenteuer": "Vibrant exploration art, dynamic composition, warm light",
        "Realismus": "Fine art photography style, natural lighting, sharp focus",
        "Grusel": "Dark gothic art, misty, psychological horror aesthetic",
        "Dystopie": "Gritty, industrial, muted tones, post-apocalyptic vibe",
        "Satire": "Stylized editorial illustration, bold colors, ironic composition"
    }
    
    genre_hint = style_hints.get(genre, "Artistic illustration")
    enhanced_prompt = (
        f"Anspruchsvolles Szene-Artwork: {synopsis}. "
        f"Genre: {genre}. Visueller Stil: {genre_hint}, literarisch, hochwertig, ästhetisch ansprechend, keine Klischees. "
        f"Passend zum Schreibstil von {style}. Minimalistisch und modern. "
        f"WICHTIGE REGEL: KEIN TEXT! Keine Buchstaben, keine Wörter."
    )

    try:
        response = client.models.generate_images(
            model=model_id,
            prompt=enhanced_prompt,
            config=types.GenerateImagesConfig(number_of_images=1, output_mime_type='image/png')
        )
        if response.generated_images:
            output_path.write_bytes(response.generated_images[0].image.image_bytes)
            return True
    except Exception as e:
        print(f"Fehler bei Generierung: {e}")
    return False

async def main():
    if not GEMINI_API_KEY:
        print("FEHLER: GEMINI_API_KEY nicht gefunden. Bitte im Script oder environment setzen.")
        return

    if not DB_PATH.exists():
        print(f"FEHLER: Datenbank {DB_PATH} nicht gefunden.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Suche fertige Stories ohne Bild
    cur.execute("SELECT id, title, genre, style FROM storymeta WHERE image_url IS NULL AND status = 'done'")
    stories = cur.fetchall()
    print(f"Gefunden: {len(stories)} Stories ohne Bild.")

    for story_id, title, genre, style in stories:
        print(f"Bearbeite: {title} ({story_id})...")
        story_dir = DB_PATH.parent / story_id
        text_path = story_dir / "story.json"
        
        if not text_path.exists():
            print(f"  -> story.json fehlt. Überspringe.")
            continue
            
        data = json.loads(text_path.read_text())
        synopsis = data.get("synopsis", "Ein schönes Bild.")
        
        image_path = story_dir / "cover.png"
        if await generate_image_vps(synopsis, image_path, genre, style):
            # Update DB (passe URL an deine Architektur an, meistens relativ)
            image_url = f"/api/stories/{story_id}/image.png"
            cur.execute("UPDATE storymeta SET image_url = ? WHERE id = ?", (image_url, story_id))
            conn.commit()
            print(f"  -> ERFOLG!")
        else:
            print(f"  -> FEHLGESCHLAGEN.")

    conn.close()
    print("Fertig.")

if __name__ == "__main__":
    asyncio.run(main())
