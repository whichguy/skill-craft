"""Obligation check for the hand-off pointers: render the hand-off block with the base and the changed checkout on the long-
knowledge fixture (measure_handoff_block.py's) and prove that every line the change removed is a same-packet duplicate.

    check_handoff_dedupe.py <base checkout> <changed checkout>

A removed line is accepted when it is (a) diff scaffolding or a `+` line of a file the packet quotes whole, whose text is in that
quote, (b) a line of a followed entry that is in a quoted file, or (c) (efficiency unit U13) a line of a followed entry that is a
`+` line of the whole-file diff the changed block prints below it.  Anything else is printed as UNEXPLAINED and the exit code is 1.
Taken from docs/experiments/shiploop-eff-packets-20261016/check_handoff_dedupe.py (the packets branch's check); (c) is the addition.

The measure script is that directory's measure_handoff_block.py (run from the repository root, or pass --measure PATH).
"""
import difflib, importlib.util, os, re, subprocess, sys, tempfile
from pathlib import Path
here = Path(__file__).resolve().parents[2] / "shiploop-eff-packets-20261016"

def block(root, stage):
    """The stage's quoted-files-and-hand-offs lines from a checkout (its own modules), on the shared fixture."""
    code = (here / "measure_handoff_block.py").read_text().replace("sys.argv[1]", repr(str(root)))
    code = code.replace('print(f"{stage:20s} {n:7d}")', "pass").replace('print(f"{\'TOTAL\':20s} {sum(sizes.values()):7d}")', "pass")
    code += "\nimport json; print('@@BLOCKS@@' + json.dumps(blocks))\n"
    code = code.replace("sizes[stage] = len(text)", "sizes[stage] = len(text); blocks[stage] = text").replace("sizes = {}", "sizes = {}; blocks = {}")
    out = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, env={**os.environ, "PYTHONPATH": ""})
    import json
    return json.loads(out.stdout.split("@@BLOCKS@@", 1)[1]) if "@@BLOCKS@@" in out.stdout else sys.exit(out.stderr)

base, changed = block(sys.argv[1], None), block(sys.argv[2], None)
bad = 0
for stage in base:
    old, new = base[stage].splitlines(), changed[stage].splitlines()
    quoted = set(line[4:] for line in new if line.startswith("  | "))      # the quote block's file lines (and followed entries kept)
    quoted |= {text[1:] for text in quoted if text.startswith("+")}        # (c): a `+` line of a printed diff, without its +
    removed = added = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        for line in old[i1:i2] if tag in ("replace", "delete") else ():
            removed += 1
            payload = line[4:] if line.startswith("  | ") else ""
            payload = payload[1:] if payload.startswith("+") else payload
            scaffold = re.match(r"  \| (diff --git|new file mode|index |--- |\+\+\+ |@@ |$)", line) or line.startswith(("Spec and architecture", "follows (", "- R-", "- AD-"))
            if not (payload in quoted or scaffold):
                bad += 1
                print("UNEXPLAINED", stage, repr(line[:120]))
        added += (j2 - j1) if tag in ("replace", "insert") else 0
    print(f"{stage:20s} removed {removed:5d} lines, added {added:3d}")
print("every removed line is a duplicate of a quoted file" if not bad else f"{bad} UNEXPLAINED lines")
sys.exit(1 if bad else 0)
