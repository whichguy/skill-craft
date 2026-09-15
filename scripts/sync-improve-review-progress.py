#!/usr/bin/env python3
"""Bundle/check Improve's stateless receipt evaluator for relocatable ShipLoop."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    copies = (
        ("scripts/review_progress.py", "scripts/_improve_review_progress.py"),
        ("references/review-progress.md", "references/improve-review-progress.md"),
    )
    for source_name, target_name in copies:
        source = root / "skills/improve" / source_name
        target = root / "skills/shiploop" / target_name
        if source.is_symlink() or not source.is_file():
            raise SystemExit(f"Unsafe or missing Improve source: {source}")
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise SystemExit(f"Unsafe generated destination: {target}")
        content = source.read_bytes()
        if args.write:
            target.write_bytes(content)
        if not target.is_file() or target.read_bytes() != content:
            raise SystemExit("Improve receipt bundle differs; review sources, then run with --write")
    print("Improve review-progress bundle verified")


if __name__ == "__main__":
    main()
