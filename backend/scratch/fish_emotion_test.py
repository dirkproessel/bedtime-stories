"""
Fish TTS Emotion-Tag Test
=========================
Erzeugt zwei MP3-Dateien mit identischem Text:
  - output_ohne_tags.mp3   → reiner Text, keine Emotion-Tags
  - output_mit_tags.mp3    → gleicher Text, aber mit [whispering], [sighing] etc.

Ziel: Manuell prüfen ob Fish Audio die Tags überhaupt verarbeitet
      und ob sich die Sprachausgabe hörbar unterscheidet.

Ausführung (aus backend/):
  python scratch/fish_emotion_test.py
"""

import asyncio
import httpx
from pathlib import Path

# ── Konfiguration ──────────────────────────────────────────────────────────────
# Fish Voice ID: Christoph Maria Herbst (aus FISH_VOICES in tts_service.py)
VOICE_ID = "3ee58b7440a04e468868eab1a7fff651"

# Aus .env laden oder direkt eintragen
import os, sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings
API_KEY = settings.FISH_API_KEY

OUTPUT_DIR = Path(__file__).parent / "fish_test_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Texte ──────────────────────────────────────────────────────────────────────

# TEXT A: Ohne Emotions-Tags — reiner narrativer Text
TEXT_OHNE_TAGS = """\
Die Tür zum alten Herrenhaus stand offen, obwohl niemand sie aufgeschlossen hatte.
Clara trat einen Schritt zurück und betrachtete das Gebäude.
Es war still. Viel zu still für einen Freitagabend in dieser Gegend.
Sie griff nach ihrem Telefon, aber das Display blieb schwarz.
Die Batterie war leer — natürlich war sie das.
Dann hörte sie es: ein leises Knarren aus dem Obergeschoss.
Sie flüsterte: „Da ist jemand."
Ihr Herzschlag beschleunigte sich, aber sie bewegte sich nicht vom Fleck.
Schließlich atmete sie tief durch und trat über die Schwelle.
"""

# TEXT B: Mit Emotions-Tags — identischer Text, aber mit sparsamen [tag] Markierungen
# Genau so wie der story_generator sie laut Prompt-Anweisung einfügt:
# - am Anfang eines Satzes oder vor wörtlicher Rede
# - maximal 1-2 Mal pro Kapitel / Textabschnitt
TEXT_MIT_TAGS = """\
Die Tür zum alten Herrenhaus stand offen, obwohl niemand sie aufgeschlossen hatte.
Clara trat einen Schritt zurück und betrachtete das Gebäude.
Es war still. Viel zu still für einen Freitagabend in dieser Gegend.
Sie griff nach ihrem Telefon, aber das Display blieb schwarz.
Die Batterie war leer — natürlich war sie das.
Dann hörte sie es: ein leises Knarren aus dem Obergeschoss.
[whispering] Sie flüsterte: „Da ist jemand."
Ihr Herzschlag beschleunigte sich, aber sie bewegte sich nicht vom Fleck.
[sighing] Schließlich atmete sie tief durch und trat über die Schwelle.
"""

# ── Fish API Aufruf ────────────────────────────────────────────────────────────

async def generate(text: str, output_path: Path, label: str):
    print(f"\n>> Generiere: {label}")
    print(f"  Text (erste 80 Zeichen): {repr(text[:80].strip())}...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "reference_id": VOICE_ID,
        "format": "mp3",
        "mp3_bitrate": 128,
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", "https://api.fish.audio/v1/tts",
            headers=headers, json=payload
        ) as response:
            response.raise_for_status()
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
    
    size_kb = output_path.stat().st_size / 1024
    print(f"  OK Gespeichert: {output_path.name} ({size_kb:.1f} KB)")


async def main():
    print("=" * 60)
    print("Fish TTS Emotion-Tag Test")
    print("=" * 60)
    print(f"Voice ID : {VOICE_ID}")
    print(f"Output   : {OUTPUT_DIR}")
    
    await generate(
        text=TEXT_OHNE_TAGS,
        output_path=OUTPUT_DIR / "output_ohne_tags.mp3",
        label="OHNE Emotions-Tags"
    )
    
    await generate(
        text=TEXT_MIT_TAGS,
        output_path=OUTPUT_DIR / "output_mit_tags.mp3",
        label="MIT Emotions-Tags ([whispering], [sighing])"
    )
    
    print("\n" + "=" * 60)
    print("Fertig! Beide Dateien zum Vergleich:")
    print(f"  1. {OUTPUT_DIR / 'output_ohne_tags.mp3'}")
    print(f"  2. {OUTPUT_DIR / 'output_mit_tags.mp3'}")
    print()
    print("Erwartetes Ergebnis wenn Fish Emotion-Tags UNTERSTÜTZT:")
    print("  → Die Sätze mit [whispering] / [sighing] klingen deutlich")
    print("    anders (leiser / seufzend) als in Datei 1.")
    print()
    print("Erwartetes Ergebnis wenn Fish die Tags IGNORIERT:")
    print("  → Beide Dateien klingen identisch oder in Datei 2")
    print("    werden die Tag-Texte vorgelesen ('[whispering]...').")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
