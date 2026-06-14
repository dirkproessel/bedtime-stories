import asyncio
import httpx
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("Error: DEEPSEEK_API_KEY not found")
    sys.exit(1)

async def test_model(model_name):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Sag kurz Hallo."}
        ],
        "max_tokens": 50
    }
    
    print(f"Testing model: {model_name}...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print("JSON response:")
                print(data)
            else:
                print(f"Error Response: {resp.text}")
        except Exception as e:
            print(f"Exception for {model_name}: {e}")

async def main():
    await test_model("deepseek-v4-flash")
    print("-" * 40)
    await test_model("deepseek-v4-pro")

if __name__ == "__main__":
    asyncio.run(main())
