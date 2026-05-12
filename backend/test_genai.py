import os
import sys
import asyncio
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.services.text_generator import generate_text

class TestSchema(BaseModel):
    title: str
    description: str

async def main():
    try:
        res = await generate_text(
            prompt="Write a 2 sentence story about a cat.",
            model="gemini-3.1-flash-lite", # Using standard model to test
            max_tokens=100,
            response_mime_type="application/json",
            response_schema=TestSchema
        )
        print("Success:")
        print(res)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
