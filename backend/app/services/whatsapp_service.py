import os
import logging
import httpx
import json
from app.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.api_version = "v20.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        
        if not self.access_token or not self.phone_number_id:
            logger.warning("WhatsApp Cloud API credentials missing (Access Token or Phone Number ID).")

    def send_message(self, to_number: str, body: str, media_url: str = None, buttons: list[str] = None):
        """Sends a WhatsApp message via Meta Cloud API with optional media or quick-reply buttons."""
        if not self.access_token or not self.phone_number_id:
            logger.error("Cannot send WhatsApp message: Credentials not configured.")
            return None
        
        # Clean up phone number
        clean_number = to_number.replace("whatsapp:", "").replace("+", "").strip()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # 1. Interactive Buttons (Quick Replies)
        # Note: Meta allows max 3 buttons, each title max 20 characters.
        if buttons and not media_url:
            valid_buttons = []
            for i, btn_text in enumerate(buttons[:3]):
                # WhatsApp limit: 20 chars per button title
                title = btn_text[:20]
                valid_buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_{i}",
                        "title": title
                    }
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {"buttons": valid_buttons}
                }
            }
        
        # 2. Image with Caption
        elif media_url:
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": "image",
                "image": {
                    "link": media_url,
                    "caption": body
                }
            }
        
        # 3. Plain Text
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_number,
                "type": "text",
                "text": {"body": body}
            }
            
        try:
            with httpx.Client() as client:
                logger.debug(f"WhatsApp API Request Payload: {json.dumps(payload)}")
                response = client.post(self.base_url, headers=headers, json=payload)
                
                if response.status_code >= 400:
                    logger.error(f"WhatsApp API Error ({response.status_code}): {response.text}")
                    return None
                    
                data = response.json()
                message_id = data.get("messages", [{}])[0].get("id")
                logger.info(f"WhatsApp message sent to {clean_number}: {message_id}")
                return message_id
        except Exception as e:
            logger.error(f"Critical error sending WhatsApp message: {e}")
            return None

whatsapp_service = WhatsAppService()
