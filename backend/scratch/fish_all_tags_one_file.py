# -*- coding: utf-8 -*-
"""
Fish TTS - Alle Emotion-Tags in einer Datei
============================================
Generiert eine einzige MP3 mit allen Tags nacheinander.
Vor jedem Tag-Satz wird der Tag-Name angesagt (als Trenner).

Ausfuehren (aus backend/):
  python -X utf8 scratch/fish_all_tags_one_file.py
"""

import asyncio
import httpx
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

VOICE_ID = "3ee58b7440a04e468868eab1a7fff651"
API_KEY  = settings.FISH_API_KEY

OUTPUT_FILE = Path(__file__).parent / "fish_tag_output" / "ALLE_TAGS.mp3"
OUTPUT_FILE.parent.mkdir(exist_ok=True)

# ── Vollstaendiger Test-Text mit allen Tags ────────────────────────────────────

TEXT = """\
Dies ist ein Test aller unterstuetzten Emotions-Tags bei Fish Audio.

Tag: sighing.
[sighing] Er setzte sich hin und schloss die Augen. Das war es also. Alles vorbei.

Tag: laughing.
[laughing] Der Witz war so schlecht, dass er sich nicht mehr halten konnte. Er lachte Traenen.

Tag: excited.
[excited] Die Stelle war ihm! Er hatte es geschafft! Endlich!

Tag: sad.
[sad] Das Foto zeigte sie beide, gluecklich, damals. Er legte es wieder hin.

Tag: angry.
[angry] Das war das letzte Mal. Kein einziges Wort mehr. Er warf die Tuere ins Schloss.

Tag: gasp.
[gasp] Da stand sie. Nach all den Jahren. Er konnte es kaum fassen.

Tag: yawn.
[yawn] Es war weit nach Mitternacht. Er klappte das Buch zu und loeschte das Licht.

Tag: crying.
[crying] Es war wahr. Er konnte nichts dagegen tun. Er war allein.

Tag: nervous.
[nervous] Guten Morgen. Ich... ich beginne jetzt mit der ersten Folie.

Tag: whispering.
[whispering] Psst. Hier entlang. Aber leise. Ganz leise.

Tag: chuckling.
[chuckling] Ja ja. Das sagten sie damals auch schon. Er schmunzelte still vor sich hin.

Tag: sobbing.
[sobbing] Ich vermisse dich. Jeden einzelnen Tag. Es tut so weh.

Tag: groaning.
[groaning] Das Paket war dreimal so schwer wie angekuendigt. Wer hat das eigentlich gepackt?

Tag: hesitant.
[hesitant] Ich... also... es ist kompliziert. Ich weiss nicht genau wie ich anfangen soll.

Tag: surprised.
[surprised] Fuenfzigtausend Euro. Einfach so. Im Briefkasten. Ohne Absender.

Ende des Tests.
"""

async def main():
    print("=" * 60)
    print("Fish TTS - Alle Tags in einer Datei")
    print("=" * 60)
    print()
    print("TEXT MIT EMOTION-TAGS (zur Kontrolle):")
    print("-" * 60)
    print(TEXT)
    print("-" * 60)
    print(f"Output: {OUTPUT_FILE}")
    print()
    print("Generiere Audio...")

    headers = {
        "Authorization": f"Bearer {API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": TEXT,
        "reference_id": VOICE_ID,
        "format": "mp3",
        "mp3_bitrate": 128,
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream(
            "POST", "https://api.fish.audio/v1/tts",
            headers=headers, json=payload
        ) as response:
            response.raise_for_status()
            with open(OUTPUT_FILE, "wb") as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)

    size_kb = OUTPUT_FILE.stat().st_size / 1024
    print(f"Fertig! {OUTPUT_FILE.name} ({size_kb:.0f} KB)")

if __name__ == "__main__":
    asyncio.run(main())
