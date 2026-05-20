import asyncio
import json
import os
import base64
import sys
import time
import websockets

async def main():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url:
        print("Error: AGY_BROWSER_WS_URL is not set!")
        sys.exit(1)

    print(f"Connecting to browser WebSocket: {ws_url}")
    async with websockets.connect(ws_url) as ws:
        msg_id = 1
        
        # 1. Create a NEW target (tab) for storyja.com/erstellen
        print("Creating a new background target for https://storyja.com/erstellen ...")
        create_msg = {
            "id": msg_id,
            "method": "Target.createTarget",
            "params": {
                "url": "https://storyja.com/erstellen"
            }
        }
        await ws.send(json.dumps(create_msg))
        
        new_target_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == msg_id:
                new_target_id = resp["result"]["targetId"]
                break
        
        print(f"New Target created with ID: {new_target_id}")
        
        # 2. Attach to the new target
        msg_id += 1
        print(f"Attaching to target: {new_target_id}")
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Target.attachToTarget",
            "params": {"targetId": new_target_id, "flatten": True}
        }))
        
        session_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == msg_id:
                session_id = resp["result"]["sessionId"]
                break
                
        print(f"Attached! Session ID: {session_id}")

        # Define custom send_cmd helper scoped to the new session
        async def send_cmd(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cid = msg_id
            payload = {
                "id": cid,
                "method": method,
                "sessionId": session_id
            }
            if params:
                payload["params"] = params
                
            await ws.send(json.dumps(payload))
            
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == cid:
                    if "error" in resp:
                        print(f"CDP Error in {method}: {resp['error']}")
                        return None
                    return resp.get("result")
                elif "method" in resp:
                    pass # ignore events

        async def eval_js(expr):
            res = await send_cmd("Runtime.evaluate", {
                "expression": expr,
                "returnByValue": True
            })
            if res and "result" in res:
                if "exceptionDetails" in res:
                    print(f"JS Exception in '{expr}': {res['exceptionDetails']}")
                    return None
                return res["result"].get("value")
            return None

        async def capture_screenshot(filename):
            print(f"Capturing screenshot: {filename}...")
            res = await send_cmd("Page.captureScreenshot", {"format": "png"})
            if res and "data" in res:
                img_data = base64.b64decode(res["data"])
                os.makedirs("tmp", exist_ok=True)
                filepath = os.path.join("tmp", filename)
                with open(filepath, "wb") as f:
                    f.write(img_data)
                print(f"Screenshot saved to {filepath}")
                return filepath
            print("Failed to capture screenshot")
            return None

        # 3. Wait for the page to load
        print("Waiting for page load...")
        for i in range(15):
            await asyncio.sleep(1)
            ready_state = await eval_js("document.readyState")
            curr_url = await eval_js("window.location.href")
            print(f"[{i}s] state={ready_state}, url={curr_url}")
            if ready_state == "complete":
                break

        await asyncio.sleep(2)
        await capture_screenshot("screenshot_new_target_loaded.png")

        # Get body text
        body_text = await eval_js("document.body.innerText")
        print(f"Body Text Preview:\n{body_text[:500] if body_text else 'None'}\n")

        # Inspect inputs
        inputs_info = await eval_js("""
            (() => {
                const els = Array.from(document.querySelectorAll('input, textarea, select, button'));
                return els.map(e => ({
                    tag: e.tagName,
                    type: e.type || '',
                    id: e.id || '',
                    name: e.name || '',
                    placeholder: e.placeholder || '',
                    value: e.value || '',
                    innerText: e.innerText || ''
                }));
            })()
        """)
        print("Inputs found:")
        for idx, inp in enumerate(inputs_info or []):
            print(f" [{idx}] {inp['tag']}(type={inp['type']}) id='{inp['id']}' name='{inp['name']}' placeholder='{inp['placeholder']}' value='{inp['value']}' text='{inp['innerText'][:30]}'")

        # Try to fill and submit
        print("Attempting to populate form...")
        fill_res = await eval_js("""
            (() => {
                const textareas = Array.from(document.querySelectorAll('textarea'));
                const textInputs = Array.from(document.querySelectorAll('input[type="text"]'));
                const promptInput = textareas[0] || textInputs[0];
                if (!promptInput) return "Error: No prompt input field found";

                promptInput.value = "Ein kleiner Roboter sucht seinen Schlüssel. Er begibt sich auf ein großes Abenteuer und durchsucht verschiedene Science-Fiction Welten.";
                promptInput.dispatchEvent(new Event('input', { bubbles: true }));
                promptInput.dispatchEvent(new Event('change', { bubbles: true }));

                const options = Array.from(document.querySelectorAll('*'));
                let genreClicked = false;
                for (const opt of options) {
                    const txt = (opt.innerText || '').trim();
                    if (txt === 'Science-Fiction' || txt === 'Abenteuer' || txt === 'Sci-Fi') {
                        opt.click();
                        genreClicked = true;
                        break;
                    }
                }

                const selects = Array.from(document.querySelectorAll('select'));
                for (const select of selects) {
                    for (const option of Array.from(select.options)) {
                        const val = option.text + ' ' + option.value;
                        if (val.includes('Science-Fiction') || val.includes('Abenteuer') || val.includes('science-fiction')) {
                            select.value = option.value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            genreClicked = true;
                            break;
                        }
                    }
                }

                const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
                let submitBtn = null;
                for (const btn of buttons) {
                    const text = (btn.innerText || btn.value || '').toLowerCase();
                    if (text.includes('erstellen') || text.includes('generieren') || text.includes('los') || text.includes('starten') || text.includes('schreiben')) {
                        submitBtn = btn;
                        break;
                    }
                }

                if (!submitBtn && buttons.length > 0) {
                    for (const btn of buttons) {
                        if ((btn.innerText || '').toLowerCase().includes('story')) {
                            submitBtn = btn;
                            break;
                        }
                    }
                }

                if (!submitBtn) return "Error: No submit/generate button found";

                submitBtn.click();
                return {
                    success: true,
                    prompt: promptInput.value,
                    genreClicked: genreClicked,
                    buttonClicked: submitBtn.innerText || submitBtn.className
                };
            })()
        """)
        print(f"Fill/Submit Action result: {fill_res}")

        # Wait and poll for story to generate
        print("Polling for generated story (up to 90 seconds)...")
        generated_story = None
        for i in range(18):
            await asyncio.sleep(5)
            await capture_screenshot(f"screenshot_poll_v3_{i}.png")
            
            story_res = await eval_js("""
                (() => {
                    const ps = Array.from(document.querySelectorAll('p'));
                    const story_ps = ps.filter(p => p.innerText.length > 150);
                    if (story_ps.length >= 2) {
                        return story_ps.map(p => p.innerText).join('\\n\\n');
                    }
                    const article = document.querySelector('article');
                    if (article && article.innerText.length > 300) {
                        return article.innerText;
                    }
                    return null;
                })()
            """)
            
            curr_url = await eval_js("window.location.href")
            print(f"[{i*5}s] URL: {curr_url}")
            
            if story_res:
                generated_story = story_res
                print("Success! Story found:")
                print("--------------------------------------------------")
                print(generated_story[:600] + "\n...")
                print("--------------------------------------------------")
                break
        
        if not generated_story:
            print("Could not detect story via standard containers. Dumping full page text...")
            full_body = await eval_js("document.body.innerText")
            print("--------------------------------------------------")
            print(full_body[:1000] if full_body else "None")
            print("--------------------------------------------------")
            
            filepath = "tmp/generated_story_page_dump.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_body or "")
            print(f"Dumped full page text to {filepath}")
        else:
            filepath = "tmp/generated_story.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(generated_story)
            print(f"Saved story to {filepath}")

        await capture_screenshot("screenshot_final_v3.png")
        
        # 4. Clean up / close the tab
        print(f"Closing the target tab: {new_target_id}")
        msg_id += 1
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Target.closeTarget",
            "params": {"targetId": new_target_id}
        }))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == msg_id:
                print("Target closed successfully.")
                break

        print("Finished!")

if __name__ == "__main__":
    asyncio.run(main())
