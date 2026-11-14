"""V7 registration and final source controls without the archived apparatus."""
from pathlib import Path
import tempfile
import unittest

from v7 import registration as p


def registration(purpose, count):
    return {"schema": p.REGISTRATION, "observation_schema": p.OBSERVATION, "purpose": purpose,
            "comparative": purpose == "comparison", "policies": p.POLICIES, "roles": p.ROLES,
            "sample_count": count, "arms": {"A": {}, **({"B": {}} if purpose == "comparison" else {})},
            "trials_per_arm_case": 1}


def sample(case, arm, index):
    return {"case": case, "arm": arm, "trial": 1, "sample_id": f"R{index}", "masked_id": f"M{index}"}


class RegistrationTests(unittest.TestCase):
    def test_smoke_is_one_noncomparative_secret_exposure_slot(self):
        reg = registration("smoke", 1)
        rows = [sample("secret-exposure", "A", 1)]
        p.validate_protocol(reg)
        self.assertEqual(p.validate_schedule(reg, {"purpose": "smoke", "samples": rows}), rows)
        with self.assertRaises(ValueError):
            p.validate_protocol(dict(reg, comparative=True))
        with self.assertRaises(ValueError):
            p.validate_schedule(reg, {"purpose": "smoke", "samples": [dict(rows[0], case="cosmetic")]})

    def test_v2_protocol_and_implicit_runtime_policy_are_rejected(self):
        valid = registration("smoke", 1)
        for change in ({"schema": "shiploop-security-pilot/v2"},
                       {"observation_schema": "shiploop-security-observation/v2"},
                       {"roles": {"subject": {"model": "gpt-6.1-sol", "effort": "high"}}},
                       {"policies": {k: v for k, v in p.POLICIES.items() if k != "git"}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.validate_protocol(dict(valid, **change))

    def test_comparison_balance_and_mask_inventory_are_registered(self):
        reg = registration("comparison", 4)
        rows = [sample(case, arm, index) for index, (case, arm) in
                enumerate([(c, a) for c in ("cosmetic", "integrated-secure") for a in ("A", "B")], 1)]
        self.assertEqual(p.validate_schedule(reg, {"purpose": "comparison", "samples": rows}), rows)
        for change in ({"arm": "A"}, {"masked_id": "M2"}, {"sample_id": "M2"},
                       {"trial": 2}, {"case": "../private"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                p.validate_schedule(reg, {"purpose": "comparison", "samples": [*rows[:-1], dict(rows[-1], **change)]})

    def test_fresh_and_resumed_argv_require_unambiguous_explicit_controls(self):
        binary = "/tools/codex"
        cwd = Path.cwd()
        controls = [binary, "exec", "--json", "-m", "gpt-6.1-sol", "-C", str(cwd),
                    "-c", "model_reasoning_effort=medium",
                    "-c", 'agents.default_subagent_model="gpt-6.1-sol"',
                    "-c", "agents.default_subagent_reasoning_effort=medium"]
        p.validate_launch([*controls, "prompt"], binary, cwd=cwd)
        p.validate_launch([*controls, "resume", "thread", "prompt"], binary, cwd=cwd, resumed="thread")
        for extra in (["--model", "gpt-6-asta"], ["-c", "model_reasoning_effort=high"],
                      ["resume", "unregistered-thread"]):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                p.validate_launch([*controls, *extra, "prompt"], binary, cwd=cwd)
        with self.assertRaises(ValueError):
            p.validate_launch([*controls, "resume", "wrong-thread", "prompt"], binary,
                              cwd=cwd, resumed="thread")

    def test_assembled_inventory_verifies_bytes_modes_and_new_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            for sub in p.SOURCE_DIRS:
                (root / sub).mkdir()
            for rel in p.SOURCE_FILES:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"pinned")
            rows = p.sources(root)
            receipt = {"schema": p.ASSEMBLED, "sources": rows, "source_sha256": p.digest(p.canonical(rows))}
            (root / "assembled.json").write_bytes(p.canonical(receipt))
            expected = p.verify_assembled(root)
            path = root / p.SOURCE_FILES[0]
            previous = path.stat().st_mode
            path.chmod(0o400)
            with self.assertRaises(ValueError):
                p.verify_assembled(root, expected)
            path.chmod(previous)
            path.write_bytes(b"new source")
            with self.assertRaises(ValueError):
                p.verify_assembled(root, expected)
            path.write_bytes(b"pinned")
            (root / "analysis/new.py").write_text("unregistered")
            with self.assertRaises(ValueError):
                p.verify_assembled(root, expected)
