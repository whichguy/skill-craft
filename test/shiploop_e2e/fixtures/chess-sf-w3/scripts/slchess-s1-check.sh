#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
grep -q '"sourceApiVersion": "68.0"' sfdx-project.json
grep -q '\.sf/' .gitignore
grep -q '\.sfdx/' .gitignore
test ! -e force-app/main/default/objects
test ! -e force-app/main/default/permissionsets
test ! -e force-app/main/default/staticresources
test ! -e force-app/main/default/triggers
test ! -e force-app/main/default/profiles
test ! -e force-app/main/default/labels
test ! -e force-app/main/default/flows
if find force-app -name '*.cls' ! -name 'SLChess*.cls' | grep -q .; then
  exit 1
fi
sf project deploy start --target-org de
set +e
log=$(sf apex run --target-org de --file scripts/slchess-s1-check.apex)
code=$?
set -e
printf '%s\n' "$log"
if [ "$code" -ne 0 ]; then
  exit "$code"
fi
printf '%s\n' "$log" | grep -q S1_OK
