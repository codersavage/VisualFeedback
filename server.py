"""
VizQA Web App — Backend
=======================
FastAPI server that handles:
  1. Browser automation (Playwright screenshots)
  2. LLM visual review (Gemini)
  3. Claude Code prompt compilation

Run: uvicorn server:app --reload --port 8899
"""

import asyncio
import base64
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("MODEL")
PROMPT_DIR = Path(__file__).parent / "prompts"
OUTPUT_DIR = Path(__file__).parent / "vizqa_output"
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="VizQA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CaptureRequest(BaseModel):
    url: str
    description: str
    tech_stack: str = ""
    viewports: list[str] = ["desktop"]
    flow: Optional[list[dict]] = None


class ReviewRequest(BaseModel):
    screenshots: list[dict]  # [{path, viewport, step}]
    description: str
    tech_stack: str = ""


class CompileRequest(BaseModel):
    accepted_edits: list[dict]  # [{id, priority, category, description, fix, location}]
    description: str
    tech_stack: str = ""


# ---------------------------------------------------------------------------
# Playwright — capture screenshots
# ---------------------------------------------------------------------------

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 720},
    "mobile": {"width": 375, "height": 812},
    "tablet": {"width": 768, "height": 1024},
}


async def capture_screenshots(req: CaptureRequest) -> list[dict]:
    from playwright.async_api import async_playwright

    screenshots = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for vp_name in req.viewports:
            vp = VIEWPORTS.get(vp_name, VIEWPORTS["desktop"])
            context = await browser.new_context(viewport=vp)
            page = await context.new_page()

            await page.goto(req.url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)

            if not req.flow:
                path = OUTPUT_DIR / f"screenshot_{vp_name}.png"
                await page.screenshot(path=str(path), full_page=True)
                screenshots.append({
                    "path": str(path),
                    "viewport": vp_name,
                    "step": "initial",
                })
            else:
                for i, step in enumerate(req.flow):
                    step_name = step.get("name", f"step_{i+1}")
                    await _execute_step(page, step)
                    await asyncio.sleep(step.get("wait", 0.5))
                    path = OUTPUT_DIR / f"screenshot_{vp_name}_{i+1:02d}_{step_name}.png"
                    await page.screenshot(path=str(path), full_page=True)
                    screenshots.append({
                        "path": str(path),
                        "viewport": vp_name,
                        "step": step_name,
                    })

            await context.close()
        await browser.close()

    return screenshots


async def _execute_step(page, step: dict):
    action = step.get("action", "")
    selector = step.get("selector", "")
    if action == "click":
        await page.click(selector, timeout=10000)
    elif action == "fill":
        await page.fill(selector, step.get("value", ""))
    elif action == "type":
        await page.type(selector, step.get("value", ""), delay=step.get("delay", 50))
    elif action == "wait":
        await page.wait_for_selector(selector, timeout=step.get("timeout", 10000))
    elif action == "scroll":
        await page.evaluate(f"window.scrollTo(0, {step.get('y', 'document.body.scrollHeight')})")
    elif action == "hover":
        await page.hover(selector)
    elif action == "press":
        await page.keyboard.press(step.get("key", "Enter"))
    elif action == "goto":
        await page.goto(step.get("url", ""), wait_until="networkidle")


# ---------------------------------------------------------------------------
# Gemini — visual review
# ---------------------------------------------------------------------------

