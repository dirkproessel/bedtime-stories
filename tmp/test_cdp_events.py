import asyncio
import json
import os
import time
import websockets

async def test_cdp():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url:
        print("AGY_BROWSER_WS_URL is not set!")
        return

    print("Connecting to:", ws_url)
    async with websockets.connect(ws_url) as ws:
        # Get page target
        await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        target_id = None
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                targets = msg["result"]["targetInfos"]
                page_target = next(t for t in targets if t["type"] == "page")
                target_id = page_target["targetId"]
                break
        print("Page Target ID:", target_id)

        # Attach
        await ws.send(json.dumps({
            "id": 2,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }))
        session_id = None
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 2:
                session_id = msg["result"]["sessionId"]
                break
        print("Session ID:", session_id)

        # Send Page.enable
        await ws.send(json.dumps({"id": 3, "method": "Page.enable", "sessionId": session_id}))
        # Send Runtime.enable
        await ws.send(json.dumps({"id": 4, "method": "Runtime.enable", "sessionId": session_id}))

        # Listen for 5 seconds and print all messages
        print("Listening for messages...")
        start_time = time.time()
        while time.time() - start_time < 5:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(msg)
                if "id" in data:
                    print(f"Response ID {data['id']}: {list(data.get('result', {}).keys()) or data.get('error')}")
                elif "method" in data:
                    print(f"Event: {data['method']} (params: {list(data.get('params', {}).keys())})")
                else:
                    print("Unknown msg:", data)
            except asyncio.TimeoutError:
                print("Timeout waiting for message...")

asyncio.run(test_cdp())
