#!/usr/bin/env python3
"""
Deepdive v2 — SuperAgent Research Loop

Multi-step research: plan → search → reflect → iterate → synthesize.
Inspired by deer-flow (ByteDance).

Architecture:
  - This script handles I/O: search, fetch, state management, rendering
  - Bobby (the agent) handles ALL reasoning: planning, reflection, synthesis
  - State is saved to JSON after each step so Bobby can resume

Usage (Bobby-driven):
  # Step 1: Init a research session
  python3 deepdive_v2.py init "research question" --output-dir output/

  # Step 2: Bobby reads the state, decides sub-queries, writes them back
  python3 deepdive_v2.py plan <session.json> --queries '["q1","q2","q3"]'

  # Step 3: Execute search + fetch for current queries
  python3 deepdive_v2.py search <session.json> [--fetch-top 3] [--search-count 8]

  # Step 4: Bobby reads results, writes reflection (gaps, follow-ups)
  python3 deepdive_v2.py reflect <session.json> --reflection '{"gaps":["..."],"follow_up_queries":["..."],"confidence":0.6}'

  # Step 5: Execute follow-up searches (repeat search/reflect as needed)
  python3 deepdive_v2.py search <session.json>

  # Step 6: Bobby writes final synthesis
  python3 deepdive_v2.py synthesize <session.json> --synthesis '{"summary":"...","sections":[...],"sources":[...]}'

  # Step 7: Render output
  python3 deepdive_v2.py render <session.json> [--format html|md|both]

State machine: init → planned → searched → reflected → (searched → reflected)* → synthesized → rendered
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text[:60].rstrip('-')


def load_session(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_session(path: str, data: dict):
    data['updated_at'] = datetime.now().isoformat()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Session saved: {path}")


def brave_search(query: str, count: int = 8) -> list[dict]:
    """Search via Brave API."""
    import urllib.request
    import urllib.parse

    try:
        result = subprocess.run(
            ['security', 'find-generic-password', '-s', 'brave-search-api-key', '-w'],
            capture_output=True, text=True, check=True
        )
        api_key = result.stdout.strip()
    except subprocess.CalledProcessError:
        print("ERROR: Brave Search API key not found", file=sys.stderr)
        return []

    url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count={count}"
    req = urllib.request.Request(url, headers={
        'Accept': 'application/json',
        'X-Subscription-Token': api_key
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Search error for '{query}': {e}", file=sys.stderr)
        return []

    results = []
    for item in data.get('web', {}).get('results', [])[:count]:
        results.append({
            'title': item.get('title', ''),
            'url': item.get('url', ''),
            'snippet': item.get('description', ''),
        })
    return results


def fetch_page(url: str, max_chars: int = 12000) -> str:
    """Fetch and extract readable text from a URL."""
    import urllib.request
    import html as html_mod

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"[Fetch error: {e}]"

    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html_mod.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


# ── Commands ──

def cmd_init(args):
    """Initialize a new research session."""
    date = datetime.now().strftime('%Y-%m-%d')
    slug = slugify(args.question)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    session = {
        'version': 2,
        'question': args.question,
        'date': date,
        'slug': slug,
        'state': 'initialized',
        'iteration': 0,
        'max_iterations': args.max_iterations,
        'plan': None,
        'iterations': [],
        'synthesis': None,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
    }

    path = str(output_dir / f"{date}-{slug}-session.json")
    save_session(path, session)
    print(f"Session initialized: {path}")
    print(f"Question: {args.question}")
    print(f"Max iterations: {args.max_iterations}")
    print(f"\nNext: Bobby reads this, decomposes the question, then runs:")
    print(f"  python3 deepdive_v2.py plan {path} --queries '[\"q1\",\"q2\"]'")
    return path


def cmd_plan(args):
    """Record Bobby's query plan."""
    session = load_session(args.session)
    queries = json.loads(args.queries)

    session['plan'] = {
        'queries': queries,
        'reasoning': args.reasoning or '',
        'planned_at': datetime.now().isoformat(),
    }
    session['state'] = 'planned'

    # Set up first iteration with these queries
    session['iterations'].append({
        'iteration': session['iteration'] + 1,
        'queries': queries,
        'search_results': [],
        'reflection': None,
        'searched_at': None,
        'reflected_at': None,
    })
    session['iteration'] = len(session['iterations'])

    save_session(args.session, session)
    print(f"Plan recorded: {len(queries)} queries")
    print(f"\nNext: python3 deepdive_v2.py search {args.session}")


