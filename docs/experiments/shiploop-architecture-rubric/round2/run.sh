#!/bin/bash
# One trial: Read tool from an empty directory, no MCP servers, stream-json output. Reruns stubs (<150 words) up to 3 times.
R2="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$R2/empty" "$R2/out"
f="$R2/out/$1_$2.jsonl"
words() { python3 -c "import json,sys
r=''
for l in open(sys.argv[1]):
    try: e=json.loads(l)
    except Exception: continue
    if e.get('type')=='result': r=e.get('result','')
print(len(r.split()))" "$f" 2>/dev/null || echo 0; }
for a in 1 2 3; do
  [ -s "$f" ] && [ "$(words)" -ge 150 ] && break
  ( cd "$R2/empty" && claude -p --model sonnet --tools Read --allowedTools Read --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
      --output-format stream-json --verbose < "$R2/prompts/$1.txt" > "$f" 2>/dev/null )
done
