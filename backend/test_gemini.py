
import asyncio
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gemini_params():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found")
        return
        
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents="Hallo, erzähl einen kurzen Witz.",
            config=types.GenerateContentConfig(
                presence_penalty=0.1,
                frequency_penalty=0.1,
                temperature=0.7
            )
        )
        print("Success! Gemini supports presence/frequency penalty.")
        print(response.text)
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_params())
