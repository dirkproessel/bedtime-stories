import os
from google import genai
from dotenv import load_dotenv

load_dotenv(dotenv_path="backend/.env")

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    for model in client.models.list():
        if 'image' in model.name.lower():
            print(f"Model ID: {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Supported Actions: {model.supported_actions}")
except Exception as e:
    print(f"Error listing models: {e}")
