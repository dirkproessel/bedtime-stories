from twilio.twiml.messaging_response import MessagingResponse

twiml = MessagingResponse()
reply_text = "Hallo! Ich bin bereit, eine magische Geschichte für dich zu erfinden. Was soll darin vorkommen?"
suggestions = ["Ein mutiger Drache", "Ein Abenteuer im Weltraum", "Ein sprechendes Tier"]

if suggestions:
    reply_text += "\n\n💡 Vorschläge:\n" + "\n".join([f"• {s}" for s in suggestions])

twiml.message(reply_text)
print(str(twiml))