def cmd_search(args):
    """Execute searches for the current iteration's queries."""
    session = load_session(args.session)

    if not session['iterations']:
        print("ERROR: No iteration set up. Run 'plan' first.", file=sys.stderr)
        sys.exit(1)

    current = session['iterations'][-1]
    queries = current['queries']

    print(f"Iteration {current['iteration']}: searching {len(queries)} queries")
    print(f"Settings: fetch_top={args.fetch_top}, search_count={args.search_count}")
    print()

    all_results = []
    seen_urls = set()

    # Collect URLs from all previous iterations to avoid re-fetching
    for prev_iter in session['iterations'][:-1]:
        for sr in prev_iter.get('search_results', []):
            for fc in sr.get('fetched_content', []):
                seen_urls.add(fc.get('url', ''))

    for i, query in enumerate(queries):
        print(f"  [{i+1}/{len(queries)}] Searching: {query}")
        search_results = brave_search(query, count=args.search_count)

        fetched = []
        fetch_count = 0
        for sr in search_results:
            if fetch_count >= args.fetch_top:
                break
            if sr['url'] in seen_urls:
                print(f"    Skipping (already fetched): {sr['url'][:60]}")
                continue
            seen_urls.add(sr['url'])
            print(f"    Fetching [{fetch_count+1}/{args.fetch_top}]: {sr['url'][:80]}")
            content = fetch_page(sr['url'])
            fetched.append({**sr, 'content': content})
            fetch_count += 1

        all_results.append({
            'query': query,
            'search_results': search_results,
            'fetched_content': fetched,
        })

    current['search_results'] = all_results
    current['searched_at'] = datetime.now().isoformat()
    session['state'] = 'searched'

    save_session(args.session, session)

    total_search = sum(len(r['search_results']) for r in all_results)
    total_fetched = sum(len(r['fetched_content']) for r in all_results)
    print(f"\nSearch results: {total_search}, Pages fetched: {total_fetched}")
    print(f"\nNext: Bobby reads the results, reflects, then runs:")
    print(f"  python3 deepdive_v2.py reflect {args.session} --reflection '{{...}}'")


def cmd_reflect(args):
    """Record Bobby's reflection on search results."""
    session = load_session(args.session)
    reflection = json.loads(args.reflection)

    current = session['iterations'][-1]
    current['reflection'] = {
        **reflection,
        'reflected_at': datetime.now().isoformat(),
    }
    session['state'] = 'reflected'

    # If there are follow-up queries and we haven't hit max iterations, set up next iteration
    follow_ups = reflection.get('follow_up_queries', [])
    confidence = reflection.get('confidence', 1.0)

    if follow_ups and confidence < 0.8 and session['iteration'] < session['max_iterations']:
        session['iterations'].append({
            'iteration': session['iteration'] + 1,
            'queries': follow_ups,
            'search_results': [],
            'reflection': None,
            'searched_at': None,
            'reflected_at': None,
        })
        session['iteration'] = len(session['iterations'])
        save_session(args.session, session)
        print(f"Reflection recorded. Confidence: {confidence}")
        print(f"Follow-up iteration {session['iteration']} queued with {len(follow_ups)} queries")
        print(f"\nNext: python3 deepdive_v2.py search {args.session}")
    else:
        save_session(args.session, session)
        reason = "confidence >= 0.8" if confidence >= 0.8 else f"max iterations ({session['max_iterations']}) reached" if not follow_ups else "no follow-ups"
        print(f"Reflection recorded. Confidence: {confidence}. Stopping: {reason}")
        print(f"\nNext: Bobby synthesizes all data, then runs:")
        print(f"  python3 deepdive_v2.py synthesize {args.session} --synthesis '{{...}}'")


def cmd_synthesize(args):
    """Record Bobby's synthesis."""
    session = load_session(args.session)
    synthesis = json.loads(args.synthesis)

    session['synthesis'] = {
        **synthesis,
        'synthesized_at': datetime.now().isoformat(),
    }
    session['state'] = 'synthesized'

    save_session(args.session, session)
    print(f"Synthesis recorded.")
    print(f"\nNext: python3 deepdive_v2.py render {args.session} --format both")


