#!/bin/bash
# Deepdive — Quick run helper
# Usage: ./deepdive_run.sh "research question"
# 
# This is a convenience wrapper. The actual workflow is:
# 1. Bobby decomposes the question into sub-queries
# 2. deepdive.py gathers data (web_search + web_fetch via Bobby's tools)
# 3. Bobby synthesizes the raw data
# 4. deepdive.py renders HTML from the synthesis JSON
# 5. Bobby publishes to MC Feed
#
# Since steps 1-3 require Bobby's tools and reasoning,
# this script just documents the workflow.

echo "Deepdive workflow:"
echo "1. Bobby decomposes question into sub-queries"
echo "2. Bobby uses web_search + web_fetch tools to gather data"  
echo "3. Bobby writes synthesis to output/YYYY-MM-DD-slug.json"
echo "4. python3 deepdive.py --render output/<file>.json"
echo "5. python3 ~/scripts/feed_add.py --type deep_dive --title 'Deepdive: <topic>' --file /tmp/report.md"
echo ""
echo "Question: $1"
