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
        # 1. Get targets
        msg_id = 1
        await ws.send(json.dumps({"id": msg_id, "method": "Target.getTargets"}))
        target_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == msg_id:
                targets = resp["result"]["targetInfos"]
                for t in targets:
                    if t["type"] == "page":
                        target_id = t["targetId"]
                        break
                break
        
        if not target_id:
            print("Error: No page target found!")
            sys.exit(1)
            
        print(f"Attaching to target: {target_id}")
        msg_id += 1
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }))
        session_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == msg_id:
                session_id = resp["result"]["sessionId"]
                break
                
        print(f"Attached! Session ID: {session_id}")

        # Define custom send_cmd helper that waits for matching response
        # It handles incoming events by ignoring them or printing them
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
                # If we get a response to our command
                if resp.get("id") == cid:
                    if "error" in resp:
                        print(f"CDP Error in {method}: {resp['error']}")
                        return None
                    return resp.get("result")
                # If we get an event from Runtime/Console, we can print it if it's interesting
                elif "method" in resp:
                    pass # Ignore events to avoid console spam

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

        # Check current URL
        url = await eval_js("window.location.href")
        print(f"Current URL: {url}")
        
        if "storyja.com" not in str(url):
            print("Navigating to https://storyja.com ...")
            # Navigate using Page.navigate
            await send_cmd("Page.navigate", {"url": "https://storyja.com"})
            # Wait for load
            for _ in range(10):
                await asyncio.sleep(1)
                ready_state = await eval_js("document.readyState")
                curr_url = await eval_js("window.location.href")
                print(f"Waiting for load... state={ready_state}, url={curr_url}")
                if ready_state == "complete" and "storyja.com" in str(curr_url):
                    break
        
        await asyncio.sleep(2)
        await capture_screenshot("screenshot_storyja_home.png")

        # Check if we see 'Erstellen' button or link
        print("Searching for 'Erstellen' link...")
        create_href = await eval_js("""
            (() => {
                const links = Array.from(document.querySelectorAll('a'));
                for (const l of links) {
                    if (l.innerText.includes('Erstellen') || l.innerText.includes('Geschichte erstellen')) {
                        return l.href;
                    }
                }
                for (const l of links) {
                    if (l.href.includes('/erstellen') || l.href.includes('/create')) {
                        return l.href;
                    }
                }
                return null;
            })()
        """)
        print(f"Create page link: {create_href}")
        if not create_href:
            create_href = "https://storyja.com/erstellen"
            print(f"Fallback to default: {create_href}")

        print(f"Navigating to {create_href} ...")
        await send_cmd("Page.navigate", {"url": create_href})
        for _ in range(10):
            await asyncio.sleep(1)
            ready_state = await eval_js("document.readyState")
            curr_url = await eval_js("window.location.href")
            print(f"Waiting for create page load... state={ready_state}, url={curr_url}")
            if ready_state == "complete":
                break

        await asyncio.sleep(2)
        await capture_screenshot("screenshot_create_page.png")

        # Let's read inner text of body to verify if we are on login page or create page
        body_text = await eval_js("document.body.innerText")
        print(f"Body Text Preview (first 500 chars):\n{body_text[:500] if body_text else 'None'}\n")

        # If it says 'Anmelden' or 'Registrieren' or similar, we might need to log in.
        # Let's inspect form inputs on this page
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
        print("Inputs found on current page:")
        for idx, inp in enumerate(inputs_info or []):
            print(f" [{idx}] {inp['tag']}(type={inp['type']}) id={inp['id']} name={inp['name']} placeholder='{inp['placeholder']}' value='{inp['value']}' text='{inp['innerText'][:30]}'")

        # Fill and submit form
        print("Attempting to populate prompt and submit...")
        fill_res = await eval_js("""
            (() => {
                // Find prompt text area
                const textareas = Array.from(document.querySelectorAll('textarea'));
                const textInputs = Array.from(document.querySelectorAll('input[type="text"]'));
                const promptInput = textareas[0] || textInputs[0];
                if (!promptInput) return "Error: No prompt input field found";

                promptInput.value = "Ein kleiner Roboter sucht seinen Schlüssel. Er begibt sich auf ein großes Abenteuer und durchsucht verschiedene Science-Fiction Welten.";
                promptInput.dispatchEvent(new Event('input', { bubbles: true }));
                promptInput.dispatchEvent(new Event('change', { bubbles: true }));

                // Find and select Science-Fiction or Abenteuer genre
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

                // Also check select dropdowns
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

                // Find Submit/Create button
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
                    // fallback to any button containing 'story' or similar
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
        print(f"Form submission action output: {fill_res}")
        
        # Wait and poll for story to generate
        print("Polling for generated story (up to 60 seconds)...")
        generated_story = None
        for i in range(12):
            await asyncio.sleep(5)
            await capture_screenshot(f"screenshot_poll_{i}.png")
            
            # Check page innerText for story
            story_res = await eval_js("""
                (() => {
                    // Try to find paragraphs with significant length
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
            print("Could not detect story via paragraphs/article. Dumping full body innerText...")
            full_body = await eval_js("document.body.innerText")
            print("--------------------------------------------------")
            print(full_body[:1000] if full_body else "None")
            print("--------------------------------------------------")
            
            # Save whatever we have
            filepath = "tmp/generated_story_page_dump.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(full_body or "")
            print(f"Dumped full page text to {filepath}")
        else:
            filepath = "tmp/generated_story.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(generated_story)
            print(f"Saved story to {filepath}")

        await capture_screenshot("screenshot_final.png")
        print("Story generation script execution completed.")

if __name__ == "__main__":
    asyncio.run(main())
