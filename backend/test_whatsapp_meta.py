import os
import sys
from pathlib import Path

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.whatsapp_service import whatsapp_service
from app.config import settings

def test_send():
    to_number = input("Enter your phone number (with country code, e.g. 49170...): ").strip()
    message = "Test-Nachricht von der neuen WhatsApp Cloud API! 🚀"
    
    print(f"Sending to {to_number}...")
    result = whatsapp_service.send_message(to_number, message)
    
    if result:
        print(f"Success! Message ID: {result}")
    else:
        print("Failed to send message. Check the logs.")

if __name__ == "__main__":
    test_send()
