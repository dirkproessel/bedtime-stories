import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set paths
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

# Load environment
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

from app.services.book_generator import apply_global_feedback_to_outline

async def main():
    characters_bible = "Protagonist: Leo, ein junger Fuchs, der Angst vor der Dunkelheit hat. Nebencharakter: Mia, eine mutige Eule."
    
    current_outline = json.dumps({
        "title": "Leos Abenteuer im Wald",
        "chapters": [
            {
                "id": "chap1",
                "chapter_number": 1,
                "title": "Die Angst im Dunkeln",
                "plot_outline": "Leo der Fuchs sitzt in seiner Höhle und fürchtet sich vor der Dunkelheit. Seine Mutter tröstet ihn nicht, da sie jagen ist. Plötzlich klopft es."
            },
            {
                "id": "chap2",
                "chapter_number": 2,
                "title": "Eine gefiederte Freundin",
                "plot_outline": "Leo öffnet die Tür und trifft eine fremde Katze namens Sam. Sie beschließen, gemeinsam durch den nächtlichen Wald zu spazieren, obwohl Mia die Eule eigentlich sein bester Freund ist und auf ihn wartet."
            }
        ]
    })
    
    findings = [
        {
            "category": "consistency",
            "description": "Im Charakterverzeichnis steht Mia die Eule als wichtigster Nebencharakter, in Kapitel 2 taucht aber plötzlich eine Katze namens Sam auf, die nie eingeführt wurde.",
            "chapters_involved": [2],
            "suggested_fix": "Ersetze Sam die Katze in Kapitel 2 durch Mia die Eule, um die Konsistenz zum Charakterverzeichnis zu wahren."
        }
    ]
    
    print("Sending request to Gemini...")
    try:
        updated_outline_str = await apply_global_feedback_to_outline(
            characters_bible=characters_bible,
            current_outline=current_outline,
            findings=findings,
            model="gemini-3.1-flash-lite"
        )
        print("\nOriginal Outline:")
        print(current_outline)
        print("\nUpdated Outline from Gemini:")
        print(updated_outline_str)
        
        # Verify JSON validity
        data = json.loads(updated_outline_str)
        print("\nVerification: JSON is valid!")
        assert "chapters" in data
        assert len(data["chapters"]) == 2
        print("Verification: Chapters structure exists!")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
