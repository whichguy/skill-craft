#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
cls=force-app/main/default/classes/SLChessController.cls
grep -q '@AuraEnabled' "$cls"
grep -q 'public static List<String> legalMoves' "$cls"
grep -q 'public static String applyMove' "$cls"
grep -q 'public static String status' "$cls"
grep -q 'AuraHandledException' "$cls"
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
log=$(sf apex run --target-org de --file scripts/slchess-s2-check.apex)
code=$?
set -e
printf '%s\n' "$log"
if [ "$code" -ne 0 ]; then
  exit "$code"
fi
printf '%s\n' "$log" | grep -q S2_OK
set +e
tlog=$(sf apex run test --target-org de --class-names SLChessControllerTest --synchronous --result-format tap --code-coverage)
tcode=$?
set -e
printf '%s\n' "$tlog"
if [ "$tcode" -ne 0 ]; then
  exit "$tcode"
fi
printf '%s\n' "$tlog" | grep -q 'SLChessControllerTest.blankFen'
sf apex run test --target-org de --class-names SLChessEngineTest --synchronous --result-format tap --code-coverage
