#!/bin/bash
# One review: Read tool from an empty directory, no MCP servers; retry if the revised plan is missing or under 150 words.
R3="$(cd "$(dirname "$0")" && pwd)"; f="$R3/out/$1.jsonl"
ok() { python3 - "$f" <<'PY'
import json, sys
r = ""
for l in open(sys.argv[1]):
    try: e = json.loads(l)
    except Exception: continue
    if e.get("type") == "result": r = e.get("result", "")
i = r.find("## Revised plan")
sys.exit(0 if i >= 0 and len(r[i:].split()) >= 150 else 1)
PY
}
for a in 1 2 3; do
  [ -s "$f" ] && ok && break
  ( cd "$R3/empty" && claude -p --model sonnet --tools Read --allowedTools Read --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
      --output-format stream-json --verbose < "$R3/prompts/$1.txt" > "$f" 2>/dev/null )
done
