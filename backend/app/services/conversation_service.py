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

from twilio.twiml.messaging_response import MessagingResponse

SYSTEM_PROMPT = """
Du bist der Storyja WhatsApp Bot. Deine Aufgabe ist es, mit dem Nutzer eine Geschichte-Idee zu entwickeln.
Sei freundlich, kreativ und hilfsbereit (Stil: Kindergeschichten-Experte).

ZERTIFIZIERUNG:
Damit wir eine Geschichte generieren können, brauchen wir:
1. Ein klares Genre (z.B. Märchen, Abenteuer, Science-Fiction).
2. Ein Thema oder einen Helden.
3. Einen groben Plot.

DEINE ANTWORT-STRUKTUR:
1. Reagiere auf die Eingabe des Nutzers (Lob, Bestätigung, Humor).
2. Wenn Informationen fehlen: Frage gezielt nach EINER Sache (z.B. "Welches Genre soll es sein?").
3. Wenn alles bereit ist: Fasse die Idee kurz zusammen und sage dem Nutzer, dass die Geschichte jetzt generiert wird.
4. Gib IMMER auch die "Nächsten Schritte" oder Tipps an (z.B. "Du kannst auch 'Abenteuer' schreiben, wenn du unsicher bist").

LOGIK:
- Wenn alles klar ist, setze den Status auf "READY".
- Gib IMMER ein valides JSON-Objekt zurück.

JSON-FORMAT:
{
  "status": "INCOMPLETE" | "READY",
  "reply": "Deine ausführliche Antwort an den Nutzer auf Deutsch (inkl. Next Steps)",
  "story_params": {
    "prompt": "Vollständiger, detaillierter Prompt für die KI (basiert auf dem Chat)",
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
        full_prompt = f"{conversation_context}\nNutzer: {message}\n\nAntworte im JSON-Format gemäß System-Instruction."
        
        try:
            # 3. Call Gemini
            response_json = await generate_text(
                prompt=full_prompt,
                system_instruction=SYSTEM_PROMPT,
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
