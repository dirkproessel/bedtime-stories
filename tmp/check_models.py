import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing models...")
for model in client.models.list():
    if 'imagen' in model.name.lower():
        print(f"Model Name: {model.name}, Supported Actions: {model.supported_actions}")

# Try a very simple image generation to test access
try:
    print("\nTesting simple image generation...")
    # response = client.models.generate_image(
    #     model='imagen-3.0-generate-001',
    #     prompt='A simple red apple',
    # )
    # print("Success!")
except Exception as e:
    print(f"Error: {e}")
