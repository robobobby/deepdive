# 🔬 Deepdive — Research-to-Report Agent

Autonomous research tool that fans out web searches, gathers source content, and synthesizes structured reports. Built on Bobby's existing OpenClaw infrastructure — zero external LLM API costs.

## How It Works

```
Question → Decompose → Search (Brave) → Fetch (top sources) → Synthesize → HTML Report → MC Feed
```

Bobby (the agent) drives the pipeline using his built-in tools:
1. **Decompose** — Bobby breaks the question into 3-5 focused sub-queries
2. **Gather** — `web_search` + `web_fetch` tools collect raw data
3. **Synthesize** — Bobby analyzes raw data and produces structured findings
4. **Render** — `deepdive.py --render` generates a styled HTML report
5. **Publish** — Report goes to MC Feed and/or Telegram

## Output Format

Each report produces:
- **JSON** — Structured data with raw results + synthesis
- **HTML** — Dark-themed, clean report page
- **Markdown** — For MC Feed publishing

### Synthesis Structure
- Executive Summary (3-4 sentences)
- Key Findings (5-8 specific bullets)
- Supporting Evidence (quotes/data with sources)
- Open Questions (what we still don't know)
- Sources (title + URL)

## Usage

```bash
# Render HTML from a completed synthesis
python3 deepdive.py --render output/2026-02-28-topic.json

# Full pipeline is agent-driven (Bobby uses his tools)
```

## Architecture

```
deepdive.py          — Data gathering + HTML rendering (no LLM calls)
output/              — Generated reports (JSON + HTML)
BUILDER_BRIEF.md     — Original build spec
```

### Why no direct LLM calls?

Bobby runs on Claude Max subscription. Scripts call LLM SDKs = unnecessary API costs. Instead, Bobby does all reasoning natively, and the script handles I/O and formatting.

## Cost

**$0** — Uses Bobby's existing Claude Max subscription + Brave Search free tier (2000/month).

## Example Reports

- [AI Compliance Training in Europe](output/2026-02-28-ai-compliance-training-europe.json) — Competitive landscape analysis for HverdagsAI

## Built With

- Python 3 (stdlib only, no pip dependencies)
- Bobby's OpenClaw tools (web_search, web_fetch)
- Claude Max subscription (synthesis)

---

*Part of [Bobby's Place](https://github.com/robobobby) R&D lab.*
