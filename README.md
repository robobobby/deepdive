# Deepdive v2 — SuperAgent Research Loop

Multi-step research tool: **plan → search → reflect → iterate → synthesize → render**.

Inspired by [deer-flow](https://github.com/bytedance/deer-flow) (ByteDance). Bobby drives all reasoning; the script handles I/O.

## Quick Start

```bash
# 1. Initialize
python3 deepdive_v2.py init "Your research question" --max-iterations 3

# 2. Plan (Bobby decides sub-queries)
python3 deepdive_v2.py plan session.json --queries '["query1","query2"]'

# 3. Search (script fetches results)
python3 deepdive_v2.py search session.json --fetch-top 3

# 4. Reflect (Bobby identifies gaps)
python3 deepdive_v2.py reflect session.json --reflection '{"gaps":["..."],"follow_up_queries":["..."],"confidence":0.6}'

# 5. Repeat search/reflect until confidence ≥ 0.8 or max iterations

# 6. Synthesize (Bobby writes final analysis)
python3 deepdive_v2.py synthesize session.json --synthesis '{"summary":"...","sections":[...],"sources":[...]}'

# 7. Render
python3 deepdive_v2.py render session.json --format both

# 8. Triangulate (check source quality)
python3 deepdive_v2.py triangulate session.json
```

## Commands

| Command | What it does |
|---------|-------------|
| `init` | Create a new research session |
| `plan` | Record Bobby's query decomposition |
| `search` | Execute Brave searches + fetch top pages |
| `reflect` | Record gaps, follow-ups, confidence |
| `synthesize` | Record final structured analysis |
| `render` | Generate HTML + Markdown reports |
| `triangulate` | Analyze source independence per section |
| `status` | Print session state |

## Features

- **Iterative research** with confidence-based stopping (default: 0.8)
- **URL deduplication** across iterations
- **Source triangulation** scoring (strong/moderate/weak per section)
- **Session persistence** — JSON state files for pause/resume
- **Dark-themed HTML** reports with research methodology trail
- **Zero dependencies** — pure Python stdlib
- **Zero cost** — uses Bobby's native search + reasoning

## Output

Reports include:
- Executive summary
- Structured sections with findings + evidence
- Source list with relevance notes
- Research methodology trail (queries per iteration)
- Open questions for further investigation

## Architecture

```
Bobby (LLM)          deepdive_v2.py (I/O)
    │                      │
    ├─ decides queries ───→ plan
    │                      │
    │  ←── search results ─ search (Brave API + fetch)
    │                      │
    ├─ identifies gaps ───→ reflect
    │                      │
    │  (loop if confidence < 0.8)
    │                      │
    ├─ writes synthesis ──→ synthesize
    │                      │
    │  ←── HTML + MD ────── render
```

Bobby does ALL reasoning. The script never calls an LLM.
