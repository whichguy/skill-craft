#!/usr/bin/env python3
"""usage: fv_heads.py <clone> <pad_root> <target_len> <outdir> -> whole/printed lengths per packet, writes printed texts (scratch only)"""
import json, os, sys, tempfile
from pathlib import Path
clone = Path(sys.argv[1]).resolve(); base = Path(sys.argv[2]); target = int(sys.argv[3]); outdir = Path(sys.argv[4])
pad = base if target > 83 else None
need = target - 35
if pad is not None:
    while len(str(pad)) < need:
        pad = pad / ("p" * max(1, min(40, need - len(str(pad)) - 1)))
    pad.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(pad); tempfile.tempdir = str(pad)
sys.dont_write_bytecode = True
sys.path.insert(0, str(clone / "skills/shiploop/scripts")); sys.path.insert(0, str(clone / "test/shiploop_e2e"))
import packets
cases = {k: v for k, v in json.loads((clone / "test/shiploop_e2e/step_cases.json").read_text()).items() if not k.startswith("_")}
res = {}
for d in ("inline", "ask-agent"):
    w = packets.offline_packets(cases["node-fix-bug"], delegation=d, printed=False)
    p = packets.offline_packets(cases["node-fix-bug"], delegation=d, printed=True)
    res[d] = {k: (len(w[k]), len(p[k])) for k in w if "improve" not in k}
    (outdir / d).mkdir(parents=True, exist_ok=True)
    for k in p:
        (outdir / d / (k + ".printed.txt")).write_text(p[k])
        (outdir / d / (k + ".whole.txt")).write_text(w[k])
print(json.dumps({"pad": len(str(pad)) if pad else None, "tmp": len(tempfile.gettempdir()), "r": res}))
