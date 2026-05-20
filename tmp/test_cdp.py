import asyncio
import json
import os
import websockets

async def test():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    print("Browser WebSocket URL:", ws_url)
    if not ws_url:
        print("AGY_BROWSER_WS_URL not set!")
        return

    async with websockets.connect(ws_url) as websocket:
        # Get targets
        msg = {
            "id": 1,
            "method": "Target.getTargets"
        }
        await websocket.send(json.dumps(msg))
        
        response = await websocket.recv()
        data = json.loads(response)
        print("Targets:")
        print(json.dumps(data, indent=2))

asyncio.run(test())
