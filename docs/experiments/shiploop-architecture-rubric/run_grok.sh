#!/bin/bash
# One subject trial on Grok grok-4.7 at medium effort, isolated from plugins, skills and MCP servers,
# read-only (plan mode) from an empty directory. Reruns a stub (<150 words) up to 3 times.
# usage: run_grok.sh PROMPT_FILE OUT_JSON EMPTY_DIR
G="${GROK_HOME_DIR:?set GROK_HOME_DIR to an isolated home with .grok/auth.json linked}"
words() { python3 -c "import json,sys
try: print(len(json.load(open(sys.argv[1])).get('text','').split()))
except Exception: print(0)" "$2"; }
for a in 1 2 3; do
  [ -s "$2" ] && [ "$(words "$1" "$2")" -ge 150 ] && break
  env -i PATH="$PATH" HOME="$G" GROK_CONFIG_DIR="$G/.grok" XDG_CONFIG_HOME="$G/.config" XDG_DATA_HOME="$G/.local/share" \
    XDG_CACHE_HOME="$G/.cache" XDG_STATE_HOME="$G/.local/state" GROK_CLAUDE_SKILLS_ENABLED=false \
    GROK_CURSOR_SKILLS_ENABLED=false NO_COLOR=1 \
    grok --cwd "$3" --prompt-file "$1" --verbatim --model grok-4.7 --reasoning-effort medium --output-format json \
      --no-auto-update --disable-web-search --permission-mode plan --max-turns 6 > "$2" 2>/dev/null
done
