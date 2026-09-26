#!/bin/sh
D="${EXP_DIR:-$(pwd)}"
cd $D && python3 - "$1" <<'PY' | claude -p --model sonnet --tools "" > judge/$1.json 2> judge/$1.err
import sys, pathlib
stem = sys.argv[1]; rt, req = stem.split("_")[:2]
RT = {"GAS": "Google Apps Script web app", "SF": "Salesforce DX / Lightning Web Components", "CF": "Cloudflare Workers"}[rt]
RQ = {"solo": "Battleship in the browser against the computer", "multi": "multiplayer Battleship, two people sign in, invite, place fleets, take turns"}[req]
print(pathlib.Path("judge.txt").read_text().replace("{rt}", RT).replace("{req}", RQ).replace("{plan}", pathlib.Path("plain", stem + ".md").read_text()))
PY
