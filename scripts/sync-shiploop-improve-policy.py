#!/usr/bin/env python3
"""Check or materialize ShipLoop's content-pinned copy of Improve's policy.

No host skill lookup, downloads, pin updates or runtime migrations. Review and
edit the pin explicitly before importing a changed upstream policy. This copy
is a packaging step, not a second maintained policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_improve_policy as policy
import shiploop_store as store


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="explicit upstream Improve skill directory")
    parser.add_argument("--write", action="store_true",
                        help="materialize bytes matching the reviewed pin (default: check only)")
    args = parser.parse_args()
    refs = ROOT / "skills/shiploop/references"
    try:
        # Reuse the runtime's bounded pin and body validation. The destination
        # may be missing on first import; validate the source against its pin.
        pin = policy.validate_binding({"improve_policy": json.loads(policy._read(refs / policy.PIN_FILE))})
        assert pin is not None
        source = args.source.resolve() / "references/review-policy.md"
        raw = policy._read(source)
        body = policy._body(raw, pin["sha256"])
        destination = refs / policy.SOURCE_FILE
        if args.write:
            if destination.is_symlink() or (destination.exists() and not destination.is_file()):
                raise policy.ImprovePolicyError("refusing unsafe policy copy destination")
            store.atomic_write_text(destination, body)
        _, copied = policy.load_package(refs)
        if copied.encode("utf-8") != raw:
            raise policy.ImprovePolicyError("bundled policy differs from upstream")
        print(f"Improve policy copy verified: {policy.POLICY_ID} sha256={hashlib.sha256(raw).hexdigest()}")
        return 0
    except (OSError, ValueError, store.StorageError) as exc:
        print(f"Improve policy sync blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
