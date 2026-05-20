import asyncio
import json
import os
import base64
import time
import websockets

async def run_story_generation():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url:
        print("AGY_BROWSER_WS_URL is not set!")
        return

    async with websockets.connect(ws_url) as ws:
        # 1. Get page target
        print("Step 1: Listing targets...")
        msg = {"id": 1, "method": "Target.getTargets"}
        await ws.send(json.dumps(msg))
        
        target_id = None
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 1:
                targets = resp["result"]["targetInfos"]
                for t in targets:
                    if t["type"] == "page":
                        target_id = t["targetId"]
                        break
                break
        
        if not target_id:
            print("No page target found!")
            return
            
        print(f"Attaching to page target: {target_id}")
        
        # 2. Attach to target
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
        
        print(f"Attached! Session ID: {session_id}")
        
        # Enable domains
        await ws.send(json.dumps({"id": 3, "method": "Page.enable", "sessionId": session_id}))
        await ws.send(json.dumps({"id": 4, "method": "Runtime.enable", "sessionId": session_id}))
        
        # Helper to execute JS
        async def eval_js(expr):
            eid = int(time.time() * 1000)
            eval_msg = {
                "id": eid,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expr,
                    "returnByValue": True
                },
                "sessionId": session_id
            }
            await ws.send(json.dumps(eval_msg))
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == eid:
                    result_obj = resp.get("result", {})
                    if "exceptionDetails" in result_obj:
                        print("JS Error:", result_obj["exceptionDetails"])
                        return None
                    return result_obj.get("result", {}).get("value")

        # Helper to take screenshot
        async def take_screenshot(filename):
            eid = int(time.time() * 1000)
            screenshot_msg = {
                "id": eid,
                "method": "Page.captureScreenshot",
                "params": {"format": "png"},
                "sessionId": session_id
            }
            await ws.send(json.dumps(screenshot_msg))
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == eid:
                    img_data = resp["result"]["data"]
                    os.makedirs("tmp", exist_ok=True)
                    with open(f"tmp/{filename}", "wb") as f:
                        f.write(base64.b64decode(img_data))
                    print(f"Screenshot saved to tmp/{filename}")
                    break

        # 3. Check if we are on storyja.com
        url = await eval_js("window.location.href")
        print("Current URL:", url)
        if "storyja.com" not in url:
            print("Navigating to https://storyja.com ...")
            await ws.send(json.dumps({
                "id": 5,
                "method": "Page.navigate",
                "params": {"url": "https://storyja.com"},
                "sessionId": session_id
            }))
            # Wait for response for navigate
            while True:
                resp = json.loads(await ws.recv())
                if resp.get("id") == 5:
                    break
            await asyncio.sleep(5)

        # Take screenshot of home page
        await take_screenshot("screenshot_home.png")

        # 4. Find create link and navigate
        print("Step 2: Finding 'Erstellen' page link...")
        create_href = await eval_js("""
            (() => {
                const links = Array.from(document.querySelectorAll('a'));
                // Look for text match
                for (const l of links) {
                    if (l.innerText.includes('Erstellen') || l.innerText.includes('Geschichte erstellen')) {
                        return l.href;
                    }
                }
                // Look for path match
                for (const l of links) {
                    if (l.href.includes('/erstellen') || l.href.includes('/create')) {
                        return l.href;
                    }
                }
                return null;
            })()
        """)
        print("Found create link href:", create_href)
        
        if not create_href:
            # Try guessing URL
            create_href = "https://storyja.com/erstellen"
            print("Could not find href on home page, guessing:", create_href)

        # Navigate to create page
        print("Navigating to create page...")
        await ws.send(json.dumps({
            "id": 10,
            "method": "Page.navigate",
            "params": {"url": create_href},
            "sessionId": session_id
        }))
        while True:
            resp = json.loads(await ws.recv())
            if resp.get("id") == 10:
                break
        
        print("Waiting 5 seconds for create page to load...")
        await asyncio.sleep(5)
        await take_screenshot("screenshot_create_page_init.png")

        create_page_text = await eval_js("document.body.innerText.substring(0, 1500)")
        print("Create page text preview:")
        print(create_page_text)

        # 5. Inspect the form elements
        print("Step 3: Inspecting form elements...")
        form_info = await eval_js("""
            (() => {
                const inputs = Array.from(document.querySelectorAll('input, textarea, select, button'));
                return inputs.map((el, index) => ({
                    index: index,
                    tagName: el.tagName,
                    type: el.type || '',
                    id: el.id || '',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    value: el.value || '',
                    text: el.innerText || '',
                    className: el.className || ''
                }));
            })()
        """)
        
        for item in form_info:
            print(f"[{item['index']}] {item['tagName']}(type={item['type']}) id='{item['id']}' name='{item['name']}' placeholder='{item['placeholder']}' text='{item['text'].strip()[:50]}'")

        # Let's find inputs for story description/prompt and genre selection.
        # Typically there is a textarea or input for prompt, and some select or button group for genre.
        # Let's write a JS snippet that populates them.
        print("Step 4: Filling in form and submitting...")
        
        fill_result = await eval_js("""
            (() => {
                // Find story idea input
                const textareas = Array.from(document.querySelectorAll('textarea'));
                const inputs = Array.from(document.querySelectorAll('input[type="text"]'));
                
                let promptInput = textareas[0] || inputs[0];
                if (!promptInput) return "No prompt input found";
                
                // Fill prompt
                promptInput.value = "Ein kleiner Roboter sucht seinen Schlüssel. Er begibt sich auf ein großes Abenteuer und durchsucht verschiedene Science-Fiction Welten.";
                promptInput.dispatchEvent(new Event('input', { bubbles: true }));
                promptInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Let's look for Genre select or button
                // Let's find buttons or elements with "Abenteuer" or "Science-Fiction"
                const allElements = Array.from(document.querySelectorAll('*'));
                let genreElement = null;
                for (const el of allElements) {
                    if (el.innerText && (el.innerText.trim() === 'Science-Fiction' || el.innerText.trim() === 'Abenteuer')) {
                        genreElement = el;
                        break;
                    }
                }
                
                // Also check select dropdowns
                const selects = Array.from(document.querySelectorAll('select'));
                let selectedGenre = false;
                for (const select of selects) {
                    for (const option of Array.from(select.options)) {
                        if (option.text.includes('Science-Fiction') || option.text.includes('Abenteuer') || option.value.includes('science-fiction') || option.value.includes('abenteuer')) {
                            select.value = option.value;
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            selectedGenre = true;
                            break;
                        }
                    }
                }
                
                if (genreElement) {
                    genreElement.click();
                    selectedGenre = true;
                }
                
                // Let's find the generate / submit button
                // Look for button with text "Erstellen" or "Generieren" or "Starten"
                const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));
                let submitBtn = null;
                for (const btn of buttons) {
                    const text = (btn.innerText || btn.value || '').toLowerCase();
                    if (text.includes('erstellen') || text.includes('generieren') || text.includes('starten') || text.includes('schreiben') || text.includes('los')) {
                        submitBtn = btn;
                        break;
                    }
                }
                
                if (!submitBtn && buttons.length > 0) {
                    // fall back to last button or one that looks like a primary button
                    submitBtn = buttons[buttons.length - 1];
                }
                
                if (!submitBtn) return "No submit button found";
                
                // Click the submit button
                submitBtn.click();
                return {
                    success: true,
                    promptUsed: promptInput.value,
                    selectedGenre: selectedGenre,
                    buttonClicked: submitBtn.innerText || submitBtn.className
                };
            })()
        """)
        
        print("Fill and Click result:", fill_result)
        
        # Wait for generation to start and progress (poll for 45 seconds)
        print("Step 5: Waiting for story generation (polling)...")
        for i in range(9):
            await asyncio.sleep(5)
            await take_screenshot(f"screenshot_generating_step_{i}.png")
            curr_url = await eval_js("window.location.href")
            print(f"[{i*5}s] URL: {curr_url}")
            
            # Check if story has appeared
            story_text = await eval_js("""
                (() => {
                    // Look for elements that might hold the story
                    // Or check page text for long stories
                    const paragraphs = Array.from(document.querySelectorAll('p'));
                    const storyParagraphs = paragraphs.filter(p => p.innerText.length > 150);
                    if (storyParagraphs.length >= 2) {
                        return storyParagraphs.map(p => p.innerText).join('\\n\\n');
                    }
                    // Let's also check if there is an article or specific div
                    const article = document.querySelector('article');
                    if (article && article.innerText.length > 300) {
                        return article.innerText;
                    }
                    return null;
                })()
            """)
            
            if story_text:
                print("Generated Story found!")
                print("----------------------------------------")
                print(story_text[:500] + "...")
                print("----------------------------------------")
                with open("tmp/generated_story.txt", "w", encoding="utf-8") as f:
                    f.write(story_text)
                print("Saved story to tmp/generated_story.txt")
                break
        else:
            # If polling finished and story not found in specific elements, let's extract the whole page text
            print("Specific story elements not found. Saving whole page innerText.")
            full_text = await eval_js("document.body.innerText")
            with open("tmp/generated_story_full_page.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
            print("Saved full page text to tmp/generated_story_full_page.txt")

        # Take final screenshot
        await take_screenshot("screenshot_story_final.png")
        print("Done!")

asyncio.run(run_story_generation())
