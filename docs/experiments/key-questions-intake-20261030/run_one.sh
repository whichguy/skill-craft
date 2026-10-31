#!/usr/bin/env bash
# Run one pilot X1 subject call: CASE ARM SAMPLE [MODEL].  Writes outputs/CASE-ARM-sSAMPLE.json (the ask envelope)
# and .err (runner progress).  Runs from an empty directory so no repository instructions load.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
case_id="$1"; arm="$2"; sample="$3"; model="${4:-sonnet}"
ask="/Users/dadleet/src/grok-build-additions/skills/ask/scripts/ask.sh"
out="$here/outputs/${case_id}-${arm}-s${sample}.json"
cd "$here/cwd-empty" || exit 3
start=$(date +%s)
"$ask" "$model" --json "$(cat "$here/prompts/${case_id}-${arm}.md")" >"$out" 2>"${out%.json}.err"
rc=$?
echo "{\"case\": \"$case_id\", \"arm\": \"$arm\", \"sample\": $sample, \"model\": \"$model\", \"rc\": $rc, \"seconds\": $(( $(date +%s) - start ))}" >"${out%.json}.meta.json"
exit $rc
