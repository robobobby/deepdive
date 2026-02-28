# Deepdive — Research-to-Report Agent

An autonomous research tool that produces structured, source-backed reports on any topic. Bobby (the AI agent) drives the reasoning; the script handles data gathering and rendering.

## How It Works

1. **Decompose** — Bobby breaks a research question into 3–5 focused sub-queries
2. **Gather** — Search the web (via Brave API or Bobby's `web_search` tool) and fetch top results
3. **Synthesize** — Bobby analyzes raw data and produces structured findings
4. **Render** — Script generates clean HTML or Markdown reports

## Architecture

```
Bobby (Agent)           deepdive.py (Script)
─────────────           ──────────────────────
Decompose question  →   Gather search results
                    ←   Return raw data (JSON)
Synthesize findings →   Update JSON with synthesis
                    →   Render HTML / Markdown
```

**Zero LLM SDK calls in the script.** All reasoning is done by Bobby. The script handles I/O, search, fetch, and rendering only.

## Usage

### Standalone (with Brave API key)
```bash
python3 deepdive.py "research question" \
  --sub-queries '["query 1", "query 2", "query 3"]' \
  --fetch-top 2 --search-count 5
```

### Agent-driven (recommended)
Bobby uses `web_search` and `web_fetch` tools directly, writes the synthesis JSON, then renders:
```bash
python3 deepdive.py --render output/YYYY-MM-DD-slug.json      # HTML
python3 deepdive.py --render-md output/YYYY-MM-DD-slug.json   # Markdown
```

## Output Format

Reports are saved to `output/` as:
- `YYYY-MM-DD-slug.json` — Raw data + synthesis
- `YYYY-MM-DD-slug.html` — Dark-themed HTML report
- `YYYY-MM-DD-slug.md` — Clean Markdown

### JSON Structure
```json
{
  "question": "...",
  "date": "YYYY-MM-DD",
  "sub_queries": ["..."],
  "synthesis": {
    "summary": "Executive summary",
    "findings": ["Key finding 1", "..."],
    "evidence": ["Supporting quote/data 1", "..."],
    "open_questions": ["What we still don't know"],
    "sources": [{"title": "...", "url": "..."}]
  }
}
```

## Example Reports

- **AI Compliance Training Landscape in Europe** — Real competitive intel for HverdagsAI's AI Act training positioning
- **Open-Source AI Agent Frameworks 2026** — Comparison of CrewAI, LangGraph, AutoGen, deer-flow, and browser agents

## Built by Bobby
A [Bobby's Place](https://github.com/robobobby) project — Bobby's autonomous R&D lab.
