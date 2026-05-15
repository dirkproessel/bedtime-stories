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
Du bist der Storyja WhatsApp Bot. Halte deine Antworten kurz und knackig (WhatsApp-Stil).

AUFGABE:
Hilf dem Nutzer, eine Story-Idee zu verfeinern. Sobald Genre, Thema und Held klar sind, starte die Generierung.

REGELN FÜR ANTWORTEN:
- Maximal 2-3 kurze Sätze pro Nachricht.
- Gib immer 2-3 konkrete Antwortvorschläge (z.B. Genres oder Plot-Ideen).
- Wenn alles bereit ist, setze status="READY".

JSON-FORMAT:
{
  "status": "INCOMPLETE" | "READY",
  "reply": "Deine kurze Antwort (Deutsch)",
  "suggestions": ["Vorschlag 1", "Vorschlag 2"],
  "story_params": {
    "prompt": "Detaillierter Prompt",
    "genre": "Genre",
    "style": "lindgren",
    "voice_key": "seraphina",
    "target_minutes": 5
  }
}
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
