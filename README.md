# VizQA — Visual QA Agent (Web App)

A browser-based tool that automates the **build → visually inspect → describe fixes → re-prompt** loop for local web development.

## How It Works

```
┌──────────┐    ┌──────────────┐    ┌────────────┐    ┌───────────────┐
│ Your App │───▶│  Playwright  │───▶│  Gemini    │───▶│  Accept/     │───▶ Claude Code
│ localhost│    │  Screenshots │    │  Review    │    │  Reject UI   │     Prompt
└──────────┘    └──────────────┘    └────────────┘    └───────────────┘
```

1. **Capture**: Playwright opens your localhost, optionally runs a test flow, takes screenshots
2. **Review**: Screenshots sent to Gemini Flash for visual analysis → structured edit suggestions
3. **Accept/Reject**: You review each suggestion (like Cursor's accept/reject UI)
4. **Compile**: Accepted edits are compiled into an optimized Claude Code prompt

## Setup

```bash
# Clone / copy the project
cd vizqa-app

# Install Python deps
pip install -r requirements.txt
playwright install chromium

# Set up .env
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
# Get a free key at: https://aistudio.google.com/app/apikey

# Run the server
uvicorn server:app --reload --port 8899

# Open http://localhost:8899 in your browser
```

## Files

```
vizqa-app/
├── server.py                    # FastAPI backend
├── requirements.txt
├── .env.example                 # Copy to .env and add your key
├── frontend/
│   └── index.html               # React frontend (single file)
├── prompts/
│   ├── visual_review_prompt.md  # LLM prompt for visual analysis (edit this!)
│   └── claude_code_llm_prompt.md # LLM prompt for compiling Claude Code prompts
└── vizqa_output/                # Screenshots saved here
```

## Customizing

- **`prompts/visual_review_prompt.md`** — Tune what the visual reviewer looks for. Add your design system rules, color palette, spacing scale, etc.
- **`prompts/claude_code_llm_prompt.md`** — Tune how the Claude Code prompt is compiled. Add your project structure, coding conventions, etc.
- **`.env MODEL`** — Change the Gemini model (default: `gemini-2.5-flash-preview-05-20`)

## Usage Tips

- Start your dev server first (`npm run dev` etc.) before capturing
- Use the **Flow JSON** field for multi-step interactions (login flows, form submissions)
- **Desktop viewport** is the default — add mobile/tablet for responsive testing
- The compiled prompt is optimized for Claude Code CLI: `claude -p "paste prompt here"`