def run_visual_review(screenshots: list[dict], description: str, tech_stack: str = "") -> list[dict]:
    """Send screenshots to Gemini, parse structured edit suggestions."""
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")

    # Load prompt
    prompt_path = PROMPT_DIR / "visual_review_prompt.md"
    system_prompt = prompt_path.read_text() if prompt_path.exists() else "List visual issues."

    # Build parts
    parts = []
    context_text = f"## Feature Description\n{description}\n"
    if tech_stack:
        context_text += f"\n## Tech Stack\n{tech_stack}\n"
    context_text += f"\n## Screenshots ({len(screenshots)}):\n"
    for s in screenshots:
        context_text += f"- {s['viewport']} / {s['step']}\n"

    parts.append(system_prompt + "\n\n---\n\n" + context_text)

    for s in screenshots:
        img_bytes = Path(s["path"]).read_bytes()
        parts.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
        parts.append(f"[Screenshot: {s['viewport']} — {s['step']}]")

    # Add instruction to return JSON
    parts.append("""

IMPORTANT: In addition to your analysis above, also return a JSON block at the very end of your response in this exact format:

```json
[
  {
    "id": "1",
    "priority": "critical|important|nice-to-have",
    "category": "Layout|Visual|UX|Content|Accessibility",
    "title": "Short title",
    "description": "What's wrong",
    "fix": "Specific code-level fix suggestion",
    "location": "Where on the page"
  }
]
```

Make sure the JSON is valid and wrapped in ```json``` code fences.
""")

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model=MODEL, contents=parts)
    raw_text = response.text

    # Parse JSON from response
    edits = _parse_edits(raw_text)
    return edits, raw_text


def _parse_edits(text: str) -> list[dict]:
    """Extract JSON array of edits from LLM response."""
    # Try to find ```json ... ``` block
    match = re.search(r"```json\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Fallback: try to find any JSON array
    match = re.search(r"\[\s*\{.*?\}\s*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return []


# ---------------------------------------------------------------------------
# Claude Code prompt compiler
# ---------------------------------------------------------------------------

def compile_claude_code_prompt(
    accepted_edits: list[dict],
    description: str,
    tech_stack: str = "",
) -> str:
    """Compile accepted edits into an optimized Claude Code prompt."""
    from google import genai
    from google.genai import types

    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set in .env")

    # Load the Claude Code optimization prompt
    prompt_path = PROMPT_DIR / "claude_code_llm_prompt.md"
    compiler_prompt = prompt_path.read_text() if prompt_path.exists() else ""

    edits_text = ""
    for i, edit in enumerate(accepted_edits, 1):
        edits_text += f"\n{i}. [{edit.get('priority', 'important').upper()}] {edit.get('category', 'General')}: {edit.get('title', '')}\n"
        edits_text += f"   Issue: {edit.get('description', '')}\n"
        edits_text += f"   Fix: {edit.get('fix', '')}\n"
        edits_text += f"   Location: {edit.get('location', '')}\n"

    user_content = f"""## Context
Feature: {description}
Tech Stack: {tech_stack or 'Not specified'}

## Accepted Visual Edits
{edits_text}

## Task
Compile these accepted edits into a single, optimized Claude Code prompt that will implement all the fixes efficiently. Follow the guidelines in the system prompt for Claude Code prompt optimization.
Return ONLY the final prompt text, nothing else. Do not wrap it in code fences.
"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=[compiler_prompt + "\n\n---\n\n" + user_content],
    )
    return response.text


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.post("/api/capture")
async def api_capture(req: CaptureRequest):
    """Capture screenshots from target URL."""
    try:
        screenshots = await capture_screenshots(req)
        # Convert screenshots to base64 for frontend display
        results = []
        for s in screenshots:
            img_bytes = Path(s["path"]).read_bytes()
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            results.append({
                **s,
                "image_b64": b64,
            })
        return {"screenshots": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review")
async def api_review(req: ReviewRequest):
    """Send screenshots to Gemini for visual review."""
    try:
        edits, raw_text = run_visual_review(req.screenshots, req.description, req.tech_stack)
        return {"edits": edits, "raw_review": raw_text}
    except Exception as e:
        # You can optionally print(e) here for logs
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compile")
async def api_compile(req: CompileRequest):
    """Compile accepted edits into Claude Code prompt."""
    try:
        prompt = compile_claude_code_prompt(req.accepted_edits, req.description, req.tech_stack)
        return {"prompt": prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
