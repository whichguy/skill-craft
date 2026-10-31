#!/usr/bin/env python3
"""Write jobs.tsv, QB1's subject calls (README.md): arms Qb, Sb, Bq and Bs on samples 1-8, and X1's A and B on samples 5-8.

A and B samples 1-4 are X1-T's Terra xhigh outputs, reused where they are (common.out_path).
"""
from common import ANCHORS, ARMS, CASES, HERE, SAMPLES, SUBJECT, out_path, prompt_path

rows = []
for case in CASES:
    for arm in ARMS:
        for sample in SAMPLES:
            if arm in ANCHORS and sample <= 4:
                continue
            prompt = prompt_path(case["id"], arm).relative_to(HERE.parent).as_posix()
            out = out_path(case["id"], arm, sample).relative_to(HERE).as_posix()
            rows.append(f"{SUBJECT}\t../{prompt}\t{out}")
(HERE / "jobs.tsv").write_text("\n".join(rows) + "\n")
print(f"wrote {len(rows)} subject jobs")
