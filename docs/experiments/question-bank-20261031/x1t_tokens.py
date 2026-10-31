#!/usr/bin/env python3
"""What X1-T's saved Terra intakes cost: tokens, characters and seconds per arm, from the envelopes' own usage records.

Reads ../question-record-20261031/intake/<subject>/*.json (arms A, B and C; 16 runs each) and prints one table per subject.
Needs no model call.  Usage: python3 x1t_tokens.py
"""
import glob
import re
import statistics

from common import QR, envelope


def main() -> None:
    for subject in ("terra", "terra-xhigh"):
        rows = {}
        for path in sorted(glob.glob(str(QR / "intake" / subject / "*.json"))):
            if path.endswith(".meta.json") or not re.search(r"-[ABC]-s\d+\.json$", path):
                continue
            arm = re.search(r"-([ABC])-s\d+\.json$", path).group(1)
            data = envelope(QR / "intake" / subject / path.rsplit("/", 1)[1])
            meta = envelope(QR / "intake" / subject / path.rsplit("/", 1)[1].replace(".json", ".meta.json"))
            usage = data.get("usage") or {}
            rows.setdefault(arm, []).append({
                "out": usage.get("output_tokens", 0), "reasoning": usage.get("reasoning_output_tokens", 0),
                "uncached": usage.get("input_tokens", 0) - usage.get("cached_input_tokens", 0),
                "chars": len(data.get("text") or ""), "seconds": meta.get("seconds", 0)})
        print(f"\nsubject {subject} (means per run)")
        print("arm   n  out_tokens  reasoning  uncached_input  chars  seconds")
        for arm in "ABC":
            runs = rows[arm]
            mean = {k: statistics.mean(r[k] for r in runs) for k in runs[0]}
            print(f"{arm}    {len(runs):2d}  {mean['out']:10.0f}  {mean['reasoning']:9.0f}  {mean['uncached']:14.0f}  "
                  f"{mean['chars']:5.0f}  {mean['seconds']:7.1f}")


if __name__ == "__main__":
    main()
