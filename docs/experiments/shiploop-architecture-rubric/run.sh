#!/bin/bash
# Run one trial with no MCP servers (headless trials must not start browsers or other servers).
cd "${EXP_DIR:-$(pwd)}"
claude -p --model sonnet --tools "" --strict-mcp-config --mcp-config '{"mcpServers":{}}' < "prompts/$1.txt" > "out/$1_$2.md" 2>/dev/null
