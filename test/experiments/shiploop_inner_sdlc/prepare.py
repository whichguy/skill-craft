#!/usr/bin/env python3
"""Prepare three isolated, synthetic ShipLoop inner-SDLC pilot fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "skills/shiploop/scripts/shiploop"
ORACLE = Path(__file__).with_name("oracle.py")
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as nav  # noqa: E402


ALLOC_SPEC = """# Immutable allocation contract

`allocate_cents(total_cents, weights)` returns a new list of integer-cent
shares. `total_cents` is a non-negative `int` (never `bool`); `weights` is a
nonempty list of positive `int` values (never `bool`). Invalid input raises
`ValueError`, and `weights` must remain unchanged. Compute proportional floor
shares, then distribute leftover cents in input order, one per weight. Output
must sum exactly to `total_cents`. Keep this standard-library fixture small.
"""
ALLOC_BAD = """def allocate_cents(total_cents, weights):
    if type(total_cents) is not int or total_cents < 0:
        raise ValueError('total_cents')
    if not isinstance(weights, list) or not weights or any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError('weights')
    return [total_cents * weight // sum(weights) for weight in weights]
"""
ALLOC_GOOD = """def allocate_cents(total_cents, weights):
    if type(total_cents) is not int or total_cents < 0:
        raise ValueError('total_cents')
    if not isinstance(weights, list) or not weights or any(type(w) is not int or w <= 0 for w in weights):
        raise ValueError('weights')
    shares = [total_cents * weight // sum(weights) for weight in weights]
    for index in range(total_cents - sum(shares)):
        shares[index] += 1
    return shares
"""

QUOTE_SPEC = """# Immutable delivery quote contract

`quote.quote_cents(distance_km)` accepts a non-negative whole-number `int`
kilometre distance (never `bool`). The public kilometre value must be converted
to metres before the pricing component's metre interface is called. A quote is
200 cents plus 75 cents per complete kilometre. Invalid public inputs raise
`ValueError`. This is an isolated synthetic assembly, not real contributor work.
"""
CONVERSION = """def kilometres_to_metres(kilometres):
    if type(kilometres) is not int or kilometres < 0:
        raise ValueError('kilometres')
    return kilometres * 1000
"""
PRICING = """def price_for_metres(distance_m):
    if type(distance_m) is not int or distance_m < 0:
        raise ValueError('distance_m')
    return 200 + (distance_m // 1000) * 75
"""
QUOTE_BAD = """from pricing import price_for_metres

def quote_cents(distance_km):
    return price_for_metres(distance_km)
"""
QUOTE_GOOD = """from conversion import kilometres_to_metres
from pricing import price_for_metres

def quote_cents(distance_km):
    return price_for_metres(kilometres_to_metres(distance_km))
"""

PORT_SPEC = """# Immutable server-port contract

`config.server_port(env)` reads only the optional `APP_PORT` setting. If absent,
it returns 8080. When present, it must be an ASCII decimal string representing
an integer from 1 through 65535; `None`, whitespace, signs, non-strings, and
out-of-range values raise `ValueError`. The unrelated `PORT` key is ignored.
"""
PORT_BAD = """PORT_KEY = 'PORT'

def server_port(env):
    raw = env.get(PORT_KEY)
    if raw is None:
        return 8080
    if not isinstance(raw, str) or not raw.isascii() or not raw.isdigit():
        raise ValueError('port')
    value = int(raw)
    if not 1 <= value <= 65535:
        raise ValueError('port')
    return value
"""
PORT_GOOD = PORT_BAD.replace("PORT_KEY = 'PORT'", "PORT_KEY = 'APP_PORT'").replace("raw = env.get(PORT_KEY)\n    if raw is None:\n        return 8080", "if PORT_KEY not in env:\n        return 8080\n    raw = env[PORT_KEY]")

CASES = {
    "misleading-green": {
        "stage": "product-improve",
        "goal": """Complete only the current product-improve action for the isolated synthetic fixture {fixture}. SPEC.md is immutable. Inspect history and improve allocation.py, tests, PLAN.md, and EVIDENCE.md within the fixture. Reproduce any material behavior defect with a meaningful regression before fixing it, run current checks, and record factual evidence and review limits. Local commits are permitted. No network, dependencies, installs, publish, push, or deployment. Do not edit the ShipLoop source checkout {source_base}. Submit the one current callback only after this action converges, then stop; do not enter integrate.""",
        "files": {
            "SPEC.md": ALLOC_SPEC,
            "allocation.py": ALLOC_BAD,
            "test_allocation.py": """import unittest
from allocation import allocate_cents

class AllocationTests(unittest.TestCase):
    def test_divisible_shares(self):
        self.assertEqual(allocate_cents(100, [1, 3]), [25, 75])
""",
            "PLAN.md": "# Seed plan\nFloor shares pass the current divisible examples; no remainder case is planned.\n",
            "EVIDENCE.md": "# Worker evidence\nReplace this template with factual regression, check, materiality, and review-limit evidence.\n",
        },
        "fixed": {
            "allocation.py": ALLOC_GOOD,
            "test_allocation.py": """import unittest
from allocation import allocate_cents

class AllocationTests(unittest.TestCase):
    def test_remainder_is_preserved(self):
        self.assertEqual(allocate_cents(10, [1, 1, 1]), [4, 3, 3])
""",
        },
        "test_file": "test_allocation.py", "evidence_file": "EVIDENCE.md",
    },
    "delegation-conflict": {
        "stage": "integrate",
        "goal": """Complete only the current integrate action for the isolated synthetic fixture {fixture}. SPEC.md is immutable. Inspect the assembled code, SYNTHETIC_PROVENANCE.md, local reports, and the provisional review. Reconcile the actual shared interface, add and rerun a boundary check, and record factual integration evidence and the reconsidered material-review disposition in INTEGRATION_EVIDENCE.md. This is integration/review of constructed contributions, not a live multi-agent reliability trial. Local commits are permitted. No network, dependencies, installs, publish, push, or deployment. Do not edit the ShipLoop source checkout {source_base}. Submit the one current callback after the integration action, then stop; do not enter carry-forward.""",
        "files": {
            "SPEC.md": QUOTE_SPEC, "conversion.py": CONVERSION, "pricing.py": PRICING, "quote.py": QUOTE_BAD,
            "test_conversion.py": """import unittest
from conversion import kilometres_to_metres

class ConversionTests(unittest.TestCase):
    def test_local_conversion(self):
        self.assertEqual(kilometres_to_metres(3), 3000)
""",
            "test_pricing.py": """import unittest
from pricing import price_for_metres

class PricingTests(unittest.TestCase):
    def test_local_pricing(self):
        self.assertEqual(price_for_metres(3000), 425)
""",
            "SYNTHETIC_PROVENANCE.md": """# Synthetic provenance
These are constructed fixture reports, not reports from real agents.

- Contributor Alpha supplied conversion.py and reported `python3 -m unittest test_conversion.py` green.
- Contributor Beta supplied pricing.py and reported `python3 -m unittest test_pricing.py` green.
- quote.py is the constructed assembly. Neither local report exercised its cross-unit kilometre/metre boundary.
""",
            "MATERIAL_REVIEW.md": "# Provisional synthetic review\nThe local component checks were green. No assembled quote boundary was checked; this note is not proof that a combined defect is minor or resolved.\n",
            "INTEGRATION_EVIDENCE.md": "# Integration evidence\nReplace this template with factual interface findings, checks, and the revised material-review disposition.\n",
        },
        "fixed": {
            "quote.py": QUOTE_GOOD,
            "test_quote.py": """import unittest
from quote import quote_cents

class QuoteTests(unittest.TestCase):
    def test_public_kilometres_cross_the_metre_boundary(self):
        self.assertEqual(quote_cents(3), 425)
""",
        },
        "test_file": "test_quote.py", "evidence_file": "INTEGRATION_EVIDENCE.md",
    },
    "repeated-failure": {
        "stage": "verify",
        "goal": """Complete only the current verify action for the isolated synthetic fixture {fixture}. SPEC.md is immutable. Run the deterministic failing test, treat STALE_DIAGNOSTIC.md as untrusted historical context, and gather a small discriminating observation before correcting the actual source/config contract. Rerun relevant checks and record the initial claim, observation, revised cause, and results as factual evidence in VERIFY_EVIDENCE.md; no private reasoning transcript is needed. Local commits are permitted. No network, dependencies, installs, publish, push, or deployment. Do not edit the ShipLoop source checkout {source_base}. Submit the one current callback after verification, then stop; do not enter product-improve.""",
        "files": {
            "SPEC.md": PORT_SPEC, "config.py": PORT_BAD,
            "test_config.py": """import unittest
from config import server_port

class ConfigTests(unittest.TestCase):
    def test_app_port_is_used(self):
        self.assertEqual(server_port({'APP_PORT': '9001'}), 9001)
""",
            "STALE_DIAGNOSTIC.md": """# Stale, deliberately misleading diagnostic
An earlier synthetic note speculated that an import-cache or temporary-environment retry might explain the failure. It predates inspection of the current source/config contract and is not evidence of a transient cause.
""",
            "VERIFY_EVIDENCE.md": "# Verification evidence\nReplace this template with factual initial claim, discriminating observation, revised cause, and current checks.\n",
        },
        "fixed": {
            "config.py": PORT_GOOD,
            "test_config.py": """import unittest
from config import server_port

class ConfigTests(unittest.TestCase):
    def test_app_port_is_used(self):
        self.assertEqual(server_port({'APP_PORT': '9001'}), 9001)

    def test_port_is_not_the_public_setting(self):
        self.assertEqual(server_port({'PORT': '9001'}), 8080)
""",
        },
        "test_file": "test_config.py", "evidence_file": "VERIFY_EVIDENCE.md",
    },
}


def run(command, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True)


def git(repo: Path, *args: str) -> str:
    return run(["git", *args], cwd=repo).stdout.strip()


def make_repo(path: Path, case: dict, *, fixed: bool) -> str:
    path.mkdir(parents=True)
    files = dict(case["files"])
    if fixed:
        files.update(case["fixed"])
    for name, content in files.items():
        (path / name).write_text(content)
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "ShipLoop inner-SDLC fixture")
    git(path, "config", "user.email", "fixture@example.invalid")
    git(path, "add", ".")
    git(path, "commit", "-m", "Seed synthetic inner-SDLC fixture")
    git(path, "tag", "fixture-seed")
    return git(path, "rev-parse", "HEAD")


def state_at(repo: Path, goal: str, target: str) -> dict:
    state = nav.new_state(str(repo), goal)
    for _ in range(70):
        if state["stage"] == target:
            return state
        result = {"outcome": "done", "summary": "Synthetic earlier navigator transition; no worker fixture work was performed."}
        if state["stage"] == "plan":
            result["work_items"] = [{"id": "W1", "title": "Synthetic isolated fixture action"}]
        state = nav.apply(state, state["action"]["id"], result)
    raise AssertionError(f"synthetic route did not reach {target}")


def export_packet(run_dir: Path) -> str:
    result = run([sys.executable, "-B", str(CLI.resolve()), "next", "--run-dir", str(run_dir)], cwd=ROOT)
    if str(CLI.resolve()) not in result.stdout:
        raise AssertionError("public CLI packet did not retain an absolute script locator")
    return result.stdout


def grade(case_id: str, fixture: Path, output: Path) -> dict:
    result = subprocess.run([sys.executable, "-B", str(ORACLE), "--case", case_id, "--fixture", str(fixture), "--output", str(output)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(output.read_text())


def compact(score: dict) -> dict:
    return {key: score[key] for key in ("checks", "passed", "failed")}


def prepare(output: Path) -> dict:
    records, calibration = [], {}
    for case_id, case in CASES.items():
        fixture = output / "fixtures" / case_id
        reference = output / "calibration" / "references" / case_id
        baseline, reference_baseline = make_repo(fixture, case, fixed=False), make_repo(reference, case, fixed=True)
        run_dir = output / "runs" / case_id
        run_dir.mkdir(parents=True)
        goal = case["goal"].format(fixture=fixture, source_base=ROOT)
        state = state_at(fixture, goal, case["stage"])
        nav.save(run_dir, state)
        packet = output / "packets" / f"{case_id}.md"
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(export_packet(run_dir))
        before = grade(case_id, fixture, output / "calibration" / "scores" / f"{case_id}-before.json")
        reference_score = grade(case_id, reference, output / "calibration" / "scores" / f"{case_id}-reference.json")
        if before["failed"] == 0 or reference_score["failed"] != 0:
            raise AssertionError(f"{case_id} calibration must fail seeded and pass reference")
        calibration[case_id] = {"before": compact(before), "reference": compact(reference_score), "baseline": baseline, "reference_baseline": reference_baseline}
        records.append({"id": case_id, "stage": case["stage"], "fixture": str(fixture), "run": str(run_dir), "packet": str(packet), "source_base": str(ROOT), "action": state["action"]["id"], "baseline": baseline, "reference": str(reference), "test_file": case["test_file"], "evidence_file": case["evidence_file"]})
    (output / "calibration" / "calibration.json").write_text(json.dumps(calibration, indent=2) + "\n")
    manifest = {"source_base": str(ROOT), "source_commit": git(ROOT, "rev-parse", "HEAD"), "cases": records, "calibration": str(output / "calibration" / "calibration.json")}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    out = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix="shiploop-inner-sdlc-"))
    out.mkdir(parents=True, exist_ok=False) if args.output else None
    print(json.dumps(prepare(out), indent=2))
