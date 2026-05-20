import asyncio
import json
import os
import websockets

async def main():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url:
        print("AGY_BROWSER_WS_URL is not set!")
        return
    print("Connecting to:", ws_url)
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": "https://storyja.com/erstellen"}
        }))
        while True:
            resp = json.loads(await ws.recv())
            print("Received:", resp)
            if resp.get("id") == 1:
                break

if __name__ == "__main__":
    asyncio.run(main())