def cmd_render(args):
    """Render the final report from synthesis."""
    session = load_session(args.session)
    s = session.get('synthesis')
    if not s:
        print("ERROR: No synthesis. Run synthesize first.", file=sys.stderr)
        sys.exit(1)

    question = session['question']
    date = session['date']
    slug = session['slug']
    iterations = session['iterations']
    output_dir = Path(args.session).parent

    fmt = args.format

    if fmt in ('html', 'both'):
        path = render_html(session, output_dir)
        print(f"HTML: {path}")

    if fmt in ('md', 'both'):
        path = render_md(session, output_dir)
        print(f"Markdown: {path}")

    session['state'] = 'rendered'
    save_session(args.session, session)


def render_html(session: dict, output_dir: Path) -> str:
    """Render a multi-section HTML report."""
    s = session['synthesis']
    question = session['question']
    date = session['date']
    slug = session['slug']
    iterations = session['iterations']

    # Build sections HTML
    sections_html = ""
    for sec in s.get('sections', []):
        findings_li = "\n".join(f"<li>{f}</li>" for f in sec.get('findings', []))
        evidence_blocks = "\n".join(f'<blockquote>{e}</blockquote>' for e in sec.get('evidence', []))
        sections_html += f"""
        <div class="section">
            <h2>{sec.get('title', '')}</h2>
            <p class="section-summary">{sec.get('summary', '')}</p>
            {'<h3>Key Findings</h3><ul>' + findings_li + '</ul>' if findings_li else ''}
            {'<h3>Evidence</h3>' + evidence_blocks if evidence_blocks else ''}
        </div>"""

    # Sources
    all_sources = s.get('sources', [])
    sources_html = "\n".join(
        f'<li><a href="{src.get("url","#")}" target="_blank">{src.get("title","Source")}</a>'
        f' — <span class="relevance">{src.get("relevance","")}</span></li>'
        for src in all_sources
    )

    # Methodology
    methodology_html = f"""
    <div class="methodology">
        <h2>Research Methodology</h2>
        <p><strong>Iterations:</strong> {len(iterations)} research loops</p>
        <p><strong>Total queries:</strong> {sum(len(it.get('queries',[])) for it in iterations)}</p>
        <p><strong>Sources consulted:</strong> {len(all_sources)}</p>
        <p><strong>Final confidence:</strong> {s.get('confidence', 'N/A')}</p>
        <div class="iteration-trail">
            <h3>Research Trail</h3>
            {''.join(f'<div class="iter"><strong>Iteration {it["iteration"]}:</strong> {", ".join(it.get("queries",[]))}</div>' for it in iterations)}
        </div>
    </div>"""

    # Open questions
    open_q = s.get('open_questions', [])
    open_q_html = "\n".join(f"<li>{q}</li>" for q in open_q) if open_q else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deepdive: {question}</title>
