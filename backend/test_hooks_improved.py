import asyncio
import os
import sys

# Füge app-Verzeichnis zum Pfad hinzu
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
sys.path.append(os.path.dirname(__file__))

from app.services.story_generator import generate_story_hook

async def main():
    print("--- Teste verbesserte Story-Hooks ---\n")
    
    for i in range(5):
        print(f"Test {i+1}:")
        hook = await generate_story_hook("Krimi", "kehlmann")
        print(f"Ergebnis: {hook}\n")

if __name__ == "__main__":
    asyncio.run(main())
