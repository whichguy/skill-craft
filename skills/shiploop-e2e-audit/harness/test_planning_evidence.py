"""Hermetic Plan provenance controls using real Git objects and raw trace records."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import capture
import planning_evidence as evidence


RUN = "nav-c0049ce5a42b44e6b1915fa0efbbd757"
PLAN = "nav-0bd196ef730546baa976ef2124edbb20"
IMPROVE = "nav-7d122d95629f40e790f5cd82c69b20d2"
PREPARE = "nav-f3c249e512064243857341970a710795"
OTHER_PLAN = "nav-8aab403e3d6d46fea98cd7d26bb80ac3"
OTHER_IMPROVE = "nav-fafbbde7be9f4d0ab5f30ccf9e77c13"
INITIAL = "The sole reaper records the exit before taking the lifecycle lock."
FINAL = "The final controller returns a separate cancellation receipt."
OTHER = "A separate Plan review elected an append-only scheduler."
WRONG_ACTION = "Another Plan moves every waiter to a shared queue."
UNLINKED = "A scratch file proposes checking each process group twice."
COMMAND = "printf command-only-evidence"
KEY = "dictionary-key-only-evidence"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_record(title: str, data: dict) -> str:
    return f"# {title}\n\n```shiploop-state\n{json.dumps(data, indent=2, sort_keys=True)}\n```\n"


class PlanningFixture(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="planning-evidence-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.top = self.root / "worktree"
        self.repo = self.top / "app"
        self.docs = self.repo / "docs"
        self.docs.mkdir(parents=True)
        self.run_dir = self.root / "run"
        self.bind = self.run_dir / "improve" / f"{PLAN}-bind.md"
        self.bind.parent.mkdir(parents=True)
        (self.run_dir / "packets" / "sent").mkdir(parents=True)
        self.out = self.root / "derived"
        self.arch = self.docs / "architecture.md"
        self.skill = str(self.root / "installed" / "improve" / "SKILL.md")
        self.locator = str(self.arch) + "#lifecycle"
        self.alias = "docs/architecture.md:2"
        self.git("init", "-q")
        self.arch.write_text("# Lifecycle\nThe sole reaper records the exit before\ntaking the lifecycle lock.\n",
                             encoding="utf-8")
        (self.docs / "other.md").write_text(OTHER, encoding="utf-8")
        (self.docs / "unlinked.md").write_text(UNLINKED, encoding="utf-8")
        self.git("add", "-A")
        self.tree = self.git("write-tree").decode().strip()
        self.seed = {
            "outcome": "done", "headline": "Producer Plan", "summary": "The Plan separates shutdown from admission.",
            "evidence_refs": [self.locator, self.alias, "docs/other.md"],
            "assumptions": [{"id": "A1", "assumption": "Gate termination on the sole reaper.",
                             "disposition": "probed", "check": COMMAND, "evidence": [self.locator]}],
            "concerns": {KEY: "A concern value."},
            "work_items": [{"id": "W1", "title": "Prove shutdown ordering", "context": "Stop at accepted planning."}],
        }
        self.expected = evidence.ExpectedPlan(
            run_id=RUN, plan_action=PLAN, improve_action=IMPROVE, producer_revision=8,
            seed_sha256=evidence.seed_digest(self.seed), repo=str(self.repo), repo_prefix="app",
        )
        self.state = {
            "run_id": RUN, "status": "active", "stage": "prepare", "revision": 9, "repo": str(self.repo),
            "history": [{"stage": "plan", "action": PLAN, "outcome": "done", "workitem": None}],
            "improve_results": {PLAN: {
                "version": 1, "action_id": PLAN, "improve_action": IMPROVE, "stage": "plan",
                "binding_id": f"{RUN}/{PLAN}", "workspace": str(self.repo), "runtime_phase": "complete",
                "skill": {"skill_card": self.skill}, "seed_result": self.seed,
            }},
            "accepted": {PLAN: {**self.seed, "summary": FINAL}},
        }
        self.write_producer()

    def git(self, *args: str) -> bytes:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.check_output(["git", "-C", str(self.top), *args], env=env, stderr=subprocess.PIPE)

    def write_state(self) -> None:
        (self.run_dir / "state.md").write_text(state_record("ShipLoop navigator state", self.state), encoding="utf-8")

    @property
    def bound_result(self) -> Path:
        return self.bind.with_name(f"{PLAN}-bind-result.json")

    def write_bind(self, tree: str) -> None:
        bind = {"prefix": "app", "result": self.expected.seed_sha256, "toplevel": str(self.top), "tree": tree}
        self.bind.write_text(state_record("ShipLoop Improve bind snapshot", bind), encoding="utf-8")
        self.bound_result.write_text(json.dumps(self.seed, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")

    def write_producer(self, *, bound: bool = True) -> None:
        self.expected = replace(self.expected, seed_sha256=evidence.seed_digest(self.seed))
        self.write_state()
        self.write_bind(self.tree)
        packet = "ShipLoop navigator | improve | revision 8 | the plan result\n"
        if bound:
            packet += (
                "1. Run the improve skill on the plan result with this argument, at every Improve stage and "
                "not from memory of an earlier one:\n"
                f"       ShipLoop Improve: {self.repo}/.shiploop-improve/plan-24edbb20/handoff.md\n"
                f'   (through the host\'s skill call for skill "improve": the Skill tool, or /improve, '
                f"where the host has one; otherwise open {self.skill} and follow it with the argument)\n"
                f"2. When the improve skill has completed, run: shiploop complete --run-dir={self.run_dir} "
                f"--action={IMPROVE}\n"
            )
        else:
            packet += "Next command (bind the Improve skill's SKILL.md, absolute path)\n"
        packet += f"Keepalive marker: SHIPLOOP-RUN run={RUN} rev=8 dir={self.run_dir}\n"
        packet_sha = sha256(packet.encode())[:16]
        packet_file = f"packets/sent/{packet_sha}.md"
        (self.run_dir / packet_file).write_text(packet, encoding="utf-8")

        # The runtime takes mtime/ctime inside complete, writes the packet, then
        # appends the command row. Reproduce that relation without a model or clock sleep.
        at = round(max(self.bind.stat().st_ctime, self.bound_result.stat().st_ctime), 3) + 0.010
        self.rows = [
            {"kind": "command", "verb": "next", "exit": 0, "rev": [7, 7], "stage": ["plan", "plan"],
             "cursor": [PLAN, PLAN], "ts": at - 2, "ms": 75},
            {"kind": "packet", "action": IMPROVE, "stage": "improve", "reviewed": "plan",
             "rev": 8, "chars": len(packet), "printed": len(packet), "whole": True, "sha": packet_sha,
             "file": packet_file, "ts": at},
            {"kind": "command", "verb": "complete", "action": PLAN, "exit": 0, "ms": 1400, "rev": [7, 8],
             "stage": ["plan", "improve"], "cursor": [PLAN, IMPROVE], "ts": at + 0.009},
            {"kind": "command", "verb": "improve-pass", "action": IMPROVE, "exit": 0, "ms": 23, "rev": [8, 8],
             "stage": ["improve", "improve"], "cursor": [IMPROVE, IMPROVE], "ts": at + 60},
            {"kind": "packet", "action": PREPARE, "stage": "prepare", "rev": 9, "ts": at + 65.999},
            {"kind": "command", "verb": "complete", "action": IMPROVE, "exit": 0, "ms": 279, "rev": [8, 9],
             "stage": ["improve", "prepare"], "cursor": [IMPROVE, PREPARE], "ts": at + 66,
             "accepted": [{"stage": "plan", "action": PLAN, "outcome": "done", "item": None}]},
        ]
        self.write_trace()

    def write_trace(self) -> None:
        (self.run_dir / "trace.jsonl").write_text("".join(
            json.dumps({"v": 1, "at": "2026-11-08T22:50:39Z", "status": "active", **row}) + "\n"
            for row in self.rows
        ), encoding="utf-8")

    def collect(self, expected: evidence.ExpectedPlan | None = None) -> dict:
        return evidence.collect_initial_artifacts(self.run_dir, self.out, expected=expected or self.expected)

    def captured(self) -> tuple[dict, dict]:
        result = self.collect()
        self.assertEqual(result["status"], "captured", result)
        return result, json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))

    def verify(self, receipt: dict, *, quote: str = INITIAL, locator: str | None = None, **kwargs) -> dict:
        options = {"expected": self.expected, "manifest_sha256": receipt["manifest_sha256"], **kwargs}
        return evidence.verify_linked_quote(self.out, quote=quote, locator=locator or self.locator, **options)

    def replace_manifest(self, manifest: dict) -> dict:
        path = self.out / evidence.MANIFEST_NAME
        data = json.dumps(manifest, ensure_ascii=False).encode()
        path.write_bytes(data)
        return {"manifest_sha256": sha256(data)}

    def field(self, field: str, quote: str, **kwargs) -> dict:
        options = {"run_id": RUN, "plan_action": PLAN, "improve_action": IMPROVE,
                   "seed_sha256": self.expected.seed_sha256, **kwargs}
        return evidence.verify_initial_field(self.run_dir, field=field, quote=quote, **options)


class ProvenanceTest(PlanningFixture):
    def test_producer_architecture_survives_final_changes_and_offline_archive(self) -> None:
        self.arch.write_text(FINAL, encoding="utf-8")
        self.git("add", "-A")
        final_tree = self.git("write-tree").decode().strip()
        self.assertNotEqual(final_tree, self.tree)
        result, manifest = self.captured()
        entry = manifest["entries"][self.locator]
        self.assertEqual(manifest["receipt_kind"], "derived-after-producer")
        self.assertEqual(manifest["capture_basis"], "automatic-producer-bind-git-snapshot")
        self.assertEqual(manifest["trace_lines"], {"producer_packet": 2, "producer": 3, "acceptance": 6})
        self.assertEqual(manifest["tree"], self.tree)
        self.assertEqual(entry["blob"], self.git("rev-parse", f"{self.tree}:app/docs/architecture.md").decode().strip())
        self.assertEqual(self.verify(result)["status"], "matched")
        self.assertEqual(self.verify(result, quote=FINAL)["status"], "not-found")
        self.assertEqual(self.verify(result, locator=self.alias)["status"], "matched")

        (self.out / "unrelated.txt").write_text("outside the declared portable set", encoding="utf-8")
        archive = self.root / "archive"
        archived = capture.archive_planning_evidence(self.out, archive, manifest_sha256=result["manifest_sha256"])
        self.assertEqual(archived["status"], "archived", archived)
        self.assertEqual(archived["manifest_sha256"], result["manifest_sha256"])
        self.assertFalse((archive / "unrelated.txt").exists())
        self.assertEqual((archive / entry["sidecar"]).read_bytes(), (self.out / entry["sidecar"]).read_bytes())
        shutil.rmtree(self.top)
        shutil.rmtree(self.run_dir)
        shutil.rmtree(self.out)
        observed = evidence.verify_linked_quote(archive, expected=self.expected,
                                                manifest_sha256=result["manifest_sha256"],
                                                locator=self.locator, quote=INITIAL)
        self.assertEqual(observed["status"], "matched", observed)

    def test_wrong_source_action_field_key_command_and_final(self) -> None:
        self.arch.write_text(WRONG_ACTION, encoding="utf-8")
        self.git("add", "-A")
        other_tree = self.git("write-tree").decode().strip()
        other_record = {**self.state["improve_results"][PLAN], "action_id": OTHER_PLAN, "improve_action": OTHER_IMPROVE,
                        "binding_id": f"{RUN}/{OTHER_PLAN}", "seed_result": {**self.seed, "summary": WRONG_ACTION}}
        self.state["improve_results"][OTHER_PLAN] = other_record
        (self.bind.parent / f"{OTHER_PLAN}-bind.md").write_text(
            state_record("ShipLoop Improve bind snapshot", {"prefix": "app", "result": self.expected.seed_sha256,
                                                             "toplevel": str(self.top), "tree": other_tree}),
            encoding="utf-8",
        )
        self.write_state()
        result, _ = self.captured()
        for quote in (OTHER, WRONG_ACTION, UNLINKED, KEY, COMMAND, FINAL):
            with self.subTest(quote=quote):
                self.assertEqual(self.verify(result, quote=quote)["status"], "not-found")
        self.assertEqual(self.verify(result, locator="docs/other.md")["status"], "not-found")
        self.assertEqual(self.verify(result, locator="docs/unlinked.md", quote=UNLINKED)["status"], "unsupported")
        self.assertEqual(self.verify(result, locator=str(self.arch))["status"], "unsupported")
        self.assertEqual(self.field("summary", self.seed["summary"])["status"], "matched")
        self.assertEqual(self.field("summary", FINAL)["status"], "not-found")
        self.assertEqual(self.field("summary", COMMAND)["status"], "not-found")
        self.assertEqual(self.field("summary", KEY)["status"], "not-found")
        self.assertEqual(self.field("command", COMMAND)["status"], "unsupported")
        self.assertEqual(self.field("concerns", KEY)["status"], "unsupported")

    def test_named_field_requires_no_snapshot_or_trace(self) -> None:
        self.bind.unlink()
        self.bound_result.unlink()
        (self.run_dir / "trace.jsonl").unlink()
        self.assertEqual(self.field("headline", "Producer Plan")["status"], "matched")
        self.assertEqual(self.field("summary", "The Plan separates shutdown   from admission.")["status"], "matched")
        self.assertEqual(self.collect()["status"], "unavailable")

    def test_restart_replaces_architecture_with_unchanged_seed(self) -> None:
        self.arch.write_text(FINAL, encoding="utf-8")
        self.git("add", "-A")
        replacement = self.git("write-tree").decode().strip()
        self.assertNotEqual(replacement, self.tree)
        original_seed = self.bound_result.read_bytes()
        self.write_bind(replacement)
        self.assertEqual(original_seed, self.bound_result.read_bytes())
        self.assertIn(self.expected.seed_sha256, self.bind.read_text(encoding="utf-8"))
        # improve-start can replace both bind files without a revision increment.
        restart = {**self.rows[3], "verb": "improve-start", "ts": self.rows[3]["ts"] + 1}
        self.rows.insert(4, restart)
        self.write_trace()
        result = self.collect()
        self.assertEqual(result["status"], "unavailable", result)
        self.assertIn("restart", result["reason"])
        self.assertFalse(self.out.exists())

    def test_missing_restart_row_still_fails_replacement_clock(self) -> None:
        stamp = self.bind.stat()
        time.sleep(0.03)
        self.write_bind(self.tree)
        # A preserved mtime alone cannot corroborate provenance after a copy or rewrite.
        os.utime(self.bind, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        result = self.collect()
        self.assertEqual(result["status"], "unavailable", result)
        self.assertIn("metadata", result["reason"])

    def test_late_bind_and_replayed_complete_do_not_supply_provenance(self) -> None:
        self.write_producer(bound=False)
        result = self.collect()
        self.assertEqual(result["status"], "unavailable", result)
        self.assertIn("automatically bound", result["reason"])
        self.write_producer()
        self.rows[-1].update(rev=[9, 9], stage=["prepare", "prepare"], cursor=[PREPARE, PREPARE])
        self.rows[-1].pop("accepted")
        self.write_trace()
        self.assertEqual(self.collect()["status"], "unavailable")

    def test_malformed_trace_missing_transition_or_out_of_order_rows(self) -> None:
        path = self.run_dir / "trace.jsonl"
        valid = path.read_bytes()
        for broken in (valid + b'{"v":1}\n{bad\n', valid[:-1], valid.replace(b'"verb": "improve-pass"', b'"verb": "improve-bind"')):
            with self.subTest(tail=broken[-30:]):
                path.write_bytes(broken)
                self.assertEqual(self.collect()["status"], "unavailable")
        self.rows[2], self.rows[-1] = self.rows[-1], self.rows[2]
        self.write_trace()
        self.assertEqual(self.collect()["status"], "unavailable")

    def test_producer_packet_must_belong_to_expected_improve_action(self) -> None:
        packet = self.rows[1]
        original = (self.run_dir / packet["file"]).read_text(encoding="utf-8")
        modified = original.replace(f"--action={IMPROVE}", f"--action={OTHER_IMPROVE}")
        packet["sha"] = sha256(modified.encode())[:16]
        packet["file"] = f"packets/sent/{packet['sha']}.md"
        packet["chars"] = len(modified)
        (self.run_dir / packet["file"]).write_text(modified, encoding="utf-8")
        self.write_trace()
        self.assertEqual(self.collect()["status"], "unavailable")

    def test_wrong_expected_run_action_phase_revision_scope_seed_tree_and_manifest(self) -> None:
        result, _ = self.captured()
        for changed in (
            {"run_id": OTHER_PLAN}, {"plan_action": OTHER_PLAN}, {"improve_action": OTHER_IMPROVE},
            {"phase": "final"}, {"producer_revision": 7}, {"repo": str(self.top)}, {"repo_prefix": "."},
            {"seed_sha256": "f" * 64},
        ):
            with self.subTest(changed=changed):
                wrong = replace(self.expected, **changed)
                self.assertNotEqual(self.verify(result, expected=wrong)["status"], "matched")
                self.assertNotEqual(self.collect(wrong)["status"], "captured")
        self.assertEqual(self.verify(result, expected_tree="f" * 40)["status"], "invalid")
        self.assertEqual(self.verify(result, manifest_sha256="f" * 64)["status"], "invalid")

    def test_missing_objects_and_non_git_bind_are_unavailable(self) -> None:
        blob = self.git("rev-parse", f"{self.tree}:app/docs/architecture.md").decode().strip()
        (self.top / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
        result, manifest = self.captured()
        self.assertEqual(manifest["entries"][self.locator]["status"], "unavailable")
        self.assertEqual(self.verify(result)["status"], "unavailable")
        shutil.rmtree(self.top / ".git")
        self.assertEqual(self.collect()["status"], "unavailable")

    def test_modes_scope_traversal_binary_utf8_size_and_no_filters(self) -> None:
        outside = self.top / "app-sibling"
        outside.mkdir()
        sibling = outside / "architecture.md"
        sibling.write_text(INITIAL, encoding="utf-8")
        (self.docs / "symlink.md").symlink_to(self.arch)
        (self.repo / "link-dir").symlink_to(self.docs, target_is_directory=True)
        (self.docs / "binary.md").write_bytes(b"before\x00after")
        (self.docs / "bad-utf8.md").write_bytes(b"bad \xff")
        (self.docs / "too-big.md").write_bytes(b"x" * (evidence.MAX_BLOB_BYTES + 1))
        (self.repo / ".gitattributes").write_text("docs/architecture.md filter=probe\n", encoding="utf-8")
        sentinel = self.root / "smudge-triggered"
        self.git("config", "filter.probe.smudge", f"touch {sentinel} && cat")
        self.git("add", "-A")
        self.git("update-index", "--add", "--cacheinfo", "160000", "a" * 40, "app/docs/gitlink")
        self.tree = self.git("write-tree").decode().strip()
        rejected = [str(sibling), "docs/../docs/architecture.md", "docs/symlink.md", "link-dir/architecture.md",
                    "docs/gitlink", "docs", "https://example.invalid/a.md", "docs/binary.md",
                    "docs/bad-utf8.md", "docs/too-big.md"]
        self.seed["evidence_refs"].extend(rejected)
        self.write_producer()
        result, manifest = self.captured()
        self.assertEqual(self.verify(result)["status"], "matched")
        self.assertFalse(sentinel.exists())
        for locator in rejected:
            with self.subTest(locator=locator):
                self.assertIn(manifest["entries"][locator]["status"], ("unsupported", "unavailable"))
                self.assertIn(self.verify(result, locator=locator)["status"], ("unsupported", "unavailable"))

    def test_malformed_schema_duplicates_wrong_blob_and_corrupt_sidecar(self) -> None:
        result, manifest = self.captured()
        original = (self.out / evidence.MANIFEST_NAME).read_bytes()
        tests = [
            ({**manifest, "schema": "shiploop-initial-plan-evidence/v99"}, "unsupported"),
            ({**manifest, "schema": False}, "invalid"),
            ({**manifest, "initial_result": []}, "invalid"),
        ]
        for changed, expected_status in tests:
            with self.subTest(changed=expected_status):
                self.assertEqual(self.verify(self.replace_manifest(changed))["status"], expected_status)
        changed = json.loads(original)
        changed["entries"][self.locator]["blob"] = "f" * len(self.tree)
        changed["entries"][self.alias]["blob"] = "f" * len(self.tree)
        self.assertEqual(self.verify(self.replace_manifest(changed))["status"], "invalid")
        duplicate = b'{"schema":"bad",' + original[1:]
        (self.out / evidence.MANIFEST_NAME).write_bytes(duplicate)
        self.assertEqual(self.verify({"manifest_sha256": sha256(duplicate)})["status"], "invalid")
        (self.out / evidence.MANIFEST_NAME).write_bytes(original)
        sidecar = self.out / manifest["entries"][self.locator]["sidecar"]
        sidecar.write_bytes(sidecar.read_bytes().replace(b"before\ntaking", b"before taking"))
        self.assertEqual(self.verify(result)["status"], "invalid")

    def test_unsafe_sidecar_or_conflicting_alias_cannot_be_verified_or_archived(self) -> None:
        result, manifest = self.captured()
        original = (self.out / evidence.MANIFEST_NAME).read_bytes()
        changed = json.loads(original)
        changed["entries"][self.locator]["sidecar"] = "../outside.txt"
        changed["entries"][self.alias]["sidecar"] = "../outside.txt"
        receipt = self.replace_manifest(changed)
        self.assertEqual(self.verify(receipt)["status"], "invalid")
        archive = self.root / "archive"
        self.assertEqual(capture.archive_planning_evidence(
            self.out, archive, manifest_sha256=receipt["manifest_sha256"],
        )["status"], "invalid")
        self.assertFalse(archive.exists())

        changed = json.loads(original)
        different = changed["entries"]["docs/other.md"]
        changed["entries"][self.locator] = {**different, "path": changed["entries"][self.locator]["path"]}
        self.assertEqual(self.verify(self.replace_manifest(changed))["status"], "invalid")
        (self.out / evidence.MANIFEST_NAME).write_bytes(original)
        content = self.out / manifest["entries"][self.locator]["sidecar"]
        external = self.root / "outside.txt"
        content.rename(external)
        content.symlink_to(external)
        self.assertEqual(self.verify(result)["status"], "invalid")
        content.unlink()
        content.parent.rename(self.root / "outside-blobs")
        (self.root / "outside-blobs" / content.name).write_bytes(external.read_bytes())
        content.parent.symlink_to(self.root / "outside-blobs", target_is_directory=True)
        self.assertEqual(self.verify(result)["status"], "invalid")

    def test_exact_and_changed_retries_never_overwrite_receipt(self) -> None:
        first, _ = self.captured()
        manifest_path = Path(first["manifest"])
        before = (manifest_path.read_bytes(), manifest_path.stat().st_mtime_ns)
        second = self.collect()
        self.assertEqual(second, {**first, "reused": True})
        self.rows.insert(4, {"kind": "hook", "hook": "stop", "ts": self.rows[3]["ts"], "decision": "hold"})
        self.write_trace()
        retry = self.collect()
        self.assertEqual(retry["status"], "invalid", retry)
        self.assertIn("conflicting", retry["reason"])
        self.assertEqual(before, (manifest_path.read_bytes(), manifest_path.stat().st_mtime_ns))

    def test_cli_capture_verify_and_exit_status(self) -> None:
        executable = Path(evidence.__file__).resolve()
        identity = ["--run-id", RUN, "--plan-action", PLAN, "--improve-action", IMPROVE,
                    "--seed-sha256", self.expected.seed_sha256, "--phase", "initial"]
        scope = ["--producer-revision", "8", "--repo", str(self.repo), "--repo-prefix", "app"]

        def cli(*argv: str) -> tuple[int, dict]:
            result = subprocess.run([sys.executable, "-B", str(executable), *argv], cwd=self.root,
                                    capture_output=True, text=True, check=False)
            self.assertFalse(result.stderr, result.stderr)
            return result.returncode, json.loads(result.stdout)

        code, result = cli("capture", *identity, *scope, "--run-dir", str(self.run_dir), "--output-dir", str(self.out))
        self.assertEqual((code, result["status"]), (0, "captured"))
        code, result = cli("verify", *identity, *scope, "--bundle-dir", str(self.out),
                           "--manifest-sha256", result["manifest_sha256"], "--locator", self.locator, "--quote", FINAL)
        self.assertEqual((code, result["status"]), (1, "not-found"))
        code, result = cli("verify", *identity, "--run-dir", str(self.run_dir),
                           "--field", "summary", "--quote", self.seed["summary"])
        self.assertEqual((code, result["status"]), (0, "matched"))


if __name__ == "__main__":
    unittest.main()
