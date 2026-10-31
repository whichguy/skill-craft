#!/usr/bin/env python3
"""Write jobs-intake.tsv: X1-T, X1's prompts on each subject in common.SUBJECTS, samples 1-4."""
from common import CASES, HERE, SAMPLES, SUBJECTS, X1, intake_out

rows = []
for slug, subject in SUBJECTS.items():
    samples = SAMPLES
    for case in CASES:
        for arm in ("A", "B", "C"):
            prompt = (X1 / "prompts" / f"{case['id']}-{arm}.md").relative_to(HERE.parent).as_posix()
            for sample in samples:
                out = intake_out(slug, case["id"], arm, sample).relative_to(HERE)
                rows.append(f"{subject}\t../{prompt}\t{out.as_posix()}")
(HERE / "jobs-intake.tsv").write_text("\n".join(rows) + "\n")
print(f"wrote {len(rows)} intake jobs")
