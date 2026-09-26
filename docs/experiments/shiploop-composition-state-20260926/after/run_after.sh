#!/bin/bash
cd "${EXP_DIR:-$(pwd)}"
case "$1" in
  R0_*) n=4;; *) n=3;;
esac
k=$2
case "$1" in
  R6b_*) claude -p --model sonnet --tools WebSearch WebFetch --allowedTools WebSearch WebFetch < after/prompts/$1.txt > after/out/$1_$k.md 2>/dev/null ;;
  R7_*) cd fx7/gas && claude -p --model sonnet --tools Read Grep Glob --allowedTools Read Grep Glob --add-dir ${SHIPLOOP_WT:?}/skills/shiploop --output-format stream-json --verbose < "${EXP_DIR:-$(pwd)}"/after/prompts/$1.txt > "${EXP_DIR:-$(pwd)}"/after/out/$1_$k.jsonl 2>/dev/null ;;
  *) claude -p --model sonnet --tools "" < after/prompts/$1.txt > after/out/$1_$k.md 2>/dev/null ;;
esac
