# -*- coding: utf-8 -*-
"""
Fish TTS - Vollstaendiger Emotion-Tag Test
==========================================
Generiert fuer jeden Tag eine eigene MP3-Datei.
Jede Datei hat dieselbe Basis-Aussage, einmal ohne und einmal mit dem jeweiligen Tag.

Ausgabe: backend/scratch/fish_tag_output/
  - 00_REFERENZ.mp3         (kein Tag, reiner Text)
  - 01_sighing.mp3
  - 02_laughing.mp3
  - 03_excited.mp3
  - 04_sad.mp3
  - 05_angry.mp3
  - 06_gasp.mp3
  - 07_yawn.mp3
  - 08_crying.mp3
  - 09_nervous.mp3
  - 10_whispering.mp3       (als Vergleich, da nicht funktioniert)
  - 11_chuckling.mp3
  - 12_sobbing.mp3
  - 13_groaning.mp3
  - 14_hesitant.mp3
  - 15_surprised.mp3

Ausfuehren (aus backend/):
  python -X utf8 scratch/fish_tag_full_test.py
"""

import asyncio
import httpx
from pathlib import Path
import os, sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

# ── Konfiguration ──────────────────────────────────────────────────────────────
# Christoph Maria Herbst - ausdrucksstarke Stimme, gut fuer Emotion-Tests
VOICE_ID = "3ee58b7440a04e468868eab1a7fff651"
API_KEY  = settings.FISH_API_KEY

OUTPUT_DIR = Path(__file__).parent / "fish_tag_output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Test-Saetze (deutsch, emotional passend) ───────────────────────────────────
# Jeder Tag bekommt einen Satz VOR dem Tag (Kontext) und einen Satz MIT dem Tag.
# So hoert man den Unterschied klar.

REFERENZTEXT = """\
Es war eine seltsame Nacht. Die Stille draengte sich durch die Fensterritzen.
Er setzte sich ans Bett und schloss die Augen.
Das war es also. Alles vorbei.
"""

TAGS = [
    ("01_sighing",    "[sighing]",    "Er setzte sich ans Bett und schloss die Augen.\n[sighing] Das war es also. Alles vorbei.\n"),
    ("02_laughing",   "[laughing]",   "Der Witz war so schlecht, dass niemand lachte.\n[laughing] Ausser ihm natuerlich. Er konnte sich nicht mehr halten.\n"),
    ("03_excited",    "[excited]",    "Der Brief lag auf dem Tisch. Er riss ihn auf.\n[excited] Die Stelle war ihm! Er hatte es geschafft!\n"),
    ("04_sad",        "[sad]",        "Das Foto zeigte sie beide, gluecklich, damals.\n[sad] Er legte es wieder hin und ging nicht zurueck.\n"),
    ("05_angry",      "[angry]",      "Er hatte es genug. Zum dritten Mal dieselbe Entschuldigung.\n[angry] Das war das letzte Mal. Kein einziges Wort mehr.\n"),
    ("06_gasp",       "[gasp]",       "Die Tuere oeffnete sich langsam. Er trat einen Schritt vor.\n[gasp] Da stand sie. Nach all den Jahren.\n"),
    ("07_yawn",       "[yawn]",       "Es war schon weit nach Mitternacht. Die Seiten verschwammen vor seinen Augen.\n[yawn] Er klappte das Buch zu und loeschte das Licht.\n"),
    ("08_crying",     "[crying]",     "Die Nachricht traf ihn wie ein Schlag. Er las sie zweimal.\n[crying] Es war wahr. Er konnte nichts dagegen tun.\n"),
    ("09_nervous",    "[nervous]",    "Die Pruefer schauten ihn an. Zwanzig Augen. Er raeusperte sich.\n[nervous] Guten Morgen. Ich... ich beginne mit der ersten Folie.\n"),
    ("10_whispering", "[whispering]", "Im Gang war es dunkel. Schritte kamen naeher.\n[whispering] Psst. Hier entlang. Aber leise.\n"),
    ("11_chuckling",  "[chuckling]",  "Die alte Frau wies auf das Schild: Betreten verboten.\n[chuckling] Ja ja. Das sagten sie damals auch schon.\n"),
    ("12_sobbing",    "[sobbing]",    "Er fand den alten Brief im Schreibtisch. Ihre Handschrift.\n[sobbing] Ich vermisse dich. Jeden einzelnen Tag.\n"),
    ("13_groaning",   "[groaning]",   "Das Paket war dreimal so schwer wie angekuendigt. Er hob es an.\n[groaning] Wer hat das eigentlich gepackt? Ein Elefant?\n"),
    ("14_hesitant",   "[hesitant]",   "Sie fragten ihn direkt: Warst du das?\n[hesitant] Ich... also... es ist kompliziert.\n"),
    ("15_surprised",  "[surprised]",  "Der Umschlag enthielt keine Rechnung. Sondern einen Scheck.\n[surprised] Fuenfzigtausend Euro. Einfach so.\n"),
]

# ── Fish API Aufruf ────────────────────────────────────────────────────────────

async def generate(text: str, output_path: Path, label: str):
    if output_path.exists() and output_path.stat().st_size > 1000:
        print(f"  SKIP (existiert bereits): {output_path.name}")
        return

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
    print(f"  OK {output_path.name} ({size_kb:.0f} KB)")


async def main():
    print("=" * 60)
    print("Fish TTS - Vollstaendiger Emotion-Tag Test")
    print("=" * 60)
    print(f"Voice : Christoph Maria Herbst")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Referenz zuerst
    print(">> 00_REFERENZ (kein Tag)")
    await generate(REFERENZTEXT, OUTPUT_DIR / "00_REFERENZ.mp3", "Referenz")

    # Alle Tags sequenziell (um Rate-Limits zu respektieren)
    for filename, tag, text in TAGS:
        print(f">> {filename} ({tag})")
        await generate(text, OUTPUT_DIR / f"{filename}.mp3", tag)

    print()
    print("=" * 60)
    print(f"Fertig! {len(TAGS) + 1} Dateien in:")
    print(f"  {OUTPUT_DIR}")
    print()
    print("Oeffne alle auf einmal mit:")
    print(f"  Invoke-Item '{OUTPUT_DIR}\\*.mp3'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
