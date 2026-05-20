import asyncio
import json
import os
import websockets

async def main():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url:
        print("AGY_BROWSER_WS_URL is not set!")
        return
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 1:
                print(json.dumps(resp["result"]["targetInfos"], indent=2))
                break

if __name__ == "__main__":
    asyncio.run(main())
