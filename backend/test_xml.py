from twilio.twiml.messaging_response import MessagingResponse
import xml.etree.ElementTree as ET

twiml = MessagingResponse()
reply_text = "Hallo! Ich bin bereit, eine magische Geschichte für dich zu erfinden. Was soll darin vorkommen?"
suggestions = ["Ein mutiger Drache", "Ein Abenteuer im Weltraum", "Ein sprechendes Tier"]

if suggestions:
    reply_text += "\n\n💡 Vorschläge:\n" + "\n".join([f"• {s}" for s in suggestions])

twiml.message(reply_text)
xml_str = str(twiml)

try:
    ET.fromstring(xml_str)
    print("Valid XML")
    print(xml_str)
except Exception as e:
    print(f"Invalid XML: {e}")
