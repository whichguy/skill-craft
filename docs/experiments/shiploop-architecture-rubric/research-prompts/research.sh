#!/bin/bash
cd "${EXP_DIR:-$(pwd)}"
claude -p --model sonnet --tools WebSearch WebFetch --allowedTools WebSearch WebFetch --strict-mcp-config --mcp-config '{"mcpServers":{}}' < "prompts/$1.txt" > "$1.md" 2> "$1.err"
