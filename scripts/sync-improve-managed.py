#!/usr/bin/env python3
"""Materialize/check ShipLoop's package-local copy of the managed Improve controller."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "skills/improve/scripts/managed_controller.py"
    destination = root / "skills/shiploop/scripts/_improve_managed.py"
    pin_path = root / "skills/shiploop/references/improve-managed-controller-pin.json"
    contract_source = root / "skills/improve/references/managed-consumer.md"
    contract_destination = root / "skills/shiploop/references/improve-managed-consumer.md"
    contract = contract_source.read_bytes()
    raw = source.read_bytes()
    pin = {"version": 1, "controller": "improve-managed-controller/v1",
           "sha256": hashlib.sha256(raw).hexdigest(), "source": "skills/improve/scripts/managed_controller.py",
           "contract_source": "skills/improve/references/managed-consumer.md",
           "contract_path": "references/improve-managed-consumer.md",
           "contract_sha256": hashlib.sha256(contract).hexdigest()}
    pin_text = json.dumps(pin, sort_keys=True, indent=2) + "\n"
    if args.write:
        for path in (destination, pin_path, contract_destination):
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise SystemExit(f"Unsafe generated destination: {path}")
        destination.write_bytes(raw)
        contract_destination.write_bytes(contract)
        pin_path.write_text(pin_text)
    if not destination.is_file() or destination.is_symlink() or destination.read_bytes() != raw:
        raise SystemExit("Managed Improve controller copy differs; run this script with --write after reviewing the source change")
    if not pin_path.is_file() or pin_path.is_symlink() or pin_path.read_text() != pin_text:
        raise SystemExit("Managed Improve controller pin differs")
    if not contract_destination.is_file() or contract_destination.is_symlink() or contract_destination.read_bytes() != contract:
        raise SystemExit("Managed Improve consumer contract copy differs")
    print(f"Managed Improve controller copy verified: {pin['sha256']}")


if __name__ == "__main__":
    main()
