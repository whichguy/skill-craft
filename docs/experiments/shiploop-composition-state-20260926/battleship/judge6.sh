#!/bin/sh
D="${EXP_DIR:-$(pwd)}"
cd "$D" && python3 - "$1" <<'PY' | claude -p --model sonnet --tools "" > judge6/$1.json 2> judge6/$1.err
import sys, json, pathlib
stem = sys.argv[1]; rt = stem.split("_")[0]
c = json.load(open("claims6.json"))[rt]
claims = "\n".join(f"{k}: {c[k]}" for k in ("T1", "F1", "T2", "F2"))
print(pathlib.Path("judge6.txt").read_text().replace("{claims}", claims).replace("{plan}", pathlib.Path("out6", stem + ".txt").read_text()))
PY
