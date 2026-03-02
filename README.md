# Deepdive — Research Agent

An autonomous research tool that produces structured, source-backed reports on any topic. Bobby (the AI agent) drives the reasoning; the scripts handle data gathering and rendering.

## Versions

### v1 (`deepdive.py`) — Single-pass Research
Simple: decompose → search → fetch → synthesize → render. Good for quick research.

### v2 (`deepdive_v2.py`) — SuperAgent Research Loop
Multi-step: **plan → search → reflect → iterate → synthesize → render**. Inspired by [deer-flow](https://github.com/bytedance/deer-flow) (ByteDance).

Key features:
- **Iterative research loops** — searches, reflects on gaps, generates follow-up queries
- **Confidence-based stopping** — continues iterating until confidence ≥ 0.8 or max iterations reached
- **URL deduplication** — never re-fetches pages across iterations
- **State machine** — JSON session files allow pause/resume across sessions
- **Rich rendering** — HTML (dark theme) + Markdown with research methodology trail

## Architecture

```
Bobby (Agent)              deepdive_v2.py (Script)
─────────────              ──────────────────────────
Decompose question    →    init (create session)
Decide sub-queries    →    plan (record queries)
                      ←    search (execute + fetch)
Analyze results       →    reflect (gaps + follow-ups)
                      ←    search (iteration 2+)
Analyze deeper        →    reflect (confidence check)
Write final report    →    synthesize (record analysis)
                      →    render (HTML + Markdown)
```

**Zero LLM SDK calls in scripts.** All reasoning is Bobby. Scripts handle I/O only.

## Usage

```bash
# v2 (recommended): Bobby-driven multi-step loop
python3 deepdive_v2.py init "research question" --max-iterations 3
python3 deepdive_v2.py plan <session.json> --queries '["q1","q2"]'
python3 deepdive_v2.py search <session.json>
python3 deepdive_v2.py reflect <session.json> --reflection '{"gaps":[...],"follow_up_queries":[...],"confidence":0.6}'
python3 deepdive_v2.py search <session.json>  # iteration 2
python3 deepdive_v2.py reflect <session.json> --reflection '{"confidence":0.85}'
python3 deepdive_v2.py synthesize <session.json> --synthesis '{"summary":"...","sections":[...]}'
python3 deepdive_v2.py render <session.json> --format both

# v1: Quick single-pass
python3 deepdive.py "question" --sub-queries '["q1","q2"]'
```

## Example Reports

- **AI Compliance Training in Scandinavia (v2)** — 2 iterations, 8 queries, 12 sources. Found zero Nordic-specific AI compliance training providers.
- **AI Compliance Training Landscape (v1)** — Single-pass competitive intel for HverdagsAI
- **Open-Source AI Agent Frameworks 2026 (v1)** — Framework comparison

## Built by Bobby
A [Bobby's Place](https://github.com/robobobby) project — Bobby's autonomous R&D lab.
