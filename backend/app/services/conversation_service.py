import logging
import json
import uuid
import random
from datetime import datetime
from google.genai import types
from app.services.text_generator import generate_text
from app.services.story_service import story_service
from app.services.story_generator import STANZWERK_BIBLIOTHEK
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory session store
sessions = {}

BASE_SYSTEM_PROMPT = """
Du bist der Storyja WhatsApp Bot. Deine Mission: Gemeinsam mit dem Nutzer eine tolle Kindergeschichte planen.

ABLAUF (WICHTIG):
1. IDEE KLÄREN: Sammle Infos (Held, Ort, Handlung).
2. AUTOREN-WAHL: Wenn die Idee steht, schlage dem Nutzer immer 3-4 passende Autoren/Stile aus der Liste vor (als "suggestions"). Erkläre kurz, warum diese passen (z.B. "Dahl für schwarzen Humor, Funke für Magie").
3. BESTÄTIGUNG: Erst wenn der Nutzer einen Autor gewählt hat, setze Status auf "READY".

STATUS-REGELN:
- "INCOMPLETE": Standard-Status für Planung und Autoren-Vorschläge.
- "READY": NUR wenn Idee UND Autor feststehen. 

DIALOG-STIL:
- Kurz und knackig (WhatsApp-Stil). 
- Sei ein kreativer Partner: Vermeide Klischees.
- Vorschlag-Ideen für Autoren: "Stil von Roald Dahl", "Wie Cornelia Funke", "Marc-Uwe Kling Vibe".

JSON-FORMAT:
{
  "status": "INCOMPLETE" | "READY",
  "reply": "Deine Antwort",
  "suggestions": ["Autor A", "Autor B", "Autor C"],
  "story_params": {
    "prompt": "Vollständiger Story-Prompt",
    "genre": "Genre",
    "style": "ID DES GEWÄHLTEN AUTORS (oder 'none' während Planung)",
    "voice_key": "none",
    "target_minutes": 10
  }
}
"""

class ConversationService:
    def _get_random_authors_prompt(self):
        """Provide the full categorized library so Gemini can pick the best matches to suggest."""
        all_authors = []
        for cat_name, authors in STANZWERK_BIBLIOTHEK.items():
            for a in authors:
                all_authors.append(f"- `{a['id']}`: {a['name']} ({a['wortwahl']} - {a['atmosphaere']})")
        
        authors_str = "\n".join(all_authors)
        return f"\nVOLLSTÄNDIGE AUTOREN-BIBLIOTHEK:\n{authors_str}\n\nWICHTIG: Schlage dem Nutzer aus dieser Liste 3-4 Autoren vor, die am besten zu seiner aktuellen Story-Idee passen!\n"

    async def process_message(self, from_number: str, message: str, media_items: list = None) -> dict:
        """Processes a message from a user and returns a reply + potential story params."""
        
        # 1. Get or create session
        now = datetime.now()
        
        # Manual reset command
        if message and message.strip().lower() in ["!reset", "neustart", "stop"]:
            if from_number in sessions:
                del sessions[from_number]
            return {
                "status": "INCOMPLETE",
                "reply": "Alles klar, ich habe unser Gespräch zurückgesetzt. Worüber soll ich heute eine Geschichte schreiben?",
                "suggestions": ["Abenteuer im Weltraum", "Ein magischer Wald", "Ein mutiger Hund"]
            }

        if from_number not in sessions:
            sessions[from_number] = {
                "history": [],
                "last_updated": now
            }
        
        session = sessions[from_number]
        
        # Timeout logic: Reset if last message was > 30 minutes ago
        time_diff = now - session["last_updated"]
        if time_diff.total_seconds() > 1800: # 30 minutes
            logger.info(f"Session timeout for {from_number} ({time_diff.total_seconds()}s). Resetting history.")
            session["history"] = []
            
        session["last_updated"] = now
        
        # 2. Build conversation context for Gemini
        conversation_context = "\n".join([f"Nutzer: {m['user']}\nBot: {m['bot']}" for m in session["history"]])
        
        # Build contents list for Gemini (multimodal support)
        contents = []
        
        # Add history and current text
        history_text = f"{conversation_context}\nNutzer: {message or '(Medien gesendet)'}"
        contents.append(history_text)
        
        # Add media items if present
        if media_items:
            for item in media_items:
                if "data" in item and "mime_type" in item:
                    contents.append(types.Part.from_bytes(data=item["data"], mime_type=item["mime_type"]))
        
        # Inject dynamic author pool
        dynamic_authors = self._get_random_authors_prompt()
        full_instruction = BASE_SYSTEM_PROMPT + dynamic_authors + "\n\nAntworte im JSON-Format. Beziehe dich auf Medien, falls vorhanden."
        try:
            # 3. Call Gemini
            response_json = await generate_text(
                prompt=contents,
                system_instruction=full_instruction,
                response_mime_type="application/json"
            )
            
            logger.info(f"Gemini WhatsApp Response: {response_json}")
            data = json.loads(response_json)
            
            # 4. Update session history
            session["history"].append({"user": message, "bot": data.get("reply", "")})
            # Keep history short
            if len(session["history"]) > 10:
                session["history"] = session["history"][-10:]
                
            return data
            
        except Exception as e:
            logger.error(f"Error in ConversationService: {e}")
            return {
                "status": "INCOMPLETE",
                "reply": "Entschuldige, ich habe gerade ein kleines technisches Problem. Kannst du das nochmal sagen?",
                "story_params": None
            }

    def clear_session(self, from_number: str):
        if from_number in sessions:
            del sessions[from_number]

conversation_service = ConversationService()
