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
        # Get targets
        await ws.send(json.dumps({"id": 1, "method": "Target.getTargets"}))
        target_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 1:
                targets = resp["result"]["targetInfos"]
                # Look for the target that we hijacked (usually the active page)
                for t in targets:
                    if t["type"] == "page":
                        target_id = t["targetId"]
                        break
                break
                
        if not target_id:
            print("No page target found!")
            return
            
        print(f"Attaching to target: {target_id}")
        await ws.send(json.dumps({
            "id": 2,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }))
        session_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 2:
                session_id = resp["result"]["sessionId"]
                break
                
        # Navigate back to the original app URL
        orig_url = "https://127.0.0.1:63299/c/b5bf4ed9-1efb-4a24-bafe-0d839873c367?section=fdbb54b8-6a0b-40f1-adc0-2bfeea7ed231"
        print(f"Navigating back to: {orig_url}")
        
        await ws.send(json.dumps({
            "id": 3,
            "method": "Page.navigate",
            "params": {"url": orig_url},
            "sessionId": session_id
        }))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 3:
                print("Navigation command response received.")
                break
        print("Restored!")

if __name__ == "__main__":
    asyncio.run(main())
