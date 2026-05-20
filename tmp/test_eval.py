import asyncio
import json
import os
import time
import websockets

async def test_eval():
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

        # Evaluate window.location.href
        eid = 9999
        eval_msg = {
            "id": eid,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "window.location.href",
                "returnByValue": True
            },
            "sessionId": session_id
        }
        await ws.send(json.dumps(eval_msg))
        print("Sent evaluate request")

        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print("Received:", data)
            if data.get("id") == eid:
                print("Matches EID!")
                break

asyncio.run(test_eval())
