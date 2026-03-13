
import asyncio
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.story_generator import _generate_multi_pass

async def test_remix_prompt():
    # Mock data
    mock_parent_text = {
        "title": "Abenteuer im Wald",
        "synopsis": "Peter findet einen magischen Stein.",
        "chapters": [{"title": "Kapitel 1", "text": "Peter ging im Wald spazieren und fand einen Stein."}]
    }
    
    # Test Improvement
    print("Testing Improvement Prompt...")
    # We can't easily capture the prompt without modifying the service or mocking the client.
    # But we can at least check if the function runs and doesn't crash before the first API call.
    # Actually, let's just print what remix_context would be.
    
    def get_remix_context(remix_type, further_instructions, parent_text):
        remix_context = ""
        if remix_type == "improvement" and parent_text:
            remix_context = f"\n\nDIES IST EINE VERBESSERUNG DER FOLGENDEN GESCHICHTE:\n{json.dumps(parent_text, ensure_ascii=False)}\n\nSPEZIELLE ANWEISUNGEN FÜR DIE VERBESSERUNG:\n{further_instructions or 'Mache die Geschichte einfach besser.'}"
        elif remix_type == "sequel" and parent_text:
            parent_synopsis = parent_text.get("synopsis", "Teil 1")
            parent_title = parent_text.get("title", "Die erste Geschichte")
            remix_context = f"\n\nDIES IST EINE FORTSETZUNG (SEQUEL) ZU:\nTitel: {parent_title}\nZusammenfassung von Teil 1: {parent_synopsis}\n\nANWEISUNGEN FÜR DIE FORTSETZUNG:\n{further_instructions or 'Erzähle die Geschichte weiter.'}"
        return remix_context

    print("--- Improvement Context ---")
    print(get_remix_context("improvement", "Mehr Action", mock_parent_text))
    
    print("\n--- Sequel Context ---")
    print(get_remix_context("sequel", "Sie treffen einen Drachen", mock_parent_text))

if __name__ == "__main__":
    asyncio.run(test_remix_prompt())
