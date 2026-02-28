#!/usr/bin/env python3
"""
Deepdive — Research-to-Report Data Gathering Tool

Usage:
    python3 deepdive.py "research question" [--max-queries N] [--fetch-top N] [--output-dir DIR]

Gathers web search results and page content for a research question.
Bobby (the agent) handles decomposition and synthesis — this script handles I/O.

Modes:
    gather  — Search + fetch raw data, save to JSON (default)
    render  — Take a synthesis JSON and produce HTML report
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path(__file__).parent / "output"


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text[:60].rstrip('-')


def brave_search(query: str, count: int = 5) -> list[dict]:
    """Search via Brave API using the API key from keychain."""
    import urllib.request
    import urllib.parse

    # Get API key from keychain
    try:
        result = subprocess.run(
            ['security', 'find-generic-password', '-s', 'brave-search-api-key', '-w'],
            capture_output=True, text=True, check=True
        )
        api_key = result.stdout.strip()
    except subprocess.CalledProcessError:
        print("ERROR: Brave Search API key not found in keychain (brave-search-api-key)", file=sys.stderr)
        sys.exit(1)

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


def fetch_page(url: str, max_chars: int = 8000) -> str:
    """Fetch and extract readable text from a URL."""
    import urllib.request

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return f"[Fetch error: {e}]"

    # Basic HTML to text extraction
    import html as html_mod
    # Remove scripts, styles
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode entities
    text = html_mod.unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_chars]


def gather(question: str, sub_queries: list[str], fetch_top: int = 2, search_count: int = 5) -> dict:
    """Execute search + fetch for all sub-queries."""
    date = datetime.now().strftime('%Y-%m-%d')
    results = []

    for i, query in enumerate(sub_queries):
        print(f"  [{i+1}/{len(sub_queries)}] Searching: {query}")
        search_results = brave_search(query, count=search_count)

        fetched = []
        for j, sr in enumerate(search_results[:fetch_top]):
            print(f"    Fetching [{j+1}/{fetch_top}]: {sr['url'][:80]}")
            content = fetch_page(sr['url'])
            fetched.append({**sr, 'content': content})

        results.append({
            'query': query,
            'search_results': search_results,
            'fetched_content': fetched,
        })

    return {
        'question': question,
        'date': date,
        'sub_queries': sub_queries,
        'raw_results': results,
        'synthesis': None,  # Bobby fills this in
    }


def render_markdown(synthesis_path: str, output_path: str = None) -> str:
    """Render a synthesis JSON into a clean Markdown report."""
    with open(synthesis_path) as f:
        data = json.load(f)

    s = data.get('synthesis', {})
    if not s:
        print("ERROR: No synthesis in JSON. Run Bobby's synthesis first.", file=sys.stderr)
        sys.exit(1)

    question = data.get('question', 'Research Report')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))

    lines = [f'# {question}', f'', f'*Deepdive Report — {date}*', '']
    lines += ['## Executive Summary', '', s.get('summary', ''), '']
    lines += ['## Key Findings', '']
    for f in s.get('findings', []):
        lines.append(f'- {f}')
    lines += ['', '## Supporting Evidence', '']
    for e in s.get('evidence', []):
        lines.append(f'> {e}')
        lines.append('')
    lines += ['## Open Questions', '']
    for q in s.get('open_questions', []):
        lines.append(f'- {q}')
    lines += ['', '## Sources', '']
    for src in s.get('sources', []):
        lines.append(f'- [{src.get("title", "Source")}]({src.get("url", "#")})')
    lines += ['', '---', '*Generated by Deepdive — Bobby\'s Research Agent*', '']

    md = '\n'.join(lines)

    if not output_path:
        slug = slugify(question)
        output_path = str(Path(synthesis_path).parent / f"{date}-{slug}.md")

    with open(output_path, 'w') as f:
        f.write(md)

    print(f"Markdown report saved to: {output_path}")
    return output_path


def render_html(synthesis_path: str, output_path: str = None) -> str:
    """Render a synthesis JSON into a clean HTML report."""
    with open(synthesis_path) as f:
        data = json.load(f)

    s = data.get('synthesis', {})
    if not s:
        print("ERROR: No synthesis in JSON. Run Bobby's synthesis first.", file=sys.stderr)
        sys.exit(1)

    question = data.get('question', 'Research Report')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))

    findings_html = '\n'.join(f'<li>{f}</li>' for f in s.get('findings', []))
    evidence_html = '\n'.join(f'<blockquote>{e}</blockquote>' for e in s.get('evidence', []))
    open_q_html = '\n'.join(f'<li>{q}</li>' for q in s.get('open_questions', []))
    sources_html = '\n'.join(
        f'<li><a href="{src.get("url", "#")}" target="_blank">{src.get("title", "Source")}</a></li>'
        for src in s.get('sources', [])
    )

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
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--fg); font: 16px/1.7 'Inter', -apple-system, sans-serif; padding: 2rem; max-width: 800px; margin: 0 auto; }}
  h1 {{ color: var(--accent); font-size: 1.6rem; margin-bottom: 0.3rem; }}
  .date {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; }}
  h2 {{ color: var(--fg); font-size: 1.15rem; margin: 1.8rem 0 0.8rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3rem; }}
  .summary {{ background: var(--card-bg); border-left: 3px solid var(--accent); padding: 1rem 1.2rem; border-radius: 6px; margin-bottom: 1.5rem; line-height: 1.8; }}
  ul {{ padding-left: 1.4rem; }}
  li {{ margin-bottom: 0.5rem; }}
  blockquote {{ background: var(--card-bg); border-left: 3px solid var(--border); padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 4px; font-size: 0.92rem; color: var(--muted); }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>🔬 {question}</h1>
<div class="date">Deepdive Report — {date}</div>

<h2>Executive Summary</h2>
<div class="summary">{s.get('summary', '')}</div>

<h2>Key Findings</h2>
<ul>{findings_html}</ul>

<h2>Supporting Evidence</h2>
{evidence_html}

<h2>Open Questions</h2>
<ul>{open_q_html}</ul>

<h2>Sources</h2>
<ul>{sources_html}</ul>

<div class="footer">Generated by Deepdive — Bobby's Research Agent</div>
</body>
</html>"""

    if not output_path:
        slug = slugify(question)
        output_path = str(Path(synthesis_path).parent / f"{date}-{slug}.html")

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"HTML report saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='Deepdive — Research Data Gathering')
    parser.add_argument('question', nargs='?', help='Research question')
    parser.add_argument('--sub-queries', type=str, help='JSON array of sub-queries (Bobby provides these)')
    parser.add_argument('--fetch-top', type=int, default=2, help='Number of pages to fetch per query')
    parser.add_argument('--search-count', type=int, default=5, help='Number of search results per query')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument('--render', type=str, help='Render HTML from synthesis JSON file')
    parser.add_argument('--render-md', type=str, help='Render Markdown from synthesis JSON file')

    args = parser.parse_args()

    if args.render:
        render_html(args.render)
        return

    if args.render_md:
        render_markdown(args.render_md)
        return

    if not args.question:
        parser.print_help()
        sys.exit(1)

    if not args.sub_queries:
        print("ERROR: --sub-queries required. Bobby decomposes the question and passes sub-queries.", file=sys.stderr)
        print('Example: --sub-queries \'["query 1", "query 2", "query 3"]\'', file=sys.stderr)
        sys.exit(1)

    sub_queries = json.loads(args.sub_queries)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Deepdive: {args.question}")
    print(f"Sub-queries: {len(sub_queries)}")
    print()

    data = gather(args.question, sub_queries, args.fetch_top, args.search_count)

    slug = slugify(args.question)
    date = datetime.now().strftime('%Y-%m-%d')
    json_path = output_dir / f"{date}-{slug}.json"

    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nRaw data saved to: {json_path}")
    print(f"Total search results: {sum(len(r['search_results']) for r in data['raw_results'])}")
    print(f"Pages fetched: {sum(len(r['fetched_content']) for r in data['raw_results'])}")
    print("\nNext: Bobby synthesizes this data and updates the JSON with 'synthesis' field.")
    print(f"Then: python3 deepdive.py --render {json_path}")

    return str(json_path)


if __name__ == '__main__':
    main()
