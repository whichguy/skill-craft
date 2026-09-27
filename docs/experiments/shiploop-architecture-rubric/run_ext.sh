#!/bin/bash
# One card-experiment trial. The "card" variant may read CARDS_DIR; the "nocard" control runs
# from an empty directory with no access to the cards (an earlier control that could see them read them).
cd "${EXP_DIR:-$(pwd)}"
case "$1" in
  *_card) dir=(--add-dir "${CARDS_DIR:?}"); cwd=. ;;
  *) dir=(); mkdir -p empty; cwd=empty ;;
esac
( cd "$cwd" && claude -p --model sonnet --tools Read --allowedTools Read "${dir[@]}" --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --output-format stream-json --verbose < "${EXP_DIR:-$(pwd)}/prompts_ext/$1.txt" > "${EXP_DIR:-$(pwd)}/out_ext/$1_$2.jsonl" 2>/dev/null )
