import logging
import json
import uuid
from datetime import datetime
from app.services.text_generator import generate_text
from app.services.story_service import story_service
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory session store
# { "whatsapp_number": { "idea": "...", "history": [], "last_updated": ... } }
sessions = {}

SYSTEM_PROMPT = """
Du bist der Storyja WhatsApp Bot. Deine Aufgabe ist es, mit dem Nutzer eine Geschichte-Idee zu entwickeln.
Sei freundlich, kreativ und hilfsbereit (Stil: Kindergeschichten-Experte).

PRÜFUNG:
Damit wir eine Geschichte generieren können, brauchen wir:
1. Ein klares Genre (z.B. Märchen, Abenteuer, Science-Fiction).
2. Ein Thema oder einen Helden.
3. Einen groben Plot.

LOGIK:
- Wenn Infos fehlen, frage charmant nach.
- Wenn alles klar ist, fasse die Idee kurz zusammen und setze den Status auf "READY".
- Gib IMMER ein JSON-Objekt zurück.

JSON-FORMAT:
{
  "status": "INCOMPLETE" | "READY",
  "reply": "Deine Antwort an den Nutzer auf Deutsch",
  "story_params": {
    "prompt": "Vollständiger Prompt für die KI",
    "genre": "Genre Name",
    "style": "lindgren",
    "voice_key": "seraphina",
    "target_minutes": 5
  }
}

Standards für story_params:
- genre: 'Märchen' (Standard)
- style: 'lindgren' (Standard)
- voice_key: 'seraphina' (Standard)
- target_minutes: 5
"""

class ConversationService:
    async def process_message(self, from_number: str, message: str) -> dict:
        """Processes a message from a user and returns a reply + potential story params."""
        
        # 1. Get or create session
        if from_number not in sessions:
            sessions[from_number] = {
                "history": [],
                "last_updated": datetime.now()
            }
        
        session = sessions[from_number]
        session["last_updated"] = datetime.now()
        
        # 2. Build conversation context for Gemini
        conversation_context = "\n".join([f"Nutzer: {m['user']}\nBot: {m['bot']}" for m in session["history"]])
        full_prompt = f"{conversation_context}\nNutzer: {message}\n\nAntworte im JSON-Format."
        
        try:
            # 3. Call Gemini
            response_json = await generate_text(
                prompt=full_prompt,
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
            
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
