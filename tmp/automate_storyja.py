import asyncio
import json
import os
import websockets

async def run_cdp():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url: return

    async with websockets.connect(ws_url) as ws:
        msg = {"id": 1, "method": "Target.getTargets"}
        await ws.send(json.dumps(msg))
        
        target_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 1:
                for t in resp["result"]["targetInfos"]:
                    if t["type"] == "page":
                        target_id = t["targetId"]
                        break
                break
        
        attach_msg = {
            "id": 2,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }
        await ws.send(json.dumps(attach_msg))
        
        session_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 2:
                session_id = resp["result"]["sessionId"]
                break
        
        # Get all links
        eval_msg = {
            "id": 3,
            "method": "Runtime.evaluate",
            "params": {
                "expression": """
                Array.from(document.querySelectorAll('a, button')).map(el => ({
                    tagName: el.tagName,
                    text: el.innerText || el.value,
                    href: el.href || '',
                    id: el.id,
                    className: el.className
                }))
                """,
                "returnByValue": True
            },
            "sessionId": session_id
        }
        await ws.send(json.dumps(eval_msg))
        
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 3:
                elements = resp["result"]["result"]["value"]
                print("Interactive Elements:")
                for el in elements:
                    if el['text'] or el['href']:
                        print(f"Tag: {el['tagName']}, Text: '{el['text'].strip()}', Href: '{el['href']}', ID: '{el['id']}', Class: '{el['className']}'")
                break

asyncio.run(run_cdp())
