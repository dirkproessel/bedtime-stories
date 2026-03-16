
import asyncio
import os
import sys

# Add the backend/app directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.story_generator import generate_story_hook

async def test_hooks():
    print("Testing simplified story hooks...")
    for i in range(3):
        hook = await generate_story_hook("Krimi", "kehlmann")
        print(f"\nHook {i+1}:")
        print(hook)

if __name__ == "__main__":
    asyncio.run(test_hooks())
