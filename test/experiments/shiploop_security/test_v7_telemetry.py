"""Synthetic stdout, parent rollout and independent started-ledger controls."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v7 import telemetry


THREAD = "00000000-0000-0000-0000-000000000011"
OTHER = "00000000-0000-0000-0000-000000000012"
NEXT_TURN = "00000000-0000-0000-0000-000000000013"
FIRST_TURN = "00000000-0000-0000-0000-000000000014"
FULL = {
    "input_tokens": 100, "output_tokens": 20,
    "cache_read_input_tokens": 40, "reasoning_tokens": 0,
}
PREFIX = {
    "input_tokens": 60, "output_tokens": 8,
    "cache_read_input_tokens": 30, "reasoning_tokens": 0,
}
ROLES = {"model": "gpt-6.1-sol", "effort": "medium"}


def jsonl(rows):
    return b"".join(json.dumps(row).encode() + b"\n" for row in rows)


def pair(input_tokens, output_tokens):
    return {"input_tokens": input_tokens, "output_tokens": output_tokens}


def wire(metrics):
    return {telemetry.FIELDS[key]: value for key, value in metrics.items()}


class TelemetryV7Test(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.trial = Path(folder.name).resolve()
        self.home = self.trial / "home" / ".codex"
        self.thread = THREAD
        self.rollout = self.home / "sessions" / "2026" / "01" / "01" / f"rollout-synthetic-{THREAD}.jsonl"
        self.rollout.parent.mkdir(parents=True)
        self.raw = self.trial / "raw-events.jsonl"
        self.sessions = []
        self.binding = {"registration_sha256": "a" * 64, "trial": "synthetic"}
        self.context = {"cwd": str(self.trial / "work"), **ROLES,
                        "started_at": "2026-01-01T00:00:01Z", "ended_at": "2026-01-01T00:00:09Z",
                        "resumed_thread_id": None}
        self.native = jsonl([
            {"timestamp": f"2026-01-01T00:00:0{i}Z", "ordinal": i, "type": kind, "payload": payload}
            for i, (kind, payload) in enumerate([
                ("session_meta", {"id": THREAD, "source": "exec", "cwd": self.context["cwd"]}),
                ("event_msg", {"type": "task_started", "turn_id": FIRST_TURN}),
                ("turn_context", {"turn_id": FIRST_TURN, "cwd": self.context["cwd"], **ROLES}),
                ("event_msg", {"type": "token_count", "info": {"total_token_usage": wire(PREFIX)}}),
                ("event_msg", {"type": "token_count", "info": {"total_token_usage": wire(FULL)}}),
                ("event_msg", {"type": "task_complete", "turn_id": FIRST_TURN}),
            ], 1)
        ])
        self.stdout = jsonl([{"type": "thread.started", "thread_id": THREAD}, {"type": "turn.started"},
                             {"type": "turn.completed", "usage": wire(FULL)}])

    def start(self, context, raw_start):
        return telemetry.append_start(self.trial, self.binding, cwd=context["cwd"], home=self.home,
                                      model=ROLES["model"], effort=ROLES["effort"], started_at=context["started_at"],
                                      resumed=context["resumed_thread_id"], raw_start=raw_start,
                                      argv=["synthetic-exec", "--json", ROLES["model"]])

    def replay(self, sessions=None, binding=None):
        return telemetry.ledger_usage(self.trial, self.sessions if sessions is None else sessions,
                                      self.binding if binding is None else binding, roles=ROLES)

    def capture(self, native=None, stdout=None, context=None):
        native = self.native if native is None else native
        stdout = self.stdout if stdout is None else stdout
        start = self.raw.stat().st_size if self.raw.exists() else 0
        context = self.context if context is None else context
        start_context = self.start(context, start)
        with self.raw.open("ab") as raw:
            raw.write(stdout)
        self.rollout.write_bytes(native)
        session = {"raw_usage_bytes": [start, start + len(stdout)], "launch": start_context}
        self.sessions.append(session)
        session["native_usage"] = telemetry.capture_native_usage(
            self.trial, self.home, self.sessions, context,
        )
        return self.replay()

    def assert_unknown(self, result, observed=None):
        self.assertFalse(result["usage_complete"])
        self.assertFalse(result["coverage_complete"])
        self.assertIsNone(result["measured_usage"])
        self.assertTrue(all(v is None for v in result["totals"].values()))
        self.assertEqual(result["observed_usage"], observed)
        self.assertIsNone(result["cost_usd"])

    def test_complete_parent(self):
        result = self.capture()
        self.assertTrue(result["usage_complete"])
        self.assertEqual(result["measured_usage"], FULL)
        self.assertEqual(result["observed_usage"], FULL)
        receipt = result["sessions"][0]
        copied = (self.trial / receipt["native_copy"]).read_bytes()
        self.assertEqual(copied, self.native)
        self.assertEqual(receipt["native_sha256"], hashlib.sha256(self.native).hexdigest())
        self.assertEqual(receipt["raw_sha256"], hashlib.sha256(self.stdout).hexdigest())
        offset = receipt["token_count_bytes"]
        self.assertEqual(copied[slice(*offset)], self.native.splitlines(keepends=True)[4])
        self.assertEqual(copied[slice(*receipt["turn_context_bytes"])],
                         self.native.splitlines(keepends=True)[2])
        self.assertEqual(self.stdout[slice(*receipt["raw_terminal_bytes"])],
                         self.stdout.splitlines(keepends=True)[2])

    def test_interrupted_parent_prefix(self):
        native = b"".join(self.native.splitlines(keepends=True)[:4])
        stdout = b"".join(self.stdout.splitlines(keepends=True)[:-1])
        result = self.capture(native, stdout)
        self.assert_unknown(result, PREFIX)
        offset = result["sessions"][0]["token_count_bytes"]
        self.assertEqual(native[slice(*offset)], native.splitlines(keepends=True)[3])

    def test_malformed_stdout_does_not_qualify_complete_usage(self):
        result = self.capture(stdout=self.stdout + b"{bad json}\n")
        self.assert_unknown(result, FULL)
        self.assertEqual(result["sessions"][0]["raw_malformed_bytes"],
                         [[len(self.stdout), len(self.stdout) + len(b"{bad json}\n")]])

    def test_malformed_native_tail_preserves_only_bound_prefix(self):
        native = b"".join(self.native.splitlines(keepends=True)[:4])
        result = self.capture(native=native + b'{"type":', stdout=self.stdout)
        self.assert_unknown(result, PREFIX)

    def test_duplicate_stdout_terminal_is_not_complete(self):
        result = self.capture(stdout=self.stdout + self.stdout.splitlines(keepends=True)[-1])
        self.assert_unknown(result, FULL)
        self.assertEqual(result["sessions"][0]["terminal_events"], 2)

    def test_duplicate_native_terminal_is_not_complete(self):
        result = self.capture(native=self.native + self.native.splitlines(keepends=True)[-1])
        self.assert_unknown(result)

    def test_wrong_thread_metadata_is_not_parent_evidence(self):
        meta, tail = self.native.split(b"\n", 1)
        row = json.loads(meta)
        row["payload"]["id"] = OTHER
        result = self.capture(native=jsonl([row]) + tail)
        self.assert_unknown(result)
        self.assertIn("wrong native parent", self.sessions[0]["native_usage"]["error"])

    def test_wrong_effort_cannot_bind(self):
        result = self.capture(context=dict(self.context, effort="high"))
        self.assert_unknown(result)
        self.assertEqual(result["ledger_problem"], "unbound_invocation")

    def test_mixed_stdout_threads_cannot_bind(self):
        result = self.capture(stdout=self.stdout + jsonl([{"type": "thread.started", "thread_id": OTHER}]))
        self.assert_unknown(result)
        self.assertIn("one parent thread", self.sessions[0]["native_usage"]["error"])

    def test_ambiguous_rollouts_cannot_bind(self):
        decoy = self.rollout.with_name(f"rollout-other-{self.thread}.jsonl")
        decoy.write_bytes(self.native)
        result = self.capture()
        self.assert_unknown(result)
        self.assertIn("ambiguous", self.sessions[0]["native_usage"]["error"])

    def test_no_children_are_opened_or_counted(self):
        child_id = OTHER
        decoy = self.rollout.with_name(f"rollout-child-{child_id}.jsonl")
        decoy.write_bytes(b"not evidence for this invocation\n")
        read = Path.read_bytes
        opened = []

        def track(path):
            opened.append(path)
            return read(path)

        with patch.object(Path, "read_bytes", track):
            result = self.capture()
        self.assertEqual(result["measured_usage"], FULL)
        self.assertNotIn(decoy, opened)
        self.assertEqual(len(list((self.trial / "native-usage").iterdir())), 1)

    def test_missing_optional_terminal_metrics_stay_null(self):
        rows = list(map(json.loads, self.stdout.splitlines()))
        rows[-1]["usage"] = pair(100, 20)
        result = self.capture(stdout=jsonl(rows))
        self.assertTrue(result["usage_complete"])
        self.assertEqual(result["measured_usage"],
                         dict(pair(100, 20), cache_read_input_tokens=None, reasoning_tokens=None))
        self.assertEqual(result["observed_usage"], FULL)

    def test_disagreeing_terminal_usage_stays_unknown(self):
        rows = list(map(json.loads, self.stdout.splitlines()))
        rows[-1]["usage"]["input_tokens"] += 1
        result = self.capture(stdout=jsonl(rows))
        self.assert_unknown(result, FULL)
        self.assertIn("disagrees", result["sessions"][0]["error"])

    def test_copied_rollout_hash_is_rechecked_during_replay(self):
        self.capture()
        copy = self.trial / self.sessions[0]["native_usage"]["native_copy"]
        with copy.open("ab") as handle:
            handle.write(b"changed\n")
        self.assert_unknown(self.replay())

    def resume(self, total, terminal, *, prefix=False, last=None):
        context = dict(self.context, resumed_thread_id=self.thread,
                       started_at="2026-01-01T00:00:20Z", ended_at="2026-01-01T00:00:30Z")
        native = [
            ("event_msg", {"type": "task_started", "turn_id": NEXT_TURN}),
            ("turn_context", {k: context[k] for k in ("cwd", "model", "effort")} | {"turn_id": NEXT_TURN}),
            ("event_msg", {"type": "token_count", "info": {
                "total_token_usage": total, "last_token_usage": pair(30, 5) if last is None else last,
            }}),
        ]
        stdout = [{"type": "thread.started", "thread_id": self.thread}, {"type": "turn.started"}]
        if not prefix:
            native.append(("event_msg", {"type": "task_complete", "turn_id": NEXT_TURN}))
            stdout.append({"type": "turn.completed", "usage": terminal})
        tail = jsonl([
            {"timestamp": f"2026-01-01T00:00:{21 + n}Z", "ordinal": n,
             "type": kind, "payload": payload}
            for n, (kind, payload) in enumerate(native)
        ])
        return self.capture(native=self.native + tail, stdout=jsonl(stdout), context=context)

    def test_continuation_cumulative_receipt_is_counted_once(self):
        self.capture()
        result = self.resume(pair(130, 25), pair(130, 25))
        self.assertTrue(result["usage_complete"])
        self.assertEqual(result["measured_usage"],
                         dict(pair(130, 25), cache_read_input_tokens=None, reasoning_tokens=None))
        self.assertEqual(result["sessions"][1]["fields"]["input_tokens"], 30)
        self.assertEqual(result["sessions"][1]["native_bytes"][0], len(self.native))

    def test_continuation_with_reset_counter_is_counted_once(self):
        self.capture()
        result = self.resume(pair(30, 5), pair(30, 5))
        self.assertTrue(result["usage_complete"])
        self.assertEqual(result["measured_usage"]["input_tokens"], 130)

    def test_interrupted_continuation_reports_only_observed_delta(self):
        self.capture()
        result = self.resume(pair(130, 25), None, prefix=True)
        self.assert_unknown(
            result, dict(pair(130, 25), cache_read_input_tokens=None, reasoning_tokens=None),
        )

    def test_ambiguous_continuation_counter_cannot_be_added(self):
        self.capture()
        result = self.resume(pair(70, 15), pair(70, 15))
        self.assert_unknown(result, FULL)
        self.assertIn("ambiguous continuation counter", result["sessions"][1]["error"])


    def test_repeated_prior_counter_is_not_a_reset(self):
        self.capture()
        prior = pair(100, 20)
        result = self.resume(prior, prior, last=prior)
        self.assert_unknown(result, FULL)
        self.assertIn("ambiguous continuation counter", result["sessions"][1]["error"])

    def test_lost_invocation_cannot_claim_complete_prefix(self):
        self.capture()
        self.start(dict(self.context, started_at="2026-01-01T00:00:20Z",
                        resumed_thread_id=self.thread), len(self.stdout))
        result = self.replay()
        self.assert_unknown(result, FULL)
        self.assertEqual((result["started_invocations"], result["bound_invocations"],
                          result["complete_invocations"]), (2, 1, 1))

    def test_truncating_sessions_cannot_reduce_started_count(self):
        self.capture()
        self.resume(pair(130, 25), pair(130, 25))
        result = self.replay(self.sessions[:1])
        self.assert_unknown(result, FULL)
        self.assertEqual(result["started_invocations"], 2)

    def test_wrong_binding_or_torn_start_ledger_invalidates_usage(self):
        self.capture()
        self.assert_unknown(self.replay(binding={"trial": "other"}))
        with (self.trial / telemetry.LEDGER).open("ab") as handle:
            handle.write(b'{"type":')
        result = self.replay()
        self.assert_unknown(result)
        self.assertIsNone(result["started_invocations"])

    def test_stale_overlapping_raw_range_keeps_only_verified_prefix(self):
        self.capture()
        self.resume(pair(130, 25), pair(130, 25))
        self.sessions[1]["raw_usage_bytes"][0] -= 1
        result = self.replay()
        self.assert_unknown(result, FULL)
        self.assertEqual(result["bound_invocations"], 1)

    def test_native_rollout_source_cannot_be_swapped_to_another_home(self):
        self.capture()
        captured = self.sessions[0]["native_usage"]
        captured["native_source"] = captured["native_source"].replace("home/", "other/", 1)
        self.assert_unknown(self.replay())

    def test_optional_metrics_are_subsets(self):
        rows = list(map(json.loads, self.stdout.splitlines()))
        rows[-1]["usage"]["reasoning_output_tokens"] = 21
        self.assert_unknown(self.capture(stdout=jsonl(rows)), FULL)


if __name__ == "__main__":
    unittest.main()