<style>
  :root {{
    --bg: #0d1117; --fg: #c9d1d9; --accent: #58a6ff;
    --card-bg: #161b22; --border: #30363d; --muted: #8b949e;
    --green: #3fb950; --yellow: #d29922; --red: #f85149;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--fg); font: 16px/1.7 'Inter', -apple-system, sans-serif; padding: 2rem; max-width: 860px; margin: 0 auto; }}
  h1 {{ color: var(--accent); font-size: 1.8rem; margin-bottom: 0.3rem; }}
  .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; display: flex; gap: 1.5rem; flex-wrap: wrap; }}
  .meta span {{ display: flex; align-items: center; gap: 0.3rem; }}
  h2 {{ color: var(--fg); font-size: 1.25rem; margin: 2rem 0 0.8rem; border-bottom: 1px solid var(--border); padding-bottom: 0.4rem; }}
  h3 {{ color: var(--muted); font-size: 1rem; margin: 1.2rem 0 0.5rem; }}
  .executive-summary {{ background: var(--card-bg); border-left: 3px solid var(--accent); padding: 1.2rem 1.4rem; border-radius: 6px; margin-bottom: 1.5rem; line-height: 1.8; font-size: 1.05rem; }}
  .section {{ background: var(--card-bg); border-radius: 8px; padding: 1.4rem; margin: 1rem 0; }}
  .section h2 {{ border: none; margin-top: 0; }}
  .section-summary {{ color: var(--muted); margin-bottom: 1rem; }}
  ul {{ padding-left: 1.4rem; }}
  li {{ margin-bottom: 0.5rem; }}
  blockquote {{ background: rgba(88,166,255,0.05); border-left: 3px solid var(--border); padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 4px; font-size: 0.92rem; color: var(--muted); }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .relevance {{ color: var(--muted); font-size: 0.85rem; }}
  .methodology {{ background: var(--card-bg); border-radius: 8px; padding: 1.4rem; margin: 2rem 0; border: 1px solid var(--border); }}
  .iteration-trail {{ margin-top: 1rem; }}
  .iter {{ padding: 0.4rem 0; font-size: 0.9rem; color: var(--muted); border-bottom: 1px solid var(--border); }}
  .iter:last-child {{ border: none; }}
  .confidence {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600; font-size: 0.85rem; }}
  .confidence-high {{ background: rgba(63,185,80,0.15); color: var(--green); }}
  .confidence-medium {{ background: rgba(210,153,34,0.15); color: var(--yellow); }}
  .confidence-low {{ background: rgba(248,81,73,0.15); color: var(--red); }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>🔬 {question}</h1>
<div class="meta">
    <span>📅 {date}</span>
    <span>🔄 {len(iterations)} iterations</span>
    <span>📊 {sum(len(it.get('queries',[])) for it in iterations)} queries</span>
    <span>📚 {len(all_sources)} sources</span>
</div>

<h2>Executive Summary</h2>
<div class="executive-summary">{s.get('summary', '')}</div>

{sections_html}

{'<h2>Open Questions</h2><ul>' + open_q_html + '</ul>' if open_q_html else ''}

<h2>Sources</h2>
<ul>{sources_html}</ul>

{methodology_html}

<div class="footer">Generated by Deepdive v2 — Bobby's SuperAgent Research Loop</div>
</body>
</html>"""

    path = str(output_dir / f"{date}-{slug}.html")
    with open(path, 'w') as f:
        f.write(html)
    return path


def render_md(session: dict, output_dir: Path) -> str:
    """Render Markdown report."""
    s = session['synthesis']
    question = session['question']
    date = session['date']
    slug = session['slug']
    iterations = session['iterations']

    lines = [
        f"# {question}",
        f"",
        f"*Deepdive v2 Report — {date} | {len(iterations)} iterations | "
        f"{sum(len(it.get('queries',[])) for it in iterations)} queries | "
        f"{len(s.get('sources',[]))} sources*",
        "",
        "## Executive Summary",
        "",
        s.get('summary', ''),
        "",
    ]

    for sec in s.get('sections', []):
        lines += [f"## {sec.get('title', '')}", ""]
        if sec.get('summary'):
            lines += [sec['summary'], ""]
        if sec.get('findings'):
            lines += ["### Key Findings", ""]
            for f in sec['findings']:
                lines.append(f"- {f}")
            lines.append("")
        if sec.get('evidence'):
            lines += ["### Evidence", ""]
            for e in sec['evidence']:
                lines += [f"> {e}", ""]

    if s.get('open_questions'):
        lines += ["## Open Questions", ""]
        for q in s['open_questions']:
            lines.append(f"- {q}")
        lines.append("")

    lines += ["## Sources", ""]
    for src in s.get('sources', []):
        lines.append(f"- [{src.get('title','Source')}]({src.get('url','#')}) — {src.get('relevance','')}")

    lines += [
        "",
        "## Research Methodology",
        "",
        f"- **Iterations:** {len(iterations)}",
        f"- **Total queries:** {sum(len(it.get('queries',[])) for it in iterations)}",
        f"- **Confidence:** {s.get('confidence', 'N/A')}",
        "",
        "### Research Trail",
        "",
    ]
    for it in iterations:
        lines.append(f"**Iteration {it['iteration']}:** {', '.join(it.get('queries',[]))}")
        if it.get('reflection') and it['reflection'].get('gaps'):
            lines.append(f"  Gaps identified: {', '.join(it['reflection']['gaps'])}")
        lines.append("")

    lines += ["---", "*Generated by Deepdive v2 — Bobby\'s SuperAgent Research Loop*", ""]

    md = '\n'.join(lines)
    path = str(output_dir / f"{date}-{slug}.md")
    with open(path, 'w') as f:
        f.write(md)
    return path


def cmd_triangulate(args):
    """Analyze source triangulation — how many independent sources confirm each finding."""
    session = load_session(args.session)
    s = session.get('synthesis')
    if not s:
        print("ERROR: No synthesis yet.", file=sys.stderr)
        sys.exit(1)

    # Collect all fetched content across iterations
    all_content = []
    for it in session['iterations']:
        for sr in it.get('search_results', []):
            for fc in sr.get('fetched_content', []):
                all_content.append({
                    'url': fc['url'],
                    'title': fc.get('title', ''),
                    'domain': fc['url'].split('/')[2] if '/' in fc['url'] else fc['url'],
                })

    # Extract unique domains
    domains = list(set(c['domain'] for c in all_content))

    # Build triangulation report
    triangulation = {
        'total_sources': len(all_content),
        'unique_domains': len(domains),
        'domains': domains,
        'sections': [],
    }

    for sec in s.get('sections', []):
        sec_tri = {
            'title': sec.get('title', ''),
            'finding_count': len(sec.get('findings', [])),
            'evidence_count': len(sec.get('evidence', [])),
            'triangulation_score': 'strong' if len(sec.get('evidence', [])) >= 3 else 'moderate' if len(sec.get('evidence', [])) >= 2 else 'weak',
        }
        triangulation['sections'].append(sec_tri)

    # Save to session
    session['triangulation'] = triangulation
    save_session(args.session, session)

    # Print report
    print(f"Source Triangulation Report")
    print(f"{'='*40}")
    print(f"Total sources: {triangulation['total_sources']}")
    print(f"Unique domains: {triangulation['unique_domains']}")
    print()
    for sec in triangulation['sections']:
        icon = '🟢' if sec['triangulation_score'] == 'strong' else '🟡' if sec['triangulation_score'] == 'moderate' else '🔴'
        print(f"  {icon} {sec['title']}: {sec['evidence_count']} evidence pieces ({sec['triangulation_score']})")


def cmd_status(args):
    """Print session status."""
    session = load_session(args.session)
    print(f"Question: {session['question']}")
    print(f"State: {session['state']}")
    print(f"Iteration: {session['iteration']}/{session['max_iterations']}")
    print(f"Total queries so far: {sum(len(it.get('queries',[])) for it in session['iterations'])}")
    for it in session['iterations']:
        status = "✅" if it.get('reflection') else "🔍" if it.get('searched_at') else "⏳"
        print(f"  Iter {it['iteration']}: {status} {len(it.get('queries',[]))} queries")


def main():
    parser = argparse.ArgumentParser(description='Deepdive v2 — SuperAgent Research Loop')
    sub = parser.add_subparsers(dest='command')

    p_init = sub.add_parser('init', help='Initialize research session')
    p_init.add_argument('question', help='Research question')
    p_init.add_argument('--output-dir', default='output/')
    p_init.add_argument('--max-iterations', type=int, default=3)

    p_plan = sub.add_parser('plan', help='Record query plan')
    p_plan.add_argument('session', help='Session JSON file')
    p_plan.add_argument('--queries', required=True, help='JSON array of queries')
    p_plan.add_argument('--reasoning', help='Bobby reasoning for this plan')

    p_search = sub.add_parser('search', help='Execute searches')
    p_search.add_argument('session', help='Session JSON file')
    p_search.add_argument('--fetch-top', type=int, default=3)
    p_search.add_argument('--search-count', type=int, default=8)

    p_reflect = sub.add_parser('reflect', help='Record reflection')
    p_reflect.add_argument('session', help='Session JSON file')
    p_reflect.add_argument('--reflection', required=True, help='JSON reflection object')

    p_synth = sub.add_parser('synthesize', help='Record synthesis')
    p_synth.add_argument('session', help='Session JSON file')
    p_synth.add_argument('--synthesis', required=True, help='JSON synthesis object')

    p_render = sub.add_parser('render', help='Render report')
    p_render.add_argument('session', help='Session JSON file')
    p_render.add_argument('--format', choices=['html', 'md', 'both'], default='both')

    p_tri = sub.add_parser('triangulate', help='Source triangulation analysis')
    p_tri.add_argument('session', help='Session JSON file')

    p_status = sub.add_parser('status', help='Session status')
    p_status.add_argument('session', help='Session JSON file')

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init(args)
    elif args.command == 'plan':
        cmd_plan(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'reflect':
        cmd_reflect(args)
    elif args.command == 'synthesize':
        cmd_synthesize(args)
    elif args.command == 'render':
        cmd_render(args)
    elif args.command == 'triangulate':
        cmd_triangulate(args)
    elif args.command == 'status':
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
