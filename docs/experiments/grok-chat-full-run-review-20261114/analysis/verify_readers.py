"""Reproduce the 33-versus-35 verify-row disagreement between the harness's two readers of ShipLoop's verify records.

    python3 -I verify_readers.py RUN_DIR/.shiploop-runs/<id>/run

``text reader`` is an exact copy of ``_RUN_ROWS`` in test/shiploop_e2e/metrics.py: it finds the ``"runs"`` array by
counting ``[`` and ``]`` characters without knowing about JSON strings, so a ``]`` inside a command's captured output ends
the array early and the rows after it are not counted.  ``json rows`` is what test/shiploop_e2e/fidelity.py reads: the
``runs`` list of the record's ``shiploop-state`` block.
"""
import glob
import json
import os
import re
import sys


def run_rows(text):
    start = text.find('"runs"')
    if start < 0:
        return []
    depth, index = 0, text.find("[", start)
    if index < 0:
        return []
    begin = index
    while index < len(text):
        char = text[index]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                break
        index += 1
    return re.findall(r'"command"\s*:', text[begin:index])


run_dir = sys.argv[1]
total_text = total_json = 0
for path in sorted(glob.glob(run_dir + "/tests/*-verify*.md")):
    text = open(path, errors="replace").read()
    block = re.search(r"```shiploop-state\n(.*?)\n```", text, re.S)
    record = json.loads(block.group(1))
    rows_json, rows_text = len(record["runs"]), len(run_rows(text))
    total_text += rows_text
    total_json += rows_json
    note = "  <-- the text reader stops early" if rows_text != rows_json else ""
    print("%-46s json rows %2d  text reader %2d%s" % (os.path.basename(path)[:44], rows_json, rows_text, note))
print("TOTAL json %d  text reader %d" % (total_json, total_text))
