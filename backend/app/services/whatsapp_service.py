import os
import logging
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            logger.warning("Twilio credentials missing. WhatsAppService will not be able to send messages.")
            self.client = None

    def send_message(self, to_number: str, body: str):
        """Sends a WhatsApp message via Twilio."""
        if not self.client:
            logger.error("Cannot send WhatsApp message: Twilio client not initialized.")
            return None
        
        try:
            # Ensure the numbers have the whatsapp: prefix
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            from_number = self.from_number
            if not from_number.startswith("whatsapp:"):
                from_number = f"whatsapp:{from_number}"
                
            message = self.client.messages.create(
                from_=from_number,
                body=body,
                to=to_number
            )
            logger.info(f"WhatsApp message sent to {to_number}: {message.sid}")
            return message.sid
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return None

whatsapp_service = WhatsAppService()
