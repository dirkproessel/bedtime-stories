import logging
import json
import uuid
from datetime import datetime
from google.genai import types
from app.services.text_generator import generate_text
from app.services.story_service import story_service
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory session store
# { "whatsapp_number": { "idea": "...", "history": [], "last_updated": ... } }
sessions = {}

SYSTEM_PROMPT = """
Du bist der Storyja WhatsApp Bot. Deine Mission: Gemeinsam mit dem Nutzer eine tolle Kindergeschichte planen.

STATUS-REGELN:
- "INCOMPLETE": Standard-Status. Nutze diesen, um Ideen zu sammeln, nach dem Genre zu fragen oder Bilder zu kommentieren. Frage aktiv nach, wenn etwas unklar ist.
- "READY": NUR dann verwenden, wenn Genre und Grundidee (Held/Handlung) feststehen UND du dem Nutzer im vorherigen Schritt einen Plan vorgeschlagen hast, dem er zugestimmt hat (oder wenn die Infos so klar sind, dass kein Zweifel besteht). 
- WICHTIG: Wenn Status "READY", dann KEINE Fragen im "reply". Die Antwort muss eine Bestätigung sein ("Alles klar, ich fange an!").

DIALOG-STIL:
- Kurz und knackig (WhatsApp-Stil). 
- Sei ein kreativer Partner: Vermeide Klischees wie "magischer Wald" oder "sprechende Tiere". Sei wilder und überraschender! 
- Vorschlag-Ideen (Beispiele): "Zeitreisende Pizza", "Der Roboter-Flohmarkt", "Unterwasser-Bahnhof", "Die mutige Socke".
- STILE (Wähle 1-2 passende IDs):
  - Kids/All-age: `lindgren`, `funke`, `pantermueller`, `auer`, `kaestner`, `dahl`, `kinney`, `pratchett`, `adams`.
  - Humor/Satire: `loriot`, `kling`, `jaud`, `regener`, `evers`, `stuckrad_barre`, `strunk`.
  - Spannung/Drama: `fitzek`, `christie`, `king`, `zeh`, `kehlmann`, `kracht`, `kafka`, `hemingway`, `rooney`.
  - Sinnlich/Intensiv: `nin`, `miller`, `rice`.
- Gib immer 2-3 konkrete, originelle Vorschläge als "suggestions" (WICHTIG: Absolut maximal 20 Zeichen pro Vorschlag!).
- Wenn ein Bild gesendet wird, beziehe es enthusiastisch ein, aber frage trotzdem nach der Story-Idee dazu.

JSON-FORMAT:
{
  "status": "INCOMPLETE" | "READY",
  "reply": "Deine Antwort",
  "suggestions": ["Option A", "Option B"],
  "story_params": {
    "prompt": "Vollständiger, kreativer Story-Prompt",
    "genre": "Genre",
    "style": "id1, id2",
    "voice_key": "none",
    "target_minutes": 10
  }
}
"""

class ConversationService:
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
        
        full_instruction = SYSTEM_PROMPT + "\n\nAntworte im JSON-Format. Wenn Medien (Bild/Audio) vorhanden sind, beziehe dich darauf."
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
