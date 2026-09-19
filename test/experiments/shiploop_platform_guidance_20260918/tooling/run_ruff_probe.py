#!/usr/bin/env python3
"""Probe installed Ruff fix semantics in disposable copies, not product code."""

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def command(argv):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=30)
    return {"argv": argv, "returncode": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr}


def observe(path):
    probe = """import importlib.util, json, sys
spec = importlib.util.spec_from_file_location('fixture', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    empty = {'value': module.first([])}
except Exception as error:
    empty = {'exception': type(error).__name__}
print(json.dumps({'ordinary': module.first([7, 9]), 'empty': empty}))
"""
    receipt = command([sys.executable, "-c", probe, str(path)])
    if receipt["returncode"] != 0:
        raise RuntimeError(receipt)
    return json.loads(receipt["stdout"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; choose a new receipt path")
    ruff = shutil.which("ruff")
    if not ruff:
        parser.error("installed Ruff unavailable; no installation attempted")
    version = command([ruff, "--version"])
    if version["returncode"]:
        raise RuntimeError(version)
    seed = "def first(values):\n    return list(values)[0]\n"
    compatible = (
        "def first(values):\n"
        "    try:\n"
        "        return next(iter(values))\n"
        "    except StopIteration as error:\n"
        "        raise IndexError('no item') from error\n"
    )
    expected = {"ordinary": 7, "empty": {"exception": "IndexError"}}
    checks = []
    commands = []
    with tempfile.TemporaryDirectory(prefix="shiploop-ruff-probe-") as temp:
        root = Path(temp)
        ordinary = root / "safe.py"
        unsafe = root / "unsafe.py"
        repaired = root / "compatible.py"
        ordinary.write_text(seed)
        unsafe.write_text(seed)
        repaired.write_text(compatible)
        before = observe(ordinary)
        checks.append({"id": "R0", "claim": "frozen original contract",
                       "expected": expected, "observed": before, "pass": before == expected})
        base = [ruff, "check", "--isolated", "--no-cache", "--select", "RUF015",
                "--output-format", "json"]
        safe_run = command(base + ["--fix", str(ordinary)])
        commands.append(safe_run)
        safe_after = observe(ordinary)
        checks.append({"id": "R1", "claim": "default fix leaves this unsafe fix unapplied",
                       "observed": safe_after, "source_unchanged": ordinary.read_text() == seed,
                       "pass": safe_run["returncode"] == 1 and ordinary.read_text() == seed
                       and safe_after == expected})
        unsafe_run = command(base + ["--fix", "--unsafe-fixes", str(unsafe)])
        commands.append(unsafe_run)
        unsafe_after = observe(unsafe)
        checks.append({"id": "R2", "claim": "explicit unsafe fix changes empty-input contract",
                       "observed": unsafe_after, "mutant_rejected": unsafe_after != expected,
                       "pass": unsafe_run["returncode"] == 0 and unsafe_after["ordinary"] == 7
                       and unsafe_after["empty"] == {"exception": "StopIteration"}})
        repair_run = command(base + [str(repaired)])
        commands.append(repair_run)
        repair_after = observe(repaired)
        checks.append({"id": "R3", "claim": "explicit adaptation preserves tested contract",
                       "observed": repair_after,
                       "pass": repair_run["returncode"] == 0 and repair_after == expected})
        iterator_observations = {}
        for name, path in [("original", ordinary), ("unsafe", unsafe), ("adapted", repaired)]:
            iterator_run = command([sys.executable, "-c",
                "import json, runpy, sys; f=runpy.run_path(sys.argv[1])['first']; "
                "values=iter([7,9]); first=f(values); "
                "print(json.dumps({'first':first,'remaining':list(values)}))", str(path)])
            commands.append(iterator_run)
            if iterator_run["returncode"]:
                raise RuntimeError(iterator_run)
            iterator_observations[name] = json.loads(iterator_run["stdout"])
        checks.append({"id": "R5", "claim": "matching list outputs and errors does not prove iterator-consumption compatibility",
                       "observed": iterator_observations,
                       "pass": iterator_observations["original"] == {"first": 7, "remaining": []}
                       and iterator_observations["unsafe"] == {"first": 7, "remaining": [9]}
                       and iterator_observations["adapted"] == {"first": 7, "remaining": [9]}})
        auth = root / "authorization.py"
        auth.write_text("def read_record(records, actor, record_id):\n    return records[record_id]\n")
        lint = command([ruff, "check", "--isolated", "--no-cache", "--select", "E,F",
                        "--output-format", "json", str(auth)])
        commands.append(lint)
        auth_probe = command([sys.executable, "-c",
            "import runpy, sys; f=runpy.run_path(sys.argv[1])['read_record']; "
            "print(f({'b': {'owner':'B'}}, 'A', 'b')['owner'])", str(auth)])
        commands.append(auth_probe)
        checks.append({"id": "R4", "claim": "clean selected lint rules do not prove authorization",
                       "lint_exit": lint["returncode"], "observed_owner": auth_probe["stdout"].strip(),
                       "pass": lint["returncode"] == 0 and auth_probe["returncode"] == 0
                       and auth_probe["stdout"].strip() == "B"})
    result = {
        "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python": sys.version, "ruff": version["stdout"].strip(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "seed_sha256": hashlib.sha256(seed.encode()).hexdigest(),
        "expected_contract": expected, "checks": checks, "commands": commands,
        "passed": sum(check["pass"] for check in checks), "total": len(checks),
        "limits": ["One installed version and selected rules, not all Ruff checks.",
                   "R3 establishes list-value/error equivalence only; R5 rejects general iterator equivalence.",
                   "No performance measurement, hosted runtime, or model guidance efficacy trial.",
                   "A rejected deliberately wrong implementation is a successful probe, not production success."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as receipt:
        json.dump(result, receipt, indent=2)
        receipt.write("\n")
    print(json.dumps({"passed": result["passed"], "total": result["total"],
                      "ruff": result["ruff"], "receipt": str(args.output)}))
    return 0 if all(check["pass"] for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
