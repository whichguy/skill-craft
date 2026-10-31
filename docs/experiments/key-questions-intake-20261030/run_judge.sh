#!/usr/bin/env bash
# Judge one pilot X1 case with Opus: CASE.  Writes judge/CASE.out.json (ask envelope) and .err.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
ask="/Users/dadleet/src/grok-build-additions/skills/ask/scripts/ask.sh"
cd "$here/cwd-empty" || exit 3
start=$(date +%s)
"$ask" opus --json "$(cat "$here/judge/$1.md")" >"$here/judge/$1.out.json" 2>"$here/judge/$1.err"
rc=$?
echo "{\"case\": \"$1\", \"rc\": $rc, \"seconds\": $(( $(date +%s) - start ))}" >"$here/judge/$1.meta.json"
exit $rc
