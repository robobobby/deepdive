# Builder Brief — Deepdive (Feb 28, 2026)

## What to build
`~/repos/bobbys-place/deepdive/deepdive.py` — Research-to-Report CLI

## Core pipeline (Builder 1 — 3 AM)

### Input
```
python3 deepdive.py "any research question"
```

### Steps
1. **Decompose**: Bobby breaks question into 3–5 focused sub-queries
2. **Fan out**: For each sub-query: web_search (5 results) + web_fetch top 2 URLs
3. **Synthesize**: Structure output as:
   - Executive Summary (3–4 sentences)
   - Key Findings (5–7 bullets, specific and concrete)
   - Supporting Evidence (quotes/data points with sources)
   - Open Questions (what we still don't know)
   - Sources (title + URL)
4. **Save**: Output to `output/YYYY-MM-DD-{slug}.md` and `.json`

### Constraints
- Python only: stdlib + `requests` + `pyyaml` (already installed)
- NO direct LLM SDK calls — Bobby does all reasoning
- Script handles: data gathering, file I/O, formatting
- Bobby (the agent) handles: decomposition, synthesis, all LLM work

### Output format (JSON)
```json
{
  "question": "...",
  "date": "YYYY-MM-DD",
  "sub_queries": ["...", "..."],
  "raw_results": [{"query": "...", "results": [...]}],
  "synthesis": {
    "summary": "...",
    "findings": ["..."],
    "evidence": ["..."],
    "open_questions": ["..."],
    "sources": [{"title": "...", "url": "..."}]
  }
}
```

## Delivery (Builder 2 — 5 AM)
1. HTML renderer → clean readable report page
2. Publish to MC Feed via `scripts/feed_add.py --type deep_dive`
3. Telegram summary (3 bullets + Feed link)
4. `git add . && git commit -m "feat: deepdive MVP" && git push`

## Test question for Builder 1
Use: "What is the current competitive landscape for AI compliance training platforms in Europe?"
(Relevant to HverdagsAI / AI Act Manager — gives us real intel while testing the tool)

## Repo
`~/repos/bobbys-place/deepdive/`
Already initialized with README.
