#!/usr/bin/env python3
"""QB4 (README.md): what an attended intake sends to a person, on QB2's request.

    python3 qb4.py build   write qb4/prompts/BP1-<arm>.md from QB2's prompts of arms Bp and Qp
    python3 qb4.py jobs    write jobs-qb4.tsv (4 outputs per arm, the workspace as the working directory)
    python3 qb4.py report  list every row routed to a person, per output, and count them

The only change to QB2's prompts is the frame: a person can answer one short batch at the end of the stage, and the rule says to
route an item to the person only when the repository and the skills cannot settle it and two readings lead to different work.
No judge is used: the person-routed rows are read directly.
"""
import json
import sys

from common import HERE, SUBJECT, envelope, envelope_text, state_block
from qb2 import CASE_ID, QB2, WORKSPACE

QB4 = HERE / "qb4"
ARMS = ("Bp", "Qp")
SAMPLES = (1, 2, 3, 4)
OLD_FRAME = "The run is unattended: no person will answer questions during it."
NEW_FRAME = "A person is available to answer one short batch of questions at the end of this stage."
OLD_RULE = ("- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report\n"
            "  blocked only when nothing can proceed without a person.")
NEW_RULE = ("- Attended: route an item to `person` only when the repository and the skills cannot settle it and two readings\n"
            "  lead to different work; take the best default for everything else and record it as an assumption.")


def cmd_build() -> None:
    (QB4 / "prompts").mkdir(parents=True, exist_ok=True)
    for arm in ARMS:
        base = (QB2 / "prompts" / f"{CASE_ID}-{arm}.md").read_text()
        assert base.count(OLD_FRAME) == 1 and base.count(OLD_RULE) == 1, arm
        text = base.replace(OLD_FRAME, NEW_FRAME, 1).replace(OLD_RULE, NEW_RULE, 1)
        assert text.replace(NEW_FRAME, OLD_FRAME, 1).replace(NEW_RULE, OLD_RULE, 1) == base
        (QB4 / "prompts" / f"{CASE_ID}-{arm}.md").write_text(text)
    print(f"wrote {len(ARMS)} prompts")


def cmd_jobs() -> None:
    rows = []
    for arm in ARMS:
        for sample in SAMPLES:
            prompt = (QB4 / "prompts" / f"{CASE_ID}-{arm}.md").relative_to(HERE).as_posix()
            out = (QB4 / "intake" / f"{CASE_ID}-{arm}-s{sample}.json").relative_to(HERE).as_posix()
            rows.append(f"{SUBJECT}\t{prompt}\t{out}\t{WORKSPACE}")
    (HERE / "jobs-qb4.tsv").write_text("\n".join(rows) + "\n")
    print(f"wrote {len(rows)} QB4 subject jobs")


def cmd_report() -> None:
    counts = {arm: [] for arm in ARMS}
    for arm in ARMS:
        for sample in SAMPLES:
            path = QB4 / "intake" / f"{CASE_ID}-{arm}-s{sample}.json"
            result = state_block(envelope_text(path))
            usage = envelope(path).get("usage") or {}
            rows = (result or {}).get("questions") or (result or {}).get("answers") or []
            asked = [r for r in rows if str(r.get("route") or r.get("basis") or "").strip().lower() == "person"]
            counts[arm].append(len(asked))
            print(f"\n{arm} s{sample}: {len(asked)} of {len(rows)} rows to a person; output tokens {usage.get('output_tokens')}")
            for row in asked:
                text = row.get("question") or row.get("answer") or ""
                print(f"  - {row.get('id')} {row.get('category', '')}: {' '.join(str(text).split())[:190]}")
    print("\nperson-routed rows per output:", json.dumps(counts))


if __name__ == "__main__":
    {"build": cmd_build, "jobs": cmd_jobs, "report": cmd_report}[sys.argv[1]]()
