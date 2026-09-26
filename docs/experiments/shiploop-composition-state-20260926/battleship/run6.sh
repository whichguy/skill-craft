#!/bin/sh
D="${EXP_DIR:-$(pwd)}"
cd $D
case "$1" in
 *-web) claude -p --model sonnet --tools WebSearch WebFetch --allowedTools WebSearch WebFetch --output-format stream-json --verbose < prompts6/$1.txt > out6/$1_$2.jsonl 2> out6/$1_$2.err ;;
 *) claude -p --model sonnet --tools "" < prompts6/$1.txt > out6/$1_$2.md 2> out6/$1_$2.err ;;
esac
