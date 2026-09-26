#!/bin/sh
D="${EXP_DIR:-$(pwd)}"
cd $D && python3 - "$1" <<'PY' | claude -p --model sonnet --tools "" > judge4/$1.json 2> judge4/$1.err
import sys, pathlib
stem = sys.argv[1]; rt, req = stem.split("_")[:2]
RT = {"GAS": "Google Apps Script web app", "SF": "Salesforce DX / Lightning Web Components", "CF": "Cloudflare Workers"}[rt]
RQ = {"solo": "Battleship in the browser against the computer",
      "multi": "multiplayer Battleship, two people sign in, invite, place fleets, take turns",
      "invite": "multiplayer Battleship with email invites, sign-in, and a per-player game history"}[req]
print(pathlib.Path("judge4.txt").read_text().replace("{rt}", RT).replace("{req}", RQ).replace("{plan}", pathlib.Path("out4", stem + ".md").read_text()))
PY
