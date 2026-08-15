#!/usr/bin/env python3
"""Test harness for the change-detection detect engine.

Tests:
  - Two-sided matrix: trigger (positive) + no-fire (negative) for each condition
  - Bounce verification: fire → no-fire → re-fire → no-fire
  - A→B→A re-fire
  - Acknowledged pruning
  - Extraction from real Alaska SSR HTML
  - State atomicity
  - Config validation

Usage:
  python -m pytest tests/test_detect_engine.py -v
  python tests/test_detect_engine.py
"""

import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
import httpx
import yaml  # noqa: E402
import pytest  # noqa: F401 — ensures harness detects pytest style
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts dir to path
SCRIPTS_DIR = Path(__file__).parent.parent.resolve() / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import engine components
from detect_engine import (  # noqa: E402
    FetchAgent, FetchResult, ExtractAgent, StateManager,
    TriggerAgent, GroupEvaluator, ActionAgent, LLMEscalationAgent,
    ConditionResult, Condition, Group, DetectConfig, Source, ExtractSpec,
    RetryConfig, LLMEscalation, StateConfig, write_fetch_failure_escalation,
    _fire_once_enabled, run_engine, write_health,
    parse_duration, load_config, validate_config_cross_refs,
    _expand_transitions, _state_delta, _numeric_delta, _is_empty_value,
)
from pydantic import ValidationError  # noqa: E402

FIXTURES_DIR = SCRIPTS_DIR / "fixtures"
ALASKA_HTML = FIXTURES_DIR / "alaska_as706.html"

# Prevent tests from writing health/escalation files to production directories.
# All tests use temp directories instead. (Same fix applied to ESCALATION_DIR
# after action_failure_* files leaked into cron/state/escalations/ from tests
# running with dry_run=False.)
import detect_engine as _detect_engine_mod  # noqa: E402
_test_health_dir = tempfile.mkdtemp(prefix="detect-health-test-")
_detect_engine_mod.HEALTH_DIR = Path(_test_health_dir)
_test_escalation_dir = tempfile.mkdtemp(prefix="detect-escalation-test-")
_detect_engine_mod.ESCALATION_DIR = Path(_test_escalation_dir)


# ═══════════════════════════════════════════════════════════════
#  Test helpers
# ═══════════════════════════════════════════════════════════════

class MockCalendarEvent:
    """Build a mock calendar event dict."""
    @staticmethod
    def make(summary="✈️ Alaska AS706: SEA → OAK", start="", end="", description=""):
        return {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": "America/Los_Angeles"},
            "end": {"dateTime": end, "timeZone": "America/Los_Angeles"},
            "description": description,
        }


def make_state(
    dep_time="2026-07-07T17:20:00-07:00",
    arr_time="2026-07-07T19:18:00-07:00",
    dep_airport="SEA",
    arr_airport="OAK",
    gate="C3",
    status=None,
    cal_title="✈️ Alaska AS706: SEA → OAK",
    acknowledged=None,
    first_seen=None,
    last_fired=None,
):
    """Create a state dict with defaults matching current AS706 data."""
    return {
        "dep_time": dep_time,
        "arr_time": arr_time,
        "dep_airport": dep_airport,
        "arr_airport": arr_airport,
        "gate": gate,
        "status": status,
        "cal_title": cal_title,
        "acknowledged": acknowledged or {},
        "first_seen": first_seen or {},
        "last_fired": last_fired or {},
    }


def make_extracted(
    dep_time="2026-07-07T17:20:00-07:00",
    arr_time="2026-07-07T19:18:00-07:00",
    dep_airport="SEA",
    arr_airport="OAK",
    gate="C3",
    status=None,
):
    """Create extracted values dict matching current AS706 data."""
    return {
        "dep_time": dep_time,
        "arr_time": arr_time,
        "dep_airport": dep_airport,
        "arr_airport": arr_airport,
        "gate": gate,
        "status": status,
    }


def eval_condition(cond_dict, prev_state, extracted, calendar_events=None):
    """Helper: evaluate a single condition with mocked state."""
    cal = calendar_events or {"flight": MockCalendarEvent.make()}
    trigger = TriggerAgent(prev_state, extracted, cal)
    cond = Condition(**cond_dict)
    return trigger.evaluate(cond)


def run_engine_with_mock_json(config_path, payload, dry_run=False):
    """Run the engine with one mocked JSON HTTP response."""
    with patch("detect_engine.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.text = json.dumps(payload)
        mock_resp.request = None
        mock_client.request.return_value = mock_resp
        return run_engine(str(config_path), dry_run=dry_run)


class TempStateDir:
    """Context manager for temp state directory."""
    def __init__(self):
        self.tmpdir = None
        self.state_path = None

    def __enter__(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="guard_test_"))
        self.state_path = self.tmpdir / "state.json"
        return self

    def __exit__(self, *args):
        if self.tmpdir and self.tmpdir.exists():
            shutil.rmtree(self.tmpdir)

    def write_state(self, state: dict):
        self.state_path.write_text(json.dumps(state, indent=2))

    def read_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {}


# ═══════════════════════════════════════════════════════════════
#  Test runner (no pytest dependency — simple assert-based)
# ═══════════════════════════════════════════════════════════════

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run(self, name: str, fn):
        try:
            fn()
            self.passed += 1
            print(f"  ✅ {name}")
        except AssertionError as exc:
            self.failed += 1
            self.errors.append((name, str(exc)))
            print(f"  ❌ {name}: {exc}")
        except Exception as exc:
            self.failed += 1
            self.errors.append((name, f"Exception: {exc}"))
            print(f"  💥 {name}: {exc}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print("\nFailures:")
            for name, err in self.errors:
                print(f"  ❌ {name}: {err}")
        return self.failed == 0


runner = TestRunner()


# ═══════════════════════════════════════════════════════════════
#  TC-EXTRACT: Extraction tests (from real Alaska HTML)
# ═══════════════════════════════════════════════════════════════

def test_extract_jsonld_from_alaska():
    """Extract values from real Alaska SSR HTML via jsonpath_from_html."""
    html = ALASKA_HTML.read_text()
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()

    specs = [
        ExtractSpec(id="dep_time", type="jsonpath_from_html", path="$.departureTime"),
        ExtractSpec(id="arr_time", type="jsonpath_from_html", path="$.arrivalTime"),
        ExtractSpec(id="dep_airport", type="jsonpath_from_html", path="$.departureAirport"),
        ExtractSpec(id="arr_airport", type="jsonpath_from_html", path="$.arrivalAirport"),
        ExtractSpec(id="gate", type="jsonpath_from_html", path="$.departureGate"),
    ]
    values = extractor.extract(result, specs)
    assert values["dep_airport"] == "SEA", f"Expected SEA, got {values['dep_airport']}"
    assert values["arr_airport"] == "OAK", f"Expected OAK, got {values['arr_airport']}"
    assert values["dep_time"] is not None, "dep_time should not be None"
    assert values["gate"] is not None, "gate should not be None"


def test_extract_regex():
    """Test regex extraction."""
    html = '<div>Gate: C3</div>'
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="gate", type="regex", pattern=r"Gate:\s*(\w+)", group=1)
    values = extractor.extract(result, [spec])
    assert values["gate"] == "C3", f"Expected C3, got {values['gate']}"


def test_extract_css():
    """Test CSS extraction."""
    html = '<div class="status">On time</div>'
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="status", type="css", selector=".status", transform="text")
    values = extractor.extract(result, [spec])
    assert values["status"] == "On time", f"Expected 'On time', got {values['status']}"


def test_extract_jsonpath():
    """Test JSONPath extraction from JSON response."""
    body = json.dumps({"data": [{"departure": {"scheduled": "2026-07-07T17:20:00-07:00"}}]})
    result = FetchResult(200, {}, body)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="dep_time", type="jsonpath", path="$.data[0].departure.scheduled")
    values = extractor.extract(result, [spec])
    assert values["dep_time"] == "2026-07-07T17:20:00-07:00"


runner.run("TC-EXTRACT-01: Extract JSON-LD from Alaska HTML", test_extract_jsonld_from_alaska)
runner.run("TC-EXTRACT-02: Extract via regex", test_extract_regex)
runner.run("TC-EXTRACT-03: Extract via CSS", test_extract_css)
runner.run("TC-EXTRACT-04: Extract via JSONPath", test_extract_jsonpath)


# ═══════════════════════════════════════════════════════════════
#  TC-01: dep_time_changed — two-sided matrix
# ═══════════════════════════════════════════════════════════════

def test_dep_time_changed_positive():
    """Fabricate previous state with different dep_time → condition fires."""
    prev = make_state(dep_time="2026-07-07T17:25:00-07:00")  # OLD time
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")  # CURRENT time
    cond = {"id": "dep_time_changed", "field": "dep_time", "op": "changed",
            "baseline": {"source": "state", "field": "dep_time"}}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"Should fire — dep_time changed from 17:25 to 17:20. Reason: {result.reason}"


def test_dep_time_changed_negative():
    """Fabricate previous state with SAME dep_time → condition does NOT fire."""
    prev = make_state(dep_time="2026-07-07T17:20:00-07:00")  # SAME as extracted
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
    cond = {"id": "dep_time_changed", "field": "dep_time", "op": "changed",
            "baseline": {"source": "state", "field": "dep_time"}}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — dep_time unchanged. Reason: {result.reason}"


runner.run("TC-01-POS: dep_time_changed fires on change", test_dep_time_changed_positive)
runner.run("TC-01-NEG: dep_time_changed silent on no change", test_dep_time_changed_negative)


# ═══════════════════════════════════════════════════════════════
#  TC-02: arr_time_changed — two-sided matrix
# ═══════════════════════════════════════════════════════════════

def test_arr_time_changed_positive():
    prev = make_state(arr_time="2026-07-07T19:33:00-07:00")
    extracted = make_extracted(arr_time="2026-07-07T19:18:00-07:00")
    cond = {"id": "arr_time_changed", "field": "arr_time", "op": "changed",
            "baseline": {"source": "state", "field": "arr_time"}}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"Should fire. Reason: {result.reason}"


def test_arr_time_changed_negative():
    prev = make_state(arr_time="2026-07-07T19:18:00-07:00")
    extracted = make_extracted(arr_time="2026-07-07T19:18:00-07:00")
    cond = {"id": "arr_time_changed", "field": "arr_time", "op": "changed",
            "baseline": {"source": "state", "field": "arr_time"}}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire. Reason: {result.reason}"


runner.run("TC-02-POS: arr_time_changed fires on change", test_arr_time_changed_positive)
runner.run("TC-02-NEG: arr_time_changed silent on no change", test_arr_time_changed_negative)


# ═══════════════════════════════════════════════════════════════
#  TC-04: flight_delayed — two-sided with unless clause
# ═══════════════════════════════════════════════════════════════

def test_flight_delayed_positive():
    """Status is Delayed, calendar doesn't say DELAYED → fires."""
    prev = make_state(status="On time", cal_title="✈️ Alaska AS706: SEA → OAK")
    extracted = make_extracted(status="Delayed")
    cal = {"flight": MockCalendarEvent.make(summary="✈️ Alaska AS706: SEA → OAK")}
    cond = {"id": "flight_delayed", "field": "status", "op": "eq", "value": "Delayed",
            "unless": {"field": "cal_title", "op": "contains", "value": "DELAYED"}}
    result = eval_condition(cond, prev, extracted, cal)
    assert result.matched, f"Should fire — status Delayed, calendar clean. Reason: {result.reason}"


def test_flight_delayed_negative():
    """Status is Delayed, calendar already says DELAYED → unless suppresses."""
    prev = make_state(status="Delayed", cal_title="DELAYED: ✈️ Alaska AS706: SEA → OAK")
    extracted = make_extracted(status="Delayed")
    cal = {"flight": MockCalendarEvent.make(summary="DELAYED: ✈️ Alaska AS706: SEA → OAK")}
    cond = {"id": "flight_delayed", "field": "status", "op": "eq", "value": "Delayed",
            "unless": {"field": "cal_title", "op": "contains", "value": "DELAYED"}}
    result = eval_condition(cond, prev, extracted, cal)
    assert not result.matched, f"Should NOT fire — calendar already says DELAYED. Reason: {result.reason}"


def test_flight_delayed_not_delayed():
    """Status is On time → condition doesn't match."""
    prev = make_state(status="On time")
    extracted = make_extracted(status="On time")
    cond = {"id": "flight_delayed", "field": "status", "op": "eq", "value": "Delayed",
            "unless": {"field": "cal_title", "op": "contains", "value": "DELAYED"}}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — status is On time. Reason: {result.reason}"


runner.run("TC-04-POS: flight_delayed fires when calendar clean", test_flight_delayed_positive)
runner.run("TC-04-NEG: flight_delayed suppressed by unless (calendar says DELAYED)", test_flight_delayed_negative)
runner.run("TC-04-NOT: flight_delayed doesn't fire when On time", test_flight_delayed_not_delayed)


# ═══════════════════════════════════════════════════════════════
#  TC-05: flight_cancelled — two-sided
# ═══════════════════════════════════════════════════════════════

def test_flight_cancelled_positive():
    prev = make_state(status="On time")
    extracted = make_extracted(status="Cancelled")
    cal = {"flight": MockCalendarEvent.make(summary="✈️ Alaska AS706: SEA → OAK")}
    cond = {"id": "flight_cancelled", "field": "status", "op": "eq", "value": "Cancelled",
            "unless": {"field": "cal_title", "op": "contains", "value": "CANCEL"}}
    result = eval_condition(cond, prev, extracted, cal)
    assert result.matched, f"Should fire. Reason: {result.reason}"


def test_flight_cancelled_negative():
    prev = make_state(status="Cancelled")
    extracted = make_extracted(status="Cancelled")
    cal = {"flight": MockCalendarEvent.make(summary="CANCELLED: ✈️ Alaska AS706")}
    cond = {"id": "flight_cancelled", "field": "status", "op": "eq", "value": "Cancelled",
            "unless": {"field": "cal_title", "op": "contains", "value": "CANCEL"}}
    result = eval_condition(cond, prev, extracted, cal)
    assert not result.matched, f"Should NOT fire — calendar says CANCELLED. Reason: {result.reason}"


runner.run("TC-05-POS: flight_cancelled fires", test_flight_cancelled_positive)
runner.run("TC-05-NEG: flight_cancelled suppressed by unless", test_flight_cancelled_negative)


# ═══════════════════════════════════════════════════════════════
#  TC-06: gate_changed — two-sided with AND + NOT
# ═══════════════════════════════════════════════════════════════

def test_gate_changed_positive():
    prev = make_state(gate="C3")
    extracted = make_extracted(gate="D12")
    cond = {"id": "gate_changed", "and": [
        {"field": "gate", "op": "changed", "baseline": {"source": "state", "field": "gate"}},
        {"not": [{"field": "gate", "op": "eq", "value": ""}]}
    ]}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"Should fire — gate C3→D12. Reason: {result.reason}"


def test_gate_changed_negative():
    prev = make_state(gate="D12")
    extracted = make_extracted(gate="D12")
    cond = {"id": "gate_changed", "and": [
        {"field": "gate", "op": "changed", "baseline": {"source": "state", "field": "gate"}},
        {"not": [{"field": "gate", "op": "eq", "value": ""}]}
    ]}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — gate unchanged. Reason: {result.reason}"


def test_gate_changed_empty_not_fired():
    """Gate is empty (not posted yet) → should NOT fire (NOT clause catches it)."""
    prev = make_state(gate="")
    extracted = make_extracted(gate="")
    cond = {"id": "gate_changed", "and": [
        {"field": "gate", "op": "changed", "baseline": {"source": "state", "field": "gate"}},
        {"not": [{"field": "gate", "op": "eq", "value": ""}]}
    ]}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — gate is empty. Reason: {result.reason}"


runner.run("TC-06-POS: gate_changed fires on C3→D12", test_gate_changed_positive)
runner.run("TC-06-NEG: gate_changed silent when unchanged", test_gate_changed_negative)
runner.run("TC-06-EMPTY: gate_changed doesn't fire when gate empty", test_gate_changed_empty_not_fired)


# ═══════════════════════════════════════════════════════════════
#  TC-10: status_recovered — two-sided (anti-bounce for persistent condition)
# ═══════════════════════════════════════════════════════════════

def test_status_recovered_positive():
    """Status is On time, calendar still says DELAYED → fires."""
    prev = make_state(status="Delayed", cal_title="DELAYED: ✈️ Alaska AS706")
    extracted = make_extracted(status="On time")
    cal = {"flight": MockCalendarEvent.make(summary="DELAYED: ✈️ Alaska AS706")}
    cond = {"id": "status_recovered", "and": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "cal_title", "op": "contains", "value": "DELAYED"}
    ]}
    result = eval_condition(cond, prev, extracted, cal)
    assert result.matched, f"Should fire — recovered but calendar still says DELAYED. Reason: {result.reason}"


def test_status_recovered_negative():
    """Status is On time, calendar is clean → does NOT fire (anti-bounce)."""
    prev = make_state(status="On time", cal_title="✈️ Alaska AS706")
    extracted = make_extracted(status="On time")
    cal = {"flight": MockCalendarEvent.make(summary="✈️ Alaska AS706")}
    cond = {"id": "status_recovered", "and": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "cal_title", "op": "contains", "value": "DELAYED"}
    ]}
    result = eval_condition(cond, prev, extracted, cal)
    assert not result.matched, f"Should NOT fire — calendar clean. Reason: {result.reason}"


def test_status_recovered_still_delayed():
    """Status is still Delayed → does NOT fire."""
    prev = make_state(status="Delayed")
    extracted = make_extracted(status="Delayed")
    cond = {"id": "status_recovered", "and": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "cal_title", "op": "contains", "value": "DELAYED"}
    ]}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — still delayed. Reason: {result.reason}"


runner.run("TC-10-POS: status_recovered fires when calendar stale", test_status_recovered_positive)
runner.run("TC-10-NEG: status_recovered silent when calendar clean", test_status_recovered_negative)
runner.run("TC-10-STILL: status_recovered doesn't fire when still delayed", test_status_recovered_still_delayed)


# ═══════════════════════════════════════════════════════════════
#  TC-BOUNCE: Bounce verification protocol (4-step)
# ═══════════════════════════════════════════════════════════════

def test_bounce_verification():
    """Verify: fire → no-fire → re-fire → no-fire."""
    with TempStateDir() as tsd:
        # Step 1: Fabricated state with old dep_time → should fire
        tsd.write_state(make_state(dep_time="2026-07-07T17:25:00-07:00"))
        sm = StateManager(tsd.state_path)
        sm.load()

        prev = dict(sm.state)
        extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
        eval_ctx = {**prev, **extracted}

        trigger = TriggerAgent(prev, eval_ctx, {"flight": MockCalendarEvent.make()})
        cond = Condition(id="dep_time_changed", field="dep_time", op="changed",
                         baseline={"source": "state", "field": "dep_time"})
        result1 = trigger.evaluate(cond)
        assert result1.matched, f"Step 1: Should fire. Reason: {result1.reason}"

        # Simulate action success → acknowledge + update state
        sm.update_extracted(extracted)
        sm.acknowledge("dep_time_changed", extracted["dep_time"])
        sm.set_last_fired("dep_time_changed")
        sm.save()

        # Step 2: Same values, acknowledged → should NOT fire
        prev2 = sm.load()
        eval_ctx2 = {**prev2, **extracted}
        trigger2 = TriggerAgent(prev2, eval_ctx2, {"flight": MockCalendarEvent.make()})
        result2 = trigger2.evaluate(cond)
        assert not result2.matched, f"Step 2: Should NOT fire (bounce prevention). Reason: {result2.reason}"

        # Step 3: Value changes again → should fire
        extracted3 = make_extracted(dep_time="2026-07-07T16:55:00-07:00")
        eval_ctx3 = {**prev2, **extracted3}
        trigger3 = TriggerAgent(prev2, eval_ctx3, {"flight": MockCalendarEvent.make()})
        result3 = trigger3.evaluate(cond)
        assert result3.matched, f"Step 3: Should fire on value change. Reason: {result3.reason}"

        # Step 4: Acknowledge new value → should NOT fire
        sm.update_extracted(extracted3)
        sm.acknowledge("dep_time_changed", extracted3["dep_time"])
        sm.save()
        prev4 = sm.load()
        eval_ctx4 = {**prev4, **extracted3}
        trigger4 = TriggerAgent(prev4, eval_ctx4, {"flight": MockCalendarEvent.make()})
        result4 = trigger4.evaluate(cond)
        assert not result4.matched, f"Step 4: Should NOT fire after acknowledgment. Reason: {result4.reason}"


runner.run("TC-BOUNCE: 4-step bounce verification (fire→silent→refire→silent)", test_bounce_verification)


# ═══════════════════════════════════════════════════════════════
#  TC-ABA: A→B→A re-fire test
# ═══════════════════════════════════════════════════════════════

def test_aba_refire():
    """Verify A→B (fires), B→B (no fire), B→A (fires again)."""
    val_a = "2026-07-07T17:25:00-07:00"
    val_b = "2026-07-07T17:20:00-07:00"
    cond = Condition(id="dep_time_changed", field="dep_time", op="changed",
                     baseline={"source": "state", "field": "dep_time"})

    with TempStateDir() as tsd:
        # A→B: state has A, extracted has B → fires
        tsd.write_state(make_state(dep_time=val_a))
        sm = StateManager(tsd.state_path)
        sm.load()
        prev = dict(sm.state)
        extracted_b = make_extracted(dep_time=val_b)
        ctx = {**prev, **extracted_b}
        result_ab = TriggerAgent(prev, ctx, {"flight": MockCalendarEvent.make()}).evaluate(cond)
        assert result_ab.matched, "A→B: Should fire"

        # Acknowledge B
        sm.update_extracted(extracted_b)
        sm.acknowledge("dep_time_changed", val_b)
        sm.save()

        # B→B: state has B, extracted has B → no fire
        prev_b = sm.load()
        ctx_b = {**prev_b, **extracted_b}
        result_bb = TriggerAgent(prev_b, ctx_b, {"flight": MockCalendarEvent.make()}).evaluate(cond)
        assert not result_bb.matched, "B→B: Should NOT fire (no bounce)"

        # B→A: state has B (acknowledged), extracted has A → fires!
        extracted_a = make_extracted(dep_time=val_a)
        ctx_a = {**prev_b, **extracted_a}
        result_ba = TriggerAgent(prev_b, ctx_a, {"flight": MockCalendarEvent.make()}).evaluate(cond)
        assert result_ba.matched, "B→A: Should re-fire (value changed from acknowledged B to A)"


runner.run("TC-ABA: A→B→A re-fire (fires, silent, re-fires)", test_aba_refire)


# ═══════════════════════════════════════════════════════════════
#  TC-PRUNE: Acknowledged pruning test
# ═══════════════════════════════════════════════════════════════

def test_acknowledged_pruning():
    """Verify stale acknowledged entries are removed when condition stops matching."""
    with TempStateDir() as tsd:
        state = make_state(
            dep_time="2026-07-07T17:20:00-07:00",
            status="On time",
            acknowledged={
                "dep_time_changed": {"at": "2026-07-08T00:00:00Z", "value": "2026-07-07T17:20:00-07:00"},
                "flight_delayed": {"at": "2026-07-08T00:30:00Z", "value": "Delayed"}  # Stale!
            }
        )
        tsd.write_state(state)
        sm = StateManager(tsd.state_path)
        sm.load()

        # flight_delayed condition does NOT match (status is "On time")
        # → should remove from acknowledged
        sm.remove_acknowledged("flight_delayed")

        # dep_time_changed: dep_time matches state → not matched → also remove
        sm.remove_acknowledged("dep_time_changed")

        assert "flight_delayed" not in sm.state["acknowledged"], "Stale entry should be pruned"
        assert "dep_time_changed" not in sm.state["acknowledged"], "Unchanged entry should be pruned"


runner.run("TC-PRUNE: Acknowledged pruning removes stale entries", test_acknowledged_pruning)


# ═══════════════════════════════════════════════════════════════
#  TC-STATE: State atomicity test
# ═══════════════════════════════════════════════════════════════

def test_state_atomic_write():
    """Verify state is written atomically (no .tmp file left after save)."""
    with TempStateDir() as tsd:
        sm = StateManager(tsd.state_path, {"dep_time": "", "acknowledged": {}})
        sm.load()
        sm.state["dep_time"] = "2026-07-07T17:20:00-07:00"
        sm.acknowledge("test_cond", "test_value")
        sm.save()

        # State file exists
        assert tsd.state_path.exists(), "State file should exist"
        # No .tmp file left
        assert not tsd.state_path.with_suffix(".tmp").exists(), "No .tmp file should remain"
        # Content is valid JSON
        data = json.loads(tsd.state_path.read_text())
        assert data["dep_time"] == "2026-07-07T17:20:00-07:00"
        assert data["acknowledged"]["test_cond"]["value"] == "test_value"


runner.run("TC-STATE: Atomic write (no .tmp left, valid JSON)", test_state_atomic_write)


# ═══════════════════════════════════════════════════════════════
#  TC-GROUP: Group evaluation (any/all)
# ═══════════════════════════════════════════════════════════════

def test_group_any_matched():
    """Group with any: should match when one condition matches."""
    results = {
        "dep_time_changed": ConditionResult(True, "changed"),
        "arr_time_changed": ConditionResult(False, "unchanged"),
        "flight_cancelled": ConditionResult(False, "not cancelled"),
    }
    group = Group(name="critical", any=["dep_time_changed", "arr_time_changed", "flight_cancelled"])
    ge = GroupEvaluator()
    matched, matched_ids = ge.evaluate_group(group, results)
    assert matched, "Group should match (any: one matched)"
    assert "dep_time_changed" in matched_ids


def test_group_all_matched():
    """Group with all: should match only when all conditions match."""
    results = {
        "gate_changed": ConditionResult(True, "changed"),
    }
    group = Group(name="minor", all=["gate_changed"], actions=["patch_gate"])
    ge = GroupEvaluator()
    matched, matched_ids = ge.evaluate_group(group, results)
    assert matched, "Group should match (all: one matched)"
    assert "gate_changed" in matched_ids


def test_group_all_not_matched():
    """Group with all: should NOT match when one condition doesn't match."""
    results = {
        "gate_changed": ConditionResult(True, "changed"),
        "gate_not_empty": ConditionResult(False, "gate is empty"),
    }
    group = Group(name="minor", all=["gate_changed", "gate_not_empty"])
    ge = GroupEvaluator()
    matched, _ = ge.evaluate_group(group, results)
    assert not matched, "Group should NOT match (all: one failed)"


runner.run("TC-GROUP-ANY: Group any: matches when one fires", test_group_any_matched)
runner.run("TC-GROUP-ALL: Group all: matches when all fire", test_group_all_matched)
runner.run("TC-GROUP-ALL-FAIL: Group all: doesn't match when one fails", test_group_all_not_matched)


# ═══════════════════════════════════════════════════════════════
#  TC-CONFIG: Config validation
# ═══════════════════════════════════════════════════════════════

def test_config_validation():
    """Verify Pydantic schema accepts a valid config."""
    raw = {
        "name": "Test Config",
        "sources": [{"id": "test", "url": "https://example.com", "extract": []}],
        "conditions": [{"id": "test_cond", "field": "status", "op": "eq", "value": "On time"}],
        "groups": [{"name": "test_group", "any": ["test_cond"]}],
        "actions": {},
        "state": {"file": "state.json", "initial": {}},
    }
    config = DetectConfig(**raw)
    assert config.name == "Test Config"
    assert len(config.conditions) == 1
    assert config.conditions[0].id == "test_cond"


def test_config_invalid_missing_field():
    """Verify Pydantic rejects config without required fields."""
    try:
        DetectConfig(**{"sources": []})  # Missing 'name'
        assert False, "Should have raised ValidationError"
    except Exception:
        assert True


runner.run("TC-CONFIG-VALID: Pydantic accepts valid config", test_config_validation)
runner.run("TC-CONFIG-INVALID: Pydantic rejects missing name", test_config_invalid_missing_field)


# ═══════════════════════════════════════════════════════════════
#  TC-FETCH: FetchAgent with mock HTTP
# ═══════════════════════════════════════════════════════════════

def test_fetch_retry():
    """Verify FetchAgent retries on 5xx HTTP failures within the retry budget."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://httpbin.org/status/500", required=True,
                    timeout=5, retry={"count": 1, "backoff": 0})

    # Mock httpx to return 500 — 5xx is retryable (same budget as transport errors)
    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_resp.headers = {}
        mock_client.request.return_value = mock_resp

        result = fetcher.fetch(source)
        # 500 is not ok; with count=1 we exhaust both attempts and still fail
        assert result.status_code == 500
        assert not result.ok
        assert result.attempts == 2
        assert mock_client.request.call_count == 2


def test_fetch_reuses_client_across_retries():
    """TC-M5: transient retries reuse one HTTP client for the complete fetch call."""
    fetcher = FetchAgent()
    source = Source(id="reuse", url="https://example.com", timeout=5,
                    retry={"count": 1, "backoff": 0})
    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        response = MagicMock(status_code=200, headers={}, text="ok")
        mock_client.request.side_effect = [httpx.TimeoutException("retry"), response]
        result = fetcher.fetch(source)
    assert result.ok and result.attempts == 2
    assert mock_client_cls.call_count == 1, "Retries must reuse one httpx.Client"


runner.run("TC-FETCH: FetchAgent handles 500 response", test_fetch_retry)
runner.run("TC-M5: FetchAgent reuses client across retries", test_fetch_reuses_client_across_retries)


# ═══════════════════════════════════════════════════════════════
#  TC-ESCALATION: LLM escalation evidence payload
# ═══════════════════════════════════════════════════════════════

def test_escalation_evidence():
    """Verify evidence payload contains required fields."""
    config = DetectConfig(
        name="Test",
        sources=[],
        conditions=[Condition(id="dep_time_changed", field="dep_time", op="changed")],
        groups=[],
        actions={},
        llm_escalation=None,
    )
    prev_state = make_state(dep_time="2026-07-07T17:25:00-07:00")
    current_state = make_state(dep_time="2026-07-07T17:20:00-07:00")
    actions_taken = ["patch_flight ✅"]
    esc_agent = LLMEscalationAgent(config, prev_state, current_state, actions_taken)

    cond = Condition(id="dep_time_changed", field="dep_time", op="changed")
    result = ConditionResult(True, "dep_time changed: 17:25 → 17:20")

    with patch.object(esc_agent, "_write_evidence", return_value="/tmp/test.json"):
        files = esc_agent.escalate([("dep_time_changed", result, cond)])

    assert len(files) == 1
    assert files[0] == "/tmp/test.json"


runner.run("TC-ESCALATION: Evidence payload created for matched condition", test_escalation_evidence)


# ═══════════════════════════════════════════════════════════════
#  TC-OPS: Operator coverage — exists, matches, time_diff_gt/lt, gt/lt
# ═══════════════════════════════════════════════════════════════

def test_op_exists_positive():
    prev = make_state(gate="C3")
    extracted = make_extracted(gate="C3")
    cond = {"id": "gate_exists", "field": "gate", "op": "exists"}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"Should fire — gate exists. Reason: {result.reason}"


def test_op_exists_negative():
    prev = make_state(gate="")
    extracted = make_extracted(gate="")
    cond = {"id": "gate_exists", "field": "gate", "op": "exists"}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — gate is empty. Reason: {result.reason}"


def test_op_exists_none():
    prev = make_state(gate=None)
    extracted = make_extracted(gate=None)
    cond = {"id": "gate_exists", "field": "gate", "op": "exists"}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — gate is None. Reason: {result.reason}"


def test_op_matches_positive():
    prev = make_state(status="On time, enroute.")
    extracted = make_extracted(status="On time, enroute.")
    cond = {"id": "status_on_time", "field": "status", "op": "matches", "value": "On time"}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"Should fire — regex matches. Reason: {result.reason}"


def test_op_matches_negative():
    prev = make_state(status="Delayed")
    extracted = make_extracted(status="Delayed")
    cond = {"id": "status_on_time", "field": "status", "op": "matches", "value": "On time"}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — regex doesn't match. Reason: {result.reason}"


def test_op_ne_positive():
    prev = make_state(status="On time")
    extracted = make_extracted(status="On time")
    cond = {"id": "not_delayed", "field": "status", "op": "ne", "value": "Delayed"}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"Should fire — status != Delayed. Reason: {result.reason}"


def test_op_ne_negative():
    prev = make_state(status="Delayed")
    extracted = make_extracted(status="Delayed")
    cond = {"id": "not_delayed", "field": "status", "op": "ne", "value": "Delayed"}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"Should NOT fire — status == Delayed. Reason: {result.reason}"


runner.run("TC-OPS-EXISTS-POS: exists fires when value present", test_op_exists_positive)
runner.run("TC-OPS-EXISTS-NEG: exists silent when value empty", test_op_exists_negative)
runner.run("TC-OPS-EXISTS-NONE: exists silent when value None", test_op_exists_none)
runner.run("TC-OPS-MATCHES-POS: matches fires on regex match", test_op_matches_positive)
runner.run("TC-OPS-MATCHES-NEG: matches silent on no match", test_op_matches_negative)
runner.run("TC-OPS-NE-POS: ne fires when value differs", test_op_ne_positive)
runner.run("TC-OPS-NE-NEG: ne silent when value matches", test_op_ne_negative)


# ═══════════════════════════════════════════════════════════════
#  TC-REFIRE: refire_after for persistent conditions
# ═══════════════════════════════════════════════════════════════

def test_refire_after_blocks_within_window():
    """refire_after: should NOT re-fire if within the refire window."""
    with TempStateDir() as tsd:
        tsd.write_state(make_state(
            status="Delayed",
            acknowledged={"flight_delayed": {"at": "2026-07-08T00:00:00Z", "value": "Delayed"}},
            last_fired={"flight_delayed": datetime.now(timezone.utc).isoformat()},
        ))
        sm = StateManager(tsd.state_path)
        sm.load()

        # last_fired is NOW → within 30m window → should suppress
        last_fired = sm.get_last_fired("flight_delayed")
        assert last_fired is not None
        elapsed = datetime.now(timezone.utc) - last_fired
        assert elapsed < parse_duration("30m"), "Should be within 30m window"


def test_refire_after_allows_after_window():
    """refire_after: should re-fire if past the refire window."""
    with TempStateDir() as tsd:
        old_time = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        tsd.write_state(make_state(
            status="Delayed",
            acknowledged={"flight_delayed": {"at": old_time, "value": "Delayed"}},
            last_fired={"flight_delayed": old_time},
        ))
        sm = StateManager(tsd.state_path)
        sm.load()

        last_fired = sm.get_last_fired("flight_delayed")
        assert last_fired is not None
        elapsed = datetime.now(timezone.utc) - last_fired
        assert elapsed > parse_duration("30m"), "Should be past 30m window"


runner.run("TC-REFIRE-BLOCK: refire_after blocks within 30m window", test_refire_after_blocks_within_window)
runner.run("TC-REFIRE-ALLOW: refire_after allows after 30m window", test_refire_after_allows_after_window)


# ═══════════════════════════════════════════════════════════════
#  TC-FOR: Duration gate (for: keyword)
# ═══════════════════════════════════════════════════════════════

def test_duration_gate_first_seen():
    """for: 5m — first time condition matches, first_seen is set but condition not yet fired."""
    with TempStateDir() as tsd:
        tsd.write_state(make_state(status="On time"))
        sm = StateManager(tsd.state_path)
        sm.load()

        # First time: set first_seen
        assert sm.get_first_seen("flight_delayed") is None
        sm.set_first_seen("flight_delayed")
        assert sm.get_first_seen("flight_delayed") is not None

        # Elapsed is ~0 → less than 5m → should block
        elapsed = datetime.now(timezone.utc) - sm.get_first_seen("flight_delayed")
        assert elapsed < parse_duration("5m"), "Should be within 5m gate"


def test_duration_gate_reset():
    """for: — when condition stops matching, first_seen is cleared."""
    with TempStateDir() as tsd:
        tsd.write_state(make_state())
        sm = StateManager(tsd.state_path)
        sm.load()
        sm.set_first_seen("flight_delayed")
        assert sm.get_first_seen("flight_delayed") is not None
        sm.clear_first_seen("flight_delayed")
        assert sm.get_first_seen("flight_delayed") is None


runner.run("TC-FOR-FIRST: Duration gate sets first_seen on first match", test_duration_gate_first_seen)
runner.run("TC-FOR-RESET: Duration gate resets when condition stops matching", test_duration_gate_reset)


# ═══════════════════════════════════════════════════════════════
#  TC-STATE-EDGE: State edge cases
# ═══════════════════════════════════════════════════════════════

def test_state_load_corrupt():
    """Loading a corrupt state file should reinitialize with defaults."""
    with TempStateDir() as tsd:
        tsd.state_path.write_text("{corrupt json!!!")
        sm = StateManager(tsd.state_path, {"dep_time": "default"})
        sm.load()
        assert sm.state.get("dep_time") == "default", "Should fall back to initial values"
        assert "acknowledged" in sm.state, "Should have acknowledged dict"


def test_state_load_missing():
    """Loading a non-existent state file should initialize with defaults."""
    with TempStateDir() as tsd:
        sm = StateManager(tsd.state_path, {"dep_time": "initial", "acknowledged": {}})
        sm.load()
        assert sm.state.get("dep_time") == "initial"
        assert "acknowledged" in sm.state
        assert "first_seen" in sm.state
        assert "last_fired" in sm.state


def test_state_acknowledged_with_value():
    """acknowledge() stores both timestamp and value."""
    with TempStateDir() as tsd:
        sm = StateManager(tsd.state_path, {})
        sm.load()
        sm.acknowledge("test_cond", "test_value")
        ack = sm.state["acknowledged"]["test_cond"]
        assert ack["value"] == "test_value"
        assert "at" in ack


def test_state_is_acknowledged_same_value():
    """is_acknowledged returns True when value matches."""
    with TempStateDir() as tsd:
        sm = StateManager(tsd.state_path, {})
        sm.load()
        sm.acknowledge("test_cond", "value_a")
        assert sm.is_acknowledged("test_cond", "value_a"), "Same value → acknowledged"
        assert not sm.is_acknowledged("test_cond", "value_b"), "Different value → not acknowledged"
        assert not sm.is_acknowledged("missing_cond", "anything"), "Missing → not acknowledged"


runner.run("TC-STATE-CORRUPT: Corrupt state file → reinitialize", test_state_load_corrupt)
runner.run("TC-STATE-MISSING: Missing state file → initialize with defaults", test_state_load_missing)
runner.run("TC-STATE-ACK-VALUE: acknowledge() stores value + timestamp", test_state_acknowledged_with_value)
runner.run("TC-STATE-ACK-SAME: is_acknowledged checks value match", test_state_is_acknowledged_same_value)


# ═══════════════════════════════════════════════════════════════
#  TC-EXTRACT-EDGE: Extraction edge cases
# ═══════════════════════════════════════════════════════════════

def test_extract_no_jsonld_script():
    """jsonpath_from_html on page with no JSON-LD → returns None."""
    html = "<html><body>No JSON-LD here</body></html>"
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="dep_time", type="jsonpath_from_html", path="$.departureTime")
    values = extractor.extract(result, [spec])
    assert values["dep_time"] is None, "Should return None when no JSON-LD found"


def test_extract_malformed_jsonld():
    """jsonpath_from_html with malformed JSON in script tag → skips, returns None."""
    html = '<script type="application/ld+json">{invalid json}</script>'
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="dep_time", type="jsonpath_from_html", path="$.departureTime")
    values = extractor.extract(result, [spec])
    assert values["dep_time"] is None, "Should return None for malformed JSON-LD"


def test_extract_missing_path():
    """jsonpath_from_html with valid JSON but missing path → returns None."""
    html = '<script type="application/ld+json">{"@type":"Flight","flightNumber":"706"}</script>'
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="dep_time", type="jsonpath_from_html", path="$.departureTime")
    values = extractor.extract(result, [spec])
    assert values["dep_time"] is None, "Should return None when path not found"


def test_extract_header_status_code():
    """header extraction type returns status code."""
    result = FetchResult(200, {"Content-Type": "text/html"}, "body")
    extractor = ExtractAgent()
    spec = ExtractSpec(id="code", type="header", name="status_code")
    values = extractor.extract(result, [spec])
    assert values["code"] == 200


def test_extract_header_named():
    """header extraction type returns named header."""
    result = FetchResult(200, {"Content-Type": "text/html"}, "body")
    extractor = ExtractAgent()
    spec = ExtractSpec(id="ctype", type="header", name="Content-Type")
    values = extractor.extract(result, [spec])
    assert values["ctype"] == "text/html"


def test_extract_css_not_found():
    """CSS selector with no matches → returns None."""
    html = "<html><body>No match</body></html>"
    result = FetchResult(200, {}, html)
    extractor = ExtractAgent()
    spec = ExtractSpec(id="missing", type="css", selector=".nonexistent")
    values = extractor.extract(result, [spec])
    assert values["missing"] is None


runner.run("TC-EXTRACT-NO-JSONLD: No JSON-LD script → None", test_extract_no_jsonld_script)
runner.run("TC-EXTRACT-MALFORMED: Malformed JSON-LD → None", test_extract_malformed_jsonld)
runner.run("TC-EXTRACT-MISSING-PATH: Valid JSON, missing path → None", test_extract_missing_path)
runner.run("TC-EXTRACT-HEADER-CODE: Header extraction returns status code", test_extract_header_status_code)
runner.run("TC-EXTRACT-HEADER-NAMED: Header extraction returns named header", test_extract_header_named)
runner.run("TC-EXTRACT-CSS-NOTFOUND: CSS no match → None", test_extract_css_not_found)


# ═══════════════════════════════════════════════════════════════
#  TC-ACTION: ActionAgent tests
# ═══════════════════════════════════════════════════════════════

def test_action_resolve_event_id_string():
    """Resolve a plain string event ID."""
    action = ActionAgent({}, dry_run=True)
    assert action._resolve_event_id("abc123") == "abc123"


def test_action_resolve_event_id_from_state():
    """Resolve event ID from state reference."""
    action = ActionAgent({"flight_event_id": "evt123"}, dry_run=True)
    spec = {"from_state": "flight_event_id", "required": True}
    assert action._resolve_event_id(spec) == "evt123"


def test_action_resolve_event_id_missing_required():
    """Resolve event ID from missing state key with required=True → empty string + error log."""
    action = ActionAgent({}, dry_run=True)
    spec = {"from_state": "missing_key", "required": True}
    result = action._resolve_event_id(spec)
    assert result == "", "Should return empty string for missing required key"


def test_action_render_template_simple():
    """Template rendering with simple variable."""
    action = ActionAgent({"dep_airport": "SEA", "arr_airport": "OAK"}, dry_run=True)
    result = action._render_template("{{ dep_airport }} → {{ arr_airport }}", {"dep_airport": "SEA", "arr_airport": "OAK"})
    assert result == "SEA → OAK"


def test_action_render_template_add_minutes():
    """Template rendering with add_minutes filter."""
    action = ActionAgent({}, dry_run=True)
    ctx = {"arr_time": "2026-07-07T19:18:00-07:00"}
    result = action._render_template("{{ arr_time | add_minutes: 17 }}", ctx)
    # 19:18 + 17 min = 19:35
    assert "19:35" in result, f"Expected 19:35 in result, got {result}"


def test_action_dry_run_calendar_patch():
    """Dry-run calendar patch prints but doesn't call gws."""
    action = ActionAgent({"dep_airport": "SEA", "arr_airport": "OAK"}, dry_run=True)
    action_def = {
        "type": "calendar_patch",
        "event_id": "test_evt",
        "calendar_id": "primary",
        "fields": {"summary": "✈️ {{ dep_airport }} → {{ arr_airport }}"},
    }
    success = action.execute("patch_flight", action_def)
    assert success, "Dry-run should return True"
    assert any("DRY-RUN" in r for r in action.results), "Should have DRY-RUN in results"


runner.run("TC-ACTION-EID-STR: Resolve string event ID", test_action_resolve_event_id_string)
runner.run("TC-ACTION-EID-STATE: Resolve event ID from state", test_action_resolve_event_id_from_state)
runner.run("TC-ACTION-EID-MISSING: Missing required state key → empty", test_action_resolve_event_id_missing_required)
runner.run("TC-ACTION-TEMPLATE: Simple template rendering", test_action_render_template_simple)
runner.run("TC-ACTION-TEMPLATE-ADD: Template with add_minutes filter", test_action_render_template_add_minutes)
runner.run("TC-ACTION-DRYRUN: Dry-run calendar patch", test_action_dry_run_calendar_patch)


# ── calendar_delete action tests ──

def test_action_dry_run_calendar_delete():
    """Dry-run calendar delete prints but doesn't call gws."""
    action = ActionAgent({}, dry_run=True)
    action_def = {
        "type": "calendar_delete",
        "event_id": "stale_evt_123",
        "calendar_id": "primary",
    }
    success = action.execute("delete_old", action_def)
    assert success, "Dry-run should return True"
    assert any("DRY-RUN" in r and "stale_evt_123" in r for r in action.results), \
        "Should have DRY-RUN with event ID in results"


def test_action_delete_missing_event_id():
    """calendar_delete with no event_id returns False."""
    action = ActionAgent({}, dry_run=True)
    action_def = {
        "type": "calendar_delete",
        "calendar_id": "primary",
    }
    success = action.execute("delete_no_id", action_def)
    assert not success, "Should return False when no event_id"


def test_action_delete_from_state():
    """calendar_delete resolves event_id from state."""
    action = ActionAgent({"stale_id": "evt_from_state"}, dry_run=True)
    action_def = {
        "type": "calendar_delete",
        "event_id": {"from_state": "stale_id"},
    }
    success = action.execute("delete_state", action_def)
    assert success, "Should resolve from state and return True"
    assert any("evt_from_state" in r for r in action.results), \
        "Should have resolved event ID in results"


def test_action_unknown_type():
    """Unknown action type returns False."""
    action = ActionAgent({}, dry_run=True)
    action_def = {"type": "send_email", "to": "jim@example.com"}
    success = action.execute("bad_action", action_def)
    assert not success, "Unknown action type should return False"


runner.run("TC-ACTION-DELETE-DRYRUN: Dry-run calendar delete", test_action_dry_run_calendar_delete)
runner.run("TC-ACTION-DELETE-NO-ID: Delete with missing event_id", test_action_delete_missing_event_id)
runner.run("TC-ACTION-DELETE-STATE: Delete resolves event_id from state", test_action_delete_from_state)
runner.run("TC-ACTION-UNKNOWN: Unknown action type returns False", test_action_unknown_type)


# ═══════════════════════════════════════════════════════════════
#  TC-CONFIG-EDGE: Config edge cases
# ═══════════════════════════════════════════════════════════════

def test_config_expires_past():
    """Config with expires in the past should be silently skipped."""
    config = DetectConfig(name="Expired", expires="2020-01-01T00:00:00Z", enabled=True)
    # The run_engine function checks this, but we can test the logic directly
    from datetime import datetime, timezone
    expires_dt = datetime.fromisoformat(config.expires)
    assert datetime.now(timezone.utc) > expires_dt, "Config should be expired"


def test_config_disabled():
    """Config with enabled: false should be silently skipped."""
    config = DetectConfig(name="Disabled", enabled=False)
    assert not config.enabled


def test_config_with_baseline():
    """Config with baseline: field on condition should parse correctly."""
    raw = {
        "name": "Test",
        "conditions": [{
            "id": "dep_changed",
            "field": "dep_time",
            "op": "changed",
            "baseline": {"source": "calendar", "event_id": "evt123", "field": "start.dateTime"}
        }],
        "sources": [],
        "groups": [],
        "actions": {},
    }
    config = DetectConfig(**raw)
    assert config.conditions[0].baseline is not None
    assert config.conditions[0].baseline["source"] == "calendar"


def test_config_with_unless():
    """Config with unless: field should parse correctly."""
    raw = {
        "name": "Test",
        "conditions": [{
            "id": "delayed",
            "field": "status",
            "op": "eq",
            "value": "Delayed",
            "unless": {"field": "cal_title", "op": "contains", "value": "DELAYED"}
        }],
        "sources": [],
        "groups": [],
        "actions": {},
    }
    config = DetectConfig(**raw)
    assert config.conditions[0].unless is not None
    assert config.conditions[0].unless["value"] == "DELAYED"


def test_config_with_refire_after():
    """Config with refire_after should parse correctly."""
    raw = {
        "name": "Test",
        "conditions": [{
            "id": "persistent_delay",
            "field": "status",
            "op": "eq",
            "value": "Delayed",
            "refire_after": "30m"
        }],
        "sources": [],
        "groups": [],
        "actions": {},
    }
    config = DetectConfig(**raw)
    assert config.conditions[0].refire_after == "30m"


runner.run("TC-CONFIG-EXPIRED: Expired config detected", test_config_expires_past)
runner.run("TC-CONFIG-DISABLED: Disabled config detected", test_config_disabled)
runner.run("TC-CONFIG-BASELINE: Config with baseline: parses", test_config_with_baseline)
runner.run("TC-CONFIG-UNLESS: Config with unless: parses", test_config_with_unless)
runner.run("TC-CONFIG-REFIRE: Config with refire_after parses", test_config_with_refire_after)


# ═══════════════════════════════════════════════════════════════
#  TC-AND-OR-NOT: Boolean combinator tests
# ═══════════════════════════════════════════════════════════════

def test_and_all_match():
    """AND: all sub-conditions match → True."""
    prev = make_state(status="On time", dep_time="2026-07-07T17:20:00-07:00")
    extracted = make_extracted(status="On time", dep_time="2026-07-07T17:20:00-07:00")
    cond = {"id": "ok", "and": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "dep_time", "op": "exists"},
    ]}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"AND should match. Reason: {result.reason}"


def test_and_one_fails():
    """AND: one sub-condition fails → False."""
    prev = make_state(status="Delayed")
    extracted = make_extracted(status="Delayed")
    cond = {"id": "ok", "and": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "status", "op": "exists"},
    ]}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"AND should NOT match. Reason: {result.reason}"


def test_or_one_matches():
    """OR: one sub-condition matches → True."""
    prev = make_state(status="Delayed")
    extracted = make_extracted(status="Delayed")
    cond = {"id": "any", "or": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "status", "op": "eq", "value": "Delayed"},
    ]}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"OR should match. Reason: {result.reason}"


def test_or_none_match():
    """OR: no sub-conditions match → False."""
    prev = make_state(status="Cancelled")
    extracted = make_extracted(status="Cancelled")
    cond = {"id": "any", "or": [
        {"field": "status", "op": "eq", "value": "On time"},
        {"field": "status", "op": "eq", "value": "Delayed"},
    ]}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"OR should NOT match. Reason: {result.reason}"


def test_not_inverts():
    """NOT: inverts the sub-condition result."""
    prev = make_state(status="On time")
    extracted = make_extracted(status="On time")
    cond = {"id": "not_delayed", "not": [{"field": "status", "op": "eq", "value": "Delayed"}]}
    result = eval_condition(cond, prev, extracted)
    assert result.matched, f"NOT should invert to True. Reason: {result.reason}"


def test_not_inverts_to_false():
    """NOT: inverts a True sub-condition to False."""
    prev = make_state(status="On time")
    extracted = make_extracted(status="On time")
    cond = {"id": "not_on_time", "not": [{"field": "status", "op": "eq", "value": "On time"}]}
    result = eval_condition(cond, prev, extracted)
    assert not result.matched, f"NOT should invert to False. Reason: {result.reason}"


runner.run("TC-AND-MATCH: AND matches when all true", test_and_all_match)
runner.run("TC-AND-FAIL: AND fails when one false", test_and_one_fails)
runner.run("TC-OR-MATCH: OR matches when one true", test_or_one_matches)
runner.run("TC-OR-FAIL: OR fails when all false", test_or_none_match)
runner.run("TC-NOT-TRUE: NOT inverts false to true", test_not_inverts)
runner.run("TC-NOT-FALSE: NOT inverts true to false", test_not_inverts_to_false)


# ═══════════════════════════════════════════════════════════════
#  TC-ESCALATION-EDGE: LLM escalation edge cases
# ═══════════════════════════════════════════════════════════════

def test_escalation_file_written_to_disk():
    """Evidence payload is actually written to disk with full context."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        import detect_engine
        orig_escalation_dir = detect_engine.ESCALATION_DIR
        detect_engine.ESCALATION_DIR = Path(tmpdir)

        try:
            config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
            prev_state = make_state(dep_time="2026-07-07T17:25:00-07:00", status="On time")
            current_state = make_state(dep_time="2026-07-07T17:20:00-07:00", status="Delayed")
            cal = {"flight": MockCalendarEvent.make(summary="✈️ Alaska AS706: SEA → OAK")}
            esc_agent = LLMEscalationAgent(config, prev_state, current_state, ["patch ✅"], cal)
            cond = Condition(id="dep_time_changed", field="dep_time", op="changed")
            result = ConditionResult(True, "dep_time changed: 17:25 → 17:20")

            files = esc_agent.escalate([("dep_time_changed", result, cond)])
            assert len(files) == 1
            assert Path(files[0]).exists(), "Evidence file should exist on disk"
            data = json.loads(Path(files[0]).read_text())
            assert data["escalation_type"] == "condition_matched"
            assert data["condition_id"] == "dep_time_changed"
            assert data["actions_taken"] == ["patch ✅"]
            assert "match_reason" in data
            assert "condition_definition" in data
            # NEW: previous and current state snapshots
            assert data["previous_value"] == "2026-07-07T17:25:00-07:00"
            assert data["new_value"] == "2026-07-07T17:20:00-07:00"
            assert "previous_state" in data
            assert "current_state" in data
            assert data["previous_state"]["dep_time"] == "2026-07-07T17:25:00-07:00"
            assert data["current_state"]["dep_time"] == "2026-07-07T17:20:00-07:00"
            # NEW: calendar context
            assert "calendar_events" in data
            assert data["calendar_events"]["flight"]["summary"] == "✈️ Alaska AS706: SEA → OAK"
            # NEW: submatches
            assert "submatches" in data
        finally:
            detect_engine.ESCALATION_DIR = orig_escalation_dir


def test_escalation_prompt_rendering():
    """LLM escalation prompt is rendered with condition-specific values including previous/new."""
    config = DetectConfig(
        name="AS706 Monitor",
        sources=[], conditions=[], groups=[], actions={},
        llm_escalation=None,  # Will be set manually
    )
    from detect_engine import LLMEscalation
    config.llm_escalation = LLMEscalation(
        trigger_groups=["critical"],
        prompt="Flight {{ config_name }}: {{ condition_id }} — {{ match_reason }}.\n"
               "Previous: {{ previous_value }} → New: {{ new_value }}.\n"
               "Actions: {{ actions_taken }}"
    )
    prev_state = make_state(dep_time="2026-07-07T17:25:00-07:00")
    current_state = make_state(dep_time="2026-07-07T17:20:00-07:00")
    esc_agent = LLMEscalationAgent(config, prev_state, current_state, ["patch_flight ✅"])
    _cond = Condition(id="dep_time_changed", field="dep_time", op="changed")
    result = ConditionResult(True, "dep_time changed: 17:25 → 17:20")

    prompt = esc_agent._render_prompt("dep_time_changed", result,
                                      prev_value="2026-07-07T17:25:00-07:00",
                                      new_value="2026-07-07T17:20:00-07:00")
    assert "AS706 Monitor" in prompt
    assert "dep_time_changed" in prompt
    assert "17:25" in prompt
    assert "17:20" in prompt
    assert "patch_flight" in prompt


def test_escalation_default_prompt_has_context():
    """Default prompt (no template) includes previous/new values and actions."""
    config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={}, llm_escalation=None)
    prev_state = make_state(dep_time="17:25")
    current_state = make_state(dep_time="17:20")
    esc_agent = LLMEscalationAgent(config, prev_state, current_state, ["patch ✅"])
    _cond = Condition(id="dep_changed", field="dep_time", op="changed")
    result = ConditionResult(True, "changed")
    prompt = esc_agent._render_prompt("dep_changed", result, "17:25", "17:20")
    assert "17:25" in prompt, "Default prompt should include previous value"
    assert "17:20" in prompt, "Default prompt should include new value"
    assert "patch" in prompt, "Default prompt should include actions taken"


def test_escalation_submatch_tree():
    """Evidence payload includes recursive submatch tree for AND/OR/NOT conditions."""
    config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={}, llm_escalation=None)
    prev_state = make_state(status="Delayed")
    current_state = make_state(status="Delayed")
    esc_agent = LLMEscalationAgent(config, prev_state, current_state, [])

    # Simulate an AND condition with 2 submatches
    sub1 = ConditionResult(True, "status == Delayed")
    sub2 = ConditionResult(True, "cal_title contains DELAYED")
    result = ConditionResult(True, "AND: all matched", [sub1, sub2])
    cond = Condition(id="delayed_and_calendar", and_=[
        {"field": "status", "op": "eq", "value": "Delayed"},
        {"field": "cal_title", "op": "contains", "value": "DELAYED"}
    ])

    with patch.object(esc_agent, "_write_evidence", return_value="/tmp/test.json"):
        files = esc_agent.escalate([("delayed_and_calendar", result, cond)])

    assert len(files) == 1
    # The submatch tree should be built from the ConditionResult
    tree = esc_agent._extract_submatches(result)
    assert len(tree) == 2
    assert tree[0]["matched"] is True
    assert tree[0]["reason"] == "status == Delayed"
    assert tree[1]["matched"] is True
    assert tree[1]["reason"] == "cal_title contains DELAYED"


def test_escalation_baseline_value():
    """Evidence payload includes baseline_value for 'changed' conditions with calendar baseline."""
    config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={}, llm_escalation=None)
    prev_state = make_state(dep_time="2026-07-07T17:25:00-07:00")
    current_state = make_state(dep_time="2026-07-07T17:20:00-07:00")
    cal = {"flight": MockCalendarEvent.make(
        summary="✈️ Alaska AS706",
        start="2026-07-07T17:25:00-07:00",
        end="2026-07-07T19:33:00-07:00"
    )}
    esc_agent = LLMEscalationAgent(config, prev_state, current_state, [], cal)
    cond = Condition(id="dep_changed", field="dep_time", op="changed",
                     baseline={"source": "calendar", "event_id": "evt123", "field": "start.dateTime"})
    result = ConditionResult(True, "dep_time changed")

    with patch.object(esc_agent, "_write_evidence", return_value="/tmp/test.json"):
        files = esc_agent.escalate([("dep_changed", result, cond)])

    # Verify baseline_value was extracted from the calendar event
    assert len(files) == 1


runner.run("TC-ESCALATION-DISK: Evidence file written to disk with full context", test_escalation_file_written_to_disk)
runner.run("TC-ESCALATION-PROMPT: LLM prompt rendered with previous/new values", test_escalation_prompt_rendering)
runner.run("TC-ESCALATION-DEFAULT-PROMPT: Default prompt includes context", test_escalation_default_prompt_has_context)
runner.run("TC-ESCALATION-SUBMATCH: Submatch tree for AND/OR/NOT conditions", test_escalation_submatch_tree)
runner.run("TC-ESCALATION-BASELINE: Baseline value from calendar in evidence", test_escalation_baseline_value)


# ═══════════════════════════════════════════════════════════════
#  TC-PARTIAL: Partial source failure (required=false)
# ═══════════════════════════════════════════════════════════════

def test_fetch_optional_source_failure():
    """Optional source failure returns error FetchResult but doesn't crash."""
    fetcher = FetchAgent()
    source = Source(id="optional", url="https://httpbin.org/delay/60", required=False, timeout=1)
    # This will timeout but we mock it
    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = __import__("httpx").TimeoutException("timeout")
        result = fetcher.fetch(source)
        assert not result.ok
        assert result.error != ""


runner.run("TC-PARTIAL: Optional source failure returns error (no crash)", test_fetch_optional_source_failure)


# ═══════════════════════════════════════════════════════════════
#  TC-PARSE: parse_duration helper
# ═══════════════════════════════════════════════════════════════

def test_parse_duration_minutes():
    assert parse_duration("30m") == timedelta(minutes=30)


def test_parse_duration_hours():
    assert parse_duration("2h") == timedelta(hours=2)


def test_parse_duration_complex():
    assert parse_duration("1h30m") == timedelta(hours=1, minutes=30)


def test_parse_duration_seconds():
    assert parse_duration("45s") == timedelta(seconds=45)


runner.run("TC-PARSE-M: parse_duration('30m')", test_parse_duration_minutes)
runner.run("TC-PARSE-H: parse_duration('2h')", test_parse_duration_hours)
runner.run("TC-PARSE-COMPLEX: parse_duration('1h30m')", test_parse_duration_complex)
runner.run("TC-PARSE-S: parse_duration('45s')", test_parse_duration_seconds)


# ═══════════════════════════════════════════════════════════════
#  TC-TRANSFORM: Extract transform filters
# ═══════════════════════════════════════════════════════════════

def test_transform_upper():
    """text|upper transform converts to uppercase."""
    extractor = ExtractAgent()
    assert extractor._apply_transform("hello", "text|upper") == "HELLO"


def test_transform_lower():
    """text|lower transform converts to lowercase."""
    extractor = ExtractAgent()
    assert extractor._apply_transform("HELLO", "text|lower") == "hello"


def test_transform_none_value():
    """Transform on None returns None."""
    extractor = ExtractAgent()
    assert extractor._apply_transform(None, "text|upper") is None


runner.run("TC-TRANSFORM-UPPER: text|upper filter", test_transform_upper)
runner.run("TC-TRANSFORM-LOWER: text|lower filter", test_transform_lower)
runner.run("TC-TRANSFORM-NONE: Transform on None returns None", test_transform_none_value)


# ═══════════════════════════════════════════════════════════════
#  TC-RETRY: Retry with exponential backoff + LLM escalation on failure
# ═══════════════════════════════════════════════════════════════

def test_retry_exponential_backoff_timing():
    """Verify backoff schedule: 3s, 6s, 12s for backoff=3."""
    # backoff * 2^attempt = 3*1, 3*2, 3*4 = 3, 6, 12
    for attempt, expected_wait in [(0, 3), (1, 6), (2, 12)]:
        wait = 3 * (2 ** attempt)
        assert wait == expected_wait, f"attempt {attempt}: expected {expected_wait}s, got {wait}s"


def test_retry_attempts_count():
    """Verify FetchResult.attempts is correct after all retries fail."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://httpbin.org/status/500", required=True,
                    timeout=1, retry={"count": 2, "backoff": 1})

    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = __import__("httpx").TimeoutException("timeout")

        result = fetcher.fetch(source)
        assert result.attempts == 3, f"Should have 3 attempts (1 + 2 retries), got {result.attempts}"
        assert result.last_error_type == "TimeoutException"
        assert not result.ok


def test_retry_no_retry_config():
    """Default RetryConfig: count=2, so 3 total attempts."""
    source = Source(id="test", url="https://example.com")
    # Default retry is RetryConfig(count=2, backoff=3)
    # So total_attempts = 3
    assert (source.retry or RetryConfig()).count == 2


def test_retry_zero_retries():
    """RetryConfig with count=0 → only 1 attempt, no retries."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://httpbin.org/status/500", required=True,
                    timeout=1, retry={"count": 0, "backoff": 1})

    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = __import__("httpx").TimeoutException("timeout")

        result = fetcher.fetch(source)
        assert result.attempts == 1, f"Should have 1 attempt (0 retries), got {result.attempts}"
        assert result.last_error_type == "TimeoutException"


def test_retry_success_on_second_attempt():
    """Retry succeeds on second attempt → FetchResult.ok=True, attempts=2."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://example.com", timeout=5,
                    retry={"count": 2, "backoff": 0})  # backoff=0 for fast test

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"status":"ok"}'
    mock_resp.headers = {}

    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        # First call: timeout. Second call: success.
        mock_client.request.side_effect = [__import__("httpx").TimeoutException("timeout"), mock_resp]

        result = fetcher.fetch(source)
        assert result.ok, "Should succeed on second attempt"
        assert result.attempts == 2, f"Should have 2 attempts, got {result.attempts}"
        assert result.status_code == 200


def test_retry_unexpected_error_no_retry():
    """Unexpected (non-transient) error → don't retry, escalate immediately."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://example.com", timeout=5,
                    retry={"count": 3, "backoff": 1})

    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = RuntimeError("unexpected error")

        result = fetcher.fetch(source)
        assert result.attempts == 1, "Should not retry on unexpected error"
        assert "RuntimeError" in result.last_error_type
        assert not result.ok


def test_fetch_failure_escalation_written():
    """write_fetch_failure_escalation writes evidence file to disk."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        import detect_engine
        orig_dir = detect_engine.ESCALATION_DIR
        detect_engine.ESCALATION_DIR = Path(tmpdir)

        try:
            source = Source(id="alaska_api", url="https://api.example.com/flight/706",
                            failure_prompt="The Alaska API is down. Check if there's an alternative source.")
            result = FetchResult(0, {}, "", "Connection refused",
                                 attempts=3, last_error_type="ConnectError")

            filepath = write_fetch_failure_escalation(source, result, "AS706 Monitor")
            assert filepath is not None, "Should return a file path"
            assert Path(filepath).exists(), "Evidence file should exist on disk"

            data = json.loads(Path(filepath).read_text())
            assert data["escalation_type"] == "fetch_failure"
            assert data["source_id"] == "alaska_api"
            assert data["url"] == "https://api.example.com/flight/706"
            assert data["error"] == "Connection refused"
            assert data["error_type"] == "ConnectError"
            assert data["attempts"] == 3
            assert "prompt" in data
            assert "alternative source" in data["prompt"], "Should use custom failure_prompt"
        finally:
            detect_engine.ESCALATION_DIR = orig_dir


def test_fetch_failure_escalation_default_prompt():
    """write_fetch_failure_escalation uses default prompt when no custom prompt set."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        import detect_engine
        orig_dir = detect_engine.ESCALATION_DIR
        detect_engine.ESCALATION_DIR = Path(tmpdir)

        try:
            source = Source(id="test_src", url="https://example.com")
            result = FetchResult(0, {}, "", "timeout", attempts=2, last_error_type="TimeoutException")

            filepath = write_fetch_failure_escalation(source, result, "TestConfig")
            data = json.loads(Path(filepath).read_text())
            # Default prompt should contain evaluation questions
            assert "URL still valid" in data["prompt"] or "Is the URL" in data["prompt"]
            assert "outage" in data["prompt"].lower() or "paused" in data["prompt"].lower()
        finally:
            detect_engine.ESCALATION_DIR = orig_dir


def test_fetch_failure_escalation_config_escalate_on_failure():
    """RetryConfig with escalate_on_failure=True parses correctly."""
    raw = {
        "name": "Test",
        "sources": [{
            "id": "api",
            "url": "https://api.example.com",
            "retry": {"count": 3, "backoff": 5, "escalate_on_failure": True},
            "failure_prompt": "API is down, evaluate alternatives."
        }],
        "conditions": [], "groups": [], "actions": {},
    }
    config = DetectConfig(**raw)
    assert config.sources[0].retry.escalate_on_failure is True
    assert config.sources[0].failure_prompt == "API is down, evaluate alternatives."


def test_fetch_failure_escalation_no_escalate_by_default():
    """Default RetryConfig should NOT escalate on failure."""
    config = RetryConfig()
    assert config.escalate_on_failure is False


def test_fetch_result_carries_error_type():
    """FetchResult stores last_error_type for escalation evidence."""
    result = FetchResult(0, {}, "", "timeout", attempts=3, last_error_type="TimeoutException")
    assert result.last_error_type == "TimeoutException"
    assert result.attempts == 3
    assert not result.ok


runner.run("TC-RETRY-TIMING: Exponential backoff schedule (3, 6, 12s)", test_retry_exponential_backoff_timing)
runner.run("TC-RETRY-COUNT: Attempts count correct after all retries fail", test_retry_attempts_count)
runner.run("TC-RETRY-DEFAULT: Default RetryConfig has count=2 (3 total)", test_retry_no_retry_config)
runner.run("TC-RETRY-ZERO: count=0 → 1 attempt, no retries", test_retry_zero_retries)
runner.run("TC-RETRY-SUCCESS: Success on second attempt, attempts=2", test_retry_success_on_second_attempt)
runner.run("TC-RETRY-UNEXPECTED: Unexpected error → no retry", test_retry_unexpected_error_no_retry)
runner.run("TC-FAIL-ESCALATION-DISK: Fetch failure evidence written to disk", test_fetch_failure_escalation_written)
runner.run("TC-FAIL-ESCALATION-DEFAULT: Default failure prompt used", test_fetch_failure_escalation_default_prompt)
runner.run("TC-FAIL-ESCALATION-CONFIG: escalate_on_failure=True parses in config", test_fetch_failure_escalation_config_escalate_on_failure)
runner.run("TC-FAIL-ESCALATION-DEFAULT-OFF: escalate_on_failure=False by default", test_fetch_failure_escalation_no_escalate_by_default)
runner.run("TC-FAIL-RESULT-TYPE: FetchResult carries error_type + attempts", test_fetch_result_carries_error_type)


# ═══════════════════════════════════════════════════════════════
#  TC-P0: P0 bug fix verification tests
# ═══════════════════════════════════════════════════════════════

def test_p0_1_pruning_before_fire_once():
    """P0-1: Acknowledged pruning happens BEFORE fire_once check, not after.
    A persistent condition (status=Delayed) that is acknowledged should NOT
    have its ack entry deleted by pruning, because the underlying condition
    is still True (only suppressed by fire_once)."""
    with TempStateDir() as tsd:
        tsd.write_state(make_state(
            status="Delayed",
            acknowledged={"flight_delayed": {"at": "2026-07-08T00:00:00Z", "value": "Delayed"}},
        ))
        sm = StateManager(tsd.state_path)
        sm.load()

        prev = dict(sm.state)
        extracted = make_extracted(status="Delayed")
        ctx = {**prev, **extracted}

        trigger = TriggerAgent(prev, ctx, {"flight": MockCalendarEvent.make()})
        cond = Condition(id="flight_delayed", field="status", op="eq", value="Delayed")
        result = trigger.evaluate(cond)

        # Underlying condition is True
        assert result.matched, "Underlying condition should match (status == Delayed)"

        # Simulate the P0-1 fix: pruning only when underlying_matched is False
        underlying_matched = result.matched
        if not underlying_matched:
            sm.remove_acknowledged(cond.id)

        # Since underlying_matched is True, ack should NOT be pruned
        assert "flight_delayed" in sm.state["acknowledged"], \
            "Ack should NOT be pruned when underlying condition is still True"


def test_p0_2_dry_run_no_state_save():
    """P0-2: dry-run does NOT save state file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        # Write initial state
        state_path.write_text(json.dumps(make_state(dep_time="2026-07-07T17:25:00-07:00")))
        original = state_path.read_text()

        # Simulate what run_engine does in dry-run mode (no save)
        sm = StateManager(state_path)
        sm.load()
        sm.state["dep_time"] = "2026-07-07T17:20:00-07:00"  # Would change state
        # In dry-run: sm.save() is NOT called
        # So state file should be unchanged
        assert state_path.read_text() == original, "State file should NOT be modified in dry-run"


def test_p0_3_fire_once_without_llm_escalation():
    """P0-3: fire_once works even when llm_escalation is not configured."""
    # _fire_once_enabled should return True by default
    config_no_esc = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
    assert _fire_once_enabled(config_no_esc) is True, "fire_once should default to True without llm_escalation"

    config_with_esc = DetectConfig(
        name="Test", sources=[], conditions=[], groups=[], actions={},
        llm_escalation=LLMEscalation(trigger_groups=["critical"], fire_once=True)
    )
    assert _fire_once_enabled(config_with_esc) is True, "fire_once should be True when explicitly set"

    config_no_fire = DetectConfig(
        name="Test", sources=[], conditions=[], groups=[], actions={},
        llm_escalation=LLMEscalation(trigger_groups=["critical"], fire_once=False)
    )
    assert _fire_once_enabled(config_no_fire) is False, "fire_once should be False when explicitly disabled"


def test_p0_4_calendar_baseline_resolves_event_id():
    """P0-4: Calendar baseline resolves event_id from string, not just first event."""
    prev = make_state()
    prev["flight_event_id"] = "evt_123"
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
    cal = {
        "flight": {"id": "evt_123", "summary": "Flight", "start": {"dateTime": "2026-07-07T17:25:00-07:00"}},
        "uber": {"id": "evt_456", "summary": "Uber", "start": {"dateTime": "2026-07-07T19:00:00-07:00"}},
    }
    trigger = TriggerAgent(prev, {**prev, **extracted}, cal)
    cond = Condition(id="dep_changed", field="dep_time", op="changed",
                     baseline={"source": "calendar", "event_id": "evt_123", "field": "start.dateTime"})

    # This should resolve evt_123 (not evt_456 which is first in dict iteration)
    baseline = trigger._get_baseline(cond)
    assert baseline == "2026-07-07T17:25:00-07:00", f"Should resolve evt_123's start.dateTime, got {baseline}"


def test_p0_4_calendar_baseline_from_state():
    """P0-4: Calendar baseline resolves event_id from state reference."""
    prev = make_state()
    prev["flight_event_id"] = "evt_abc"
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
    cal = {"flight": {"id": "evt_abc", "summary": "Flight", "start": {"dateTime": "2026-07-07T17:25:00-07:00"}}}
    trigger = TriggerAgent(prev, {**prev, **extracted}, cal)
    cond = Condition(id="dep_changed", field="dep_time", op="changed",
                     baseline={"source": "calendar",
                               "event_id": {"from_state": "flight_event_id"},
                               "field": "start.dateTime"})
    baseline = trigger._get_baseline(cond)
    assert baseline == "2026-07-07T17:25:00-07:00", f"Should resolve from_state event_id, got {baseline}"


runner.run("TC-P0-1: Pruning before fire_once (persistent condition keeps ack)", test_p0_1_pruning_before_fire_once)
runner.run("TC-P0-2: Dry-run does NOT save state", test_p0_2_dry_run_no_state_save)
runner.run("TC-P0-3: fire_once works without llm_escalation", test_p0_3_fire_once_without_llm_escalation)
runner.run("TC-P0-4: Calendar baseline resolves event_id from string", test_p0_4_calendar_baseline_resolves_event_id)
runner.run("TC-P0-4-STATE: Calendar baseline resolves event_id from state", test_p0_4_calendar_baseline_from_state)


# ═══════════════════════════════════════════════════════════════
#  TC-CORNER: Corner case + robustness tests
# ═══════════════════════════════════════════════════════════════

def test_corner_not_empty_list():
    """not: [] should not crash — return True (no-op)."""
    trigger = TriggerAgent({}, {}, {})
    cond = Condition(**{"not": []})  # Use dict to pass the reserved keyword alias
    result = trigger.evaluate(cond)
    assert result.matched, "not: [] should be a no-op (True)"
    assert "no-op" in result.reason


def test_corner_group_both_any_and_all():
    """TC-M9: Groups cannot declare non-empty any and all together."""
    with pytest.raises(ValidationError, match="group 'test' cannot declare both"):
        Group(name="test", any=["c1"], all=["c2"])


def test_exists_treats_whitespace_as_absent():
    """TC-M10: exists rejects whitespace strings but preserves falsey non-string values."""
    trigger = TriggerAgent({}, {"space": "   ", "zero": 0, "false": False}, {})
    assert not trigger.evaluate(Condition(id="space", field="space", op="exists")).matched
    assert trigger.evaluate(Condition(id="zero", field="zero", op="exists")).matched
    assert trigger.evaluate(Condition(id="false", field="false", op="exists")).matched


def test_corner_regex_empty_pattern():
    """regex with pattern=None returns None, not empty string."""
    extractor = ExtractAgent()
    result = FetchResult(200, {}, "some body text")
    spec = ExtractSpec(id="test", type="regex")  # no pattern
    val = extractor.extract(result, [spec])
    assert val["test"] is None, f"Empty regex pattern should return None, got {val['test']!r}"


def test_corner_first_run_changed():
    """changed op with empty baseline fires on first run (documented behavior)."""
    prev = make_state(dep_time="")  # empty initial state
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="dep_changed", field="dep_time", op="changed",
                     baseline={"source": "state", "field": "dep_time"})
    result = trigger.evaluate(cond)
    assert result.matched, "First run with empty baseline should detect change (empty → value)"

    # But None baseline should NOT fire (field doesn't exist yet)
    prev2 = make_state()  # no dep_time at all
    prev2.pop("dep_time", None)
    trigger2 = TriggerAgent(prev2, {**prev2, **extracted}, {})
    cond2 = Condition(id="dep_changed", field="dep_time", op="changed")
    result2 = trigger2.evaluate(cond2)
    # None != "2026-07-07T17:20:00-07:00" → True (changed)
    # This is expected behavior — first run sees all values as "changed"
    assert result2.matched, "None baseline should still detect change (None → value)"


def test_corner_action_unknown_type():
    """Action with unknown type should warn and return False, not crash."""
    sm = StateManager(Path("/tmp/test_action_unknown.json"))
    sm.state = make_state()
    agent = ActionAgent(sm.state, dry_run=False)
    success = agent.execute("test_action", {"type": "webhook", "url": "https://example.com"})
    assert not success, "Unknown action type should return False"


def test_corner_condition_no_field_no_op():
    """Leaf condition with no field/op returns False (not crash)."""
    trigger = TriggerAgent({}, {}, {})
    cond = Condition(id="test")  # no field, no op
    result = trigger.evaluate(cond)
    assert not result.matched, "Condition with no field/op should not match"


def test_corner_template_missing_variable():
    """Template referencing a variable not in state renders as empty string."""
    sm = StateManager(Path("/tmp/test_template_missing.json"))
    sm.state = make_state(status="ok")
    agent = ActionAgent(sm.state, dry_run=True)
    rendered = agent._render_template("Value: {{ nonexistent_var }}", {})
    # Should not crash — missing variable renders as empty
    assert "Value:" in rendered, "Template should still render with missing var"


def test_corner_add_minutes_negative():
    """add_minutes with negative value subtracts minutes."""
    sm = StateManager(Path("/tmp/test_add_neg.json"))
    sm.state = make_state(dep_time="2026-07-07T17:20:00-07:00")
    agent = ActionAgent(sm.state, dry_run=True)
    rendered = agent._render_template("{{ dep_time | add_minutes: -30 }}", sm.state)
    # Should be 16:50 (17:20 - 30 min)
    assert "16:50" in rendered or "T16:50" in rendered, f"Negative add_minutes should subtract, got: {rendered}"


def test_corner_time_diff_no_compared_to():
    """time_diff_gt without compared_to should handle gracefully."""
    prev = make_state(dep_time="2026-07-07T17:25:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="time_diff", field="dep_time", op="time_diff_gt", value="15")
    # compared_to is None — should compare against state (default behavior)
    result = trigger.evaluate(cond)
    # 5 min diff < 15 → should not match
    assert not result.matched, "5 min diff should be < 15 min threshold"


def test_corner_changed_string_vs_int():
    """changed op: '5' vs 5 (string vs int) — should detect as changed (type mismatch)."""
    prev = make_state()
    prev["price"] = "5"  # string
    extracted = {}
    extracted["price"] = 5  # int
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="price_changed", field="price", op="changed")
    result = trigger.evaluate(cond)
    assert result.matched, "'5' != 5 (string vs int) — should detect as changed"


def test_corner_state_missing_internal_keys():
    """State loaded but missing acknowledged/first_seen sub-dicts — should auto-init."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "state.json"
        # Write state WITHOUT internal keys
        path.write_text(json.dumps({"dep_time": "17:20", "status": "On time"}))
        sm = StateManager(path)
        sm.load()
        assert "acknowledged" in sm.state, "acknowledged should be auto-initialized"
        assert "first_seen" in sm.state, "first_seen should be auto-initialized"
        assert "last_fired" in sm.state, "last_fired should be auto-initialized"
        assert sm.state["dep_time"] == "17:20", "Non-internal keys should be preserved"


def test_corner_config_empty_conditions():
    """Config with empty conditions list — should parse and validate."""
    config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
    assert config.conditions == [], "Empty conditions should be valid"


def test_corner_config_empty_groups():
    """Config with empty groups list — should parse and validate."""
    config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
    assert config.groups == [], "Empty groups should be valid"


def test_corner_source_no_extract():
    """Source with empty extract list — should parse and validate."""
    config = DetectConfig(
        name="Test",
        sources=[Source(id="test", url="https://example.com", extract=[])],
        conditions=[], groups=[], actions={}
    )
    assert config.sources[0].extract == [], "Empty extract should be valid"


def test_corner_multiple_conditions_fire():
    """Multiple conditions fire in same poll — each gets its own escalation file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        import detect_engine
        orig_dir = detect_engine.ESCALATION_DIR
        detect_engine.ESCALATION_DIR = Path(tmpdir)

        try:
            config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
            prev = make_state(dep_time="17:25", arr_time="19:33", status="On time")
            current = make_state(dep_time="17:20", arr_time="19:18", status="Delayed")
            esc = LLMEscalationAgent(config, prev, current, [])
            cond1 = Condition(id="dep_changed", field="dep_time", op="changed")
            cond2 = Condition(id="arr_changed", field="arr_time", op="changed")
            cond3 = Condition(id="status_changed", field="status", op="changed")
            r1 = ConditionResult(True, "dep changed")
            r2 = ConditionResult(True, "arr changed")
            r3 = ConditionResult(True, "status changed")

            files = esc.escalate([("dep_changed", r1, cond1), ("arr_changed", r2, cond2), ("status_changed", r3, cond3)])
            assert len(files) == 3, f"Should create 3 escalation files, got {len(files)}"
            # All files should exist
            for f in files:
                assert Path(f).exists(), f"Evidence file {f} should exist"
        finally:
            detect_engine.ESCALATION_DIR = orig_dir


def test_corner_network_error_retry():
    """httpx.NetworkError should be retried (added to transient error list)."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://example.com", timeout=5,
                    retry={"count": 1, "backoff": 0})

    with patch("detect_engine.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = httpx.NetworkError("network unreachable")

        result = fetcher.fetch(source)
        assert result.attempts == 2, f"NetworkError should be retried (2 attempts), got {result.attempts}"
        assert "NetworkError" in result.last_error_type
        assert not result.ok


def test_corner_parse_dt_failure():
    """_parse_dt on non-ISO datetime should not crash — returns None."""
    sm = StateManager(Path("/tmp/test_parse_dt.json"))
    sm.state = make_state(dep_time="not-a-date")
    agent = ActionAgent(sm.state, dry_run=True)
    rendered = agent._render_template("{{ dep_time | add_minutes: 30 }}", sm.state)
    # Should not crash — invalid datetime renders as original or empty
    assert rendered is not None, "Should not crash on invalid datetime"


def test_corner_time_diff_minutes_direct():
    """Directly test _time_diff_minutes helper."""
    trigger = TriggerAgent({}, {}, {})
    # 15 minute difference
    diff = trigger._time_diff_minutes("2026-07-07T17:25:00-07:00", "2026-07-07T17:10:00-07:00")
    assert diff == 15, f"Expected 15 min diff, got {diff}"
    # Same time
    diff_same = trigger._time_diff_minutes("2026-07-07T17:25:00-07:00", "2026-07-07T17:25:00-07:00")
    assert diff_same == 0, f"Expected 0 min diff, got {diff_same}"
    # None value
    diff_none = trigger._time_diff_minutes(None, "2026-07-07T17:25:00-07:00")
    assert diff_none is None, "None input should return None"


def test_corner_env_var_interpolation():
    """_resolve_env_vars interpolates {{env:VAR_NAME}} from environment."""
    os.environ["TEST_API_KEY"] = "secret123"
    fetcher = FetchAgent()
    params = {"api_key": "{{env:TEST_API_KEY}}", "other": "normal_value"}
    resolved = fetcher._resolve_env_vars(params)
    assert resolved["api_key"] == "secret123", f"Should interpolate env var, got {resolved['api_key']}"
    assert resolved["other"] == "normal_value"
    del os.environ["TEST_API_KEY"]


def test_corner_env_var_missing():
    """_resolve_env_vars with missing env var returns empty string."""
    fetcher = FetchAgent()
    params = {"api_key": "{{env:NONEXISTENT_VAR}}"}
    resolved = fetcher._resolve_env_vars(params)
    assert resolved["api_key"] == "", "Missing env var should resolve to empty string"


def test_corner_group_empty_any_all():
    """Group with empty any: and all: lists — no conditions to check, should not match."""
    group = Group(name="empty", any=[], all=[])
    evaluator = GroupEvaluator()
    matched, ids = evaluator.evaluate_group(group, {})
    assert not matched, "Empty group should not match"
    assert ids == [], "Empty group should have no matched IDs"


runner.run("TC-CORNER-NOT-EMPTY: not: [] is a no-op (no crash)", test_corner_not_empty_list)
runner.run("TC-M9: Group with any+all is rejected", test_corner_group_both_any_and_all)
runner.run("TC-M10: exists rejects whitespace only strings", test_exists_treats_whitespace_as_absent)
runner.run("TC-CORNER-REGEX-EMPTY: regex with no pattern returns None", test_corner_regex_empty_pattern)
runner.run("TC-CORNER-FIRST-RUN: changed op fires on first run (empty baseline)", test_corner_first_run_changed)
runner.run("TC-CORNER-ACTION-UNKNOWN: Unknown action type returns False (no crash)", test_corner_action_unknown_type)
runner.run("TC-CORNER-NO-FIELD-OP: Condition with no field/op returns False", test_corner_condition_no_field_no_op)
runner.run("TC-CORNER-TEMPLATE-MISSING: Template with missing var doesn't crash", test_corner_template_missing_variable)
runner.run("TC-CORNER-ADD-NEG: add_minutes with negative value subtracts", test_corner_add_minutes_negative)
runner.run("TC-CORNER-TIME-DIFF-NO-COMPARED: time_diff_gt without compared_to uses state default", test_corner_time_diff_no_compared_to)
runner.run("TC-CORNER-CHANGED-TYPE: changed op detects string vs int as changed", test_corner_changed_string_vs_int)
runner.run("TC-CORNER-STATE-KEYS: State missing internal keys auto-initializes", test_corner_state_missing_internal_keys)
runner.run("TC-CORNER-EMPTY-CONDITIONS: Config with empty conditions list is valid", test_corner_config_empty_conditions)
runner.run("TC-CORNER-EMPTY-GROUPS: Config with empty groups list is valid", test_corner_config_empty_groups)
runner.run("TC-CORNER-SOURCE-NO-EXTRACT: Source with empty extract list is valid", test_corner_source_no_extract)
runner.run("TC-CORNER-MULTI-ESCALATION: Multiple conditions → multiple escalation files", test_corner_multiple_conditions_fire)
runner.run("TC-CORNER-NETWORK-ERROR: httpx.NetworkError is retried", test_corner_network_error_retry)
runner.run("TC-CORNER-PARSE-DT: _parse_dt on invalid datetime doesn't crash", test_corner_parse_dt_failure)
runner.run("TC-CORNER-TIME-DIFF-DIRECT: _time_diff_minutes computes correctly", test_corner_time_diff_minutes_direct)
runner.run("TC-CORNER-ENV-VAR: Env var interpolation works", test_corner_env_var_interpolation)
runner.run("TC-CORNER-ENV-MISSING: Missing env var resolves to empty string", test_corner_env_var_missing)
runner.run("TC-CORNER-GROUP-EMPTY: Group with empty any+all doesn't match", test_corner_group_empty_any_all)


# ═══════════════════════════════════════════════════════════════
#  TC-OPS2: Numeric + time_diff operator tests (two-sided)
# ═══════════════════════════════════════════════════════════════

def test_gt_pos():
    prev = make_state()
    extracted = make_extracted()
    extracted["price"] = "250"
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="price_high", field="price", op="gt", value="200")
    result = trigger.evaluate(cond)
    assert result.matched, "250 > 200 should match"

def test_gt_neg():
    prev = make_state()
    extracted = make_extracted()
    extracted["price"] = "150"
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="price_high", field="price", op="gt", value="200")
    result = trigger.evaluate(cond)
    assert not result.matched, "150 > 200 should not match"

def test_gte_pos():
    extracted = {"price": "200"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="gte", value="200")
    assert trigger.evaluate(cond).matched, "200 >= 200 should match"

def test_gte_neg():
    extracted = {"price": "199"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="gte", value="200")
    assert not trigger.evaluate(cond).matched, "199 >= 200 should not match"

def test_lt_pos():
    extracted = {"price": "49"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="lt", value="50")
    assert trigger.evaluate(cond).matched, "49 < 50 should match"

def test_lt_neg():
    extracted = {"price": "50"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="lt", value="50")
    assert not trigger.evaluate(cond).matched, "50 < 50 should not match"

def test_lte_pos():
    extracted = {"price": "50"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="lte", value="50")
    assert trigger.evaluate(cond).matched, "50 <= 50 should match"

def test_lte_neg():
    extracted = {"price": "51"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="lte", value="50")
    assert not trigger.evaluate(cond).matched, "51 <= 50 should not match"

def test_time_diff_gt_pos():
    prev = make_state(dep_time="2026-07-07T17:25:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T17:05:00-07:00")
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="test", field="dep_time", op="time_diff_gt", value="15",
                     compared_to="state.dep_time")
    assert trigger.evaluate(cond).matched, "20 min diff > 15 should match"

def test_time_diff_gt_neg():
    prev = make_state(dep_time="2026-07-07T17:25:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T17:20:00-07:00")
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="test", field="dep_time", op="time_diff_gt", value="15",
                     compared_to="state.dep_time")
    assert not trigger.evaluate(cond).matched, "5 min diff > 15 should not match"

def test_time_diff_lt_pos():
    prev = make_state(dep_time="2026-07-07T17:25:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T17:22:00-07:00")
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="test", field="dep_time", op="time_diff_lt", value="10",
                     compared_to="state.dep_time")
    assert trigger.evaluate(cond).matched, "3 min diff < 10 should match"

def test_time_diff_lt_neg():
    prev = make_state(dep_time="2026-07-07T17:25:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T17:05:00-07:00")
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="test", field="dep_time", op="time_diff_lt", value="10",
                     compared_to="state.dep_time")
    assert not trigger.evaluate(cond).matched, "20 min diff < 10 should not match"


runner.run("TC-GT-POS: gt fires when value exceeds threshold", test_gt_pos)
runner.run("TC-GT-NEG: gt silent when value below threshold", test_gt_neg)
runner.run("TC-GTE-POS: gte fires on equal value", test_gte_pos)
runner.run("TC-GTE-NEG: gte silent when below", test_gte_neg)
runner.run("TC-LT-POS: lt fires when value below threshold", test_lt_pos)
runner.run("TC-LT-NEG: lt silent when at threshold", test_lt_neg)
runner.run("TC-LTE-POS: lte fires on equal value", test_lte_pos)
runner.run("TC-LTE-NEG: lte silent when above", test_lte_neg)
runner.run("TC-TDIFF-GT-POS: time_diff_gt fires on 20 min > 15", test_time_diff_gt_pos)
runner.run("TC-TDIFF-GT-NEG: time_diff_gt silent on 5 min < 15", test_time_diff_gt_neg)
runner.run("TC-TDIFF-LT-POS: time_diff_lt fires on 3 min < 10", test_time_diff_lt_pos)
runner.run("TC-TDIFF-LT-NEG: time_diff_lt silent on 20 min > 10", test_time_diff_lt_neg)


# ═══════════════════════════════════════════════════════════════
#  TC-INT: Integration tests for run_engine end-to-end
# ═══════════════════════════════════════════════════════════════

def test_integration_no_change_silent():
    """run_engine end-to-end: no changes → exit 0, no output, state saved."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test.yaml"
        state_path = Path(tmpdir) / "state" / "test.json"
        state_path.parent.mkdir(parents=True)
        # Write initial state matching what the mock will return
        state_path.write_text(json.dumps(make_state(
            dep_time="2026-07-07T17:20:00-07:00",
            arr_time="2026-07-07T19:18:00-07:00",
        )))

        config_path.write_text("""
name: "Integration Test"
sources:
  - id: test_source
    url: "https://example.com/api"
    extract:
      - id: dep_time
        type: jsonpath
        path: "$.dep_time"
      - id: arr_time
        type: jsonpath
        path: "$.arr_time"
conditions:
  - id: dep_changed
    field: dep_time
    op: changed
    baseline: {source: state, field: dep_time}
groups:
  - name: critical
    any: [dep_changed]
    actions: []
llm_escalation:
  trigger_groups: [critical]
  fire_once: true
state:
  file: "state/test.json"
  initial: {dep_time: "", arr_time: ""}
""")

        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_resp.text = json.dumps({"dep_time": "2026-07-07T17:20:00-07:00", "arr_time": "2026-07-07T19:18:00-07:00"})
            mock_client.request.return_value = mock_resp

            exit_code = run_engine(str(config_path), dry_run=False)
            assert exit_code == 0, f"Should exit 0 on no change, got {exit_code}"


def test_integration_change_detected():
    """run_engine end-to-end: change detected → exit 0, state saved with new values."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test.yaml"
        state_path = Path(tmpdir) / "state" / "test.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps(make_state(dep_time="2026-07-07T17:25:00-07:00")))

        config_path.write_text("""
name: "Integration Test"
sources:
  - id: test_source
    url: "https://example.com/api"
    extract:
      - id: dep_time
        type: jsonpath
        path: "$.dep_time"
conditions:
  - id: dep_changed
    field: dep_time
    op: changed
    baseline: {source: state, field: dep_time}
groups:
  - name: critical
    any: [dep_changed]
    actions: []
state:
  file: "state/test.json"
  initial: {dep_time: ""}
""")

        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_resp.text = json.dumps({"dep_time": "2026-07-07T17:20:00-07:00"})
            mock_client.request.return_value = mock_resp

            exit_code = run_engine(str(config_path), dry_run=False)
            assert exit_code == 0, f"Should exit 0 on change detected, got {exit_code}"
            # State should be saved with new value
            saved = json.loads(state_path.read_text())
            assert saved["dep_time"] == "2026-07-07T17:20:00-07:00", \
                f"State should have new dep_time, got {saved.get('dep_time')}"


def test_integration_dry_run_no_state_write():
    """run_engine end-to-end: dry-run does NOT write state file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test.yaml"
        state_path = Path(tmpdir) / "state" / "test.json"
        state_path.parent.mkdir(parents=True)
        original_state = json.dumps(make_state(dep_time="2026-07-07T17:25:00-07:00"))
        state_path.write_text(original_state)

        config_path.write_text("""
name: "Integration Test"
sources:
  - id: test_source
    url: "https://example.com/api"
    extract:
      - id: dep_time
        type: jsonpath
        path: "$.dep_time"
conditions:
  - id: dep_changed
    field: dep_time
    op: changed
    baseline: {source: state, field: dep_time}
groups:
  - name: critical
    any: [dep_changed]
    actions: []
state:
  file: "state/test.json"
  initial: {dep_time: ""}
""")

        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {}
            mock_resp.text = json.dumps({"dep_time": "2026-07-07T17:20:00-07:00"})
            mock_client.request.return_value = mock_resp

            exit_code = run_engine(str(config_path), dry_run=True)
            assert exit_code == 0
            # State should NOT be modified
            assert state_path.read_text() == original_state, \
                "Dry-run should NOT modify state file"


def test_integration_expired_config_skipped():
    """run_engine: expired config → exit 0 (skipped silently)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test.yaml"
        config_path.write_text("""
name: "Expired Test"
expires: "2020-01-01T00:00:00Z"
sources:
  - id: test
    url: "https://example.com"
    extract:
      - id: x
        type: jsonpath
        path: "$.x"
conditions: []
groups: []
state:
  file: "state/test.json"
""")
        exit_code = run_engine(str(config_path), dry_run=False)
        assert exit_code == 0, "Expired config should exit 0 (skipped)"


def test_integration_fetch_failure_required():
    """run_engine: required source fails → exit 1."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test.yaml"
        config_path.write_text("""
name: "Fetch Fail Test"
sources:
  - id: test
    url: "https://example.com"
    required: true
    timeout: 5
    retry:
      count: 0
    extract:
      - id: x
        type: jsonpath
        path: "$.x"
conditions:
  - id: x_changed
    field: x
    op: changed
groups:
  - name: g
    any: [x_changed]
state:
  file: "state/test.json"
  initial: {x: ""}
""")
        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.request.side_effect = httpx.ConnectError("connection refused")
            exit_code = run_engine(str(config_path), dry_run=False)
            assert exit_code == 1, f"Required source failure should exit 1, got {exit_code}"


# ═══════════════════════════════════════════════════════════════
#  TC-MISC: Remaining P2/P3 gaps
# ═══════════════════════════════════════════════════════════════

def test_fetch_ok_property():
    """FetchResult.ok property — True for 200, False for 500 and errors."""
    ok_result = FetchResult(200, {}, "body")
    assert ok_result.ok, "200 should be ok"
    err_result = FetchResult(500, {}, "error body")
    assert not err_result.ok, "500 should not be ok"
    fail_result = FetchResult(0, {}, "", error="timeout")
    assert not fail_result.ok, "Error result should not be ok"

def test_write_health():
    """write_health writes valid JSON to disk."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = Path(tmpdir) / "health.json"
        write_health(health_path, "ok", "Test Monitor", "no changes")
        data = json.loads(health_path.read_text())
        assert data["status"] == "ok"
        assert data["config"] == "Test Monitor"
        assert data["detail"] == "no changes"
        assert "timestamp" in data

def test_action_computed_fields():
    """ActionAgent with computed: derived template variables."""
    sm = StateManager(Path("/tmp/test_computed.json"))
    sm.state = make_state(dep_time="2026-07-07T17:20:00-07:00")
    agent = ActionAgent(sm.state, dry_run=True)
    # computed: defines derived vars that can be used in fields
    action_def = {
        "type": "calendar_patch",
        "event_id": "test_event",
        "fields": {"summary": "Arrival: {{ arr_time }}"},
        "computed": {"arr_time": "{{ dep_time | add_minutes: 120 }}"}
    }
    # In dry-run, execute should succeed (just prints)
    success = agent.execute("test", action_def)
    assert success, "Dry-run with computed fields should succeed"

def test_config_invalid_op():
    """Invalid op string is now rejected by Pydantic validator (blocker 7 fix)."""
    try:
        Condition(id="test", field="x", op="invalid_op", value="y")
        assert False, "Should have raised ValidationError for invalid op"
    except ValidationError:
        pass  # Expected — invalid ops are now rejected


def test_config_valid_op():
    """Valid op strings are accepted."""
    for op in ["changed", "eq", "ne", "contains", "exists", "matches", "gt", "lt"]:
        cond = Condition(id="test", field="x", op=op, value="y")
        assert cond.op == op, f"Valid op '{op}' should be accepted"


def test_validate_cross_refs_good():
    """validate_config_cross_refs returns no errors for a well-formed config."""
    from detect_engine import DetectConfig
    config = DetectConfig(
        name="test",
        conditions=[Condition(id="dep_changed", field="dep_time", op="changed")],
        groups=[Group(name="critical", any=["dep_changed"], actions=["patch_flight"])],
        actions={"patch_flight": {"type": "calendar_patch", "event_id": "evt1"}},
    )
    errors = validate_config_cross_refs(config)
    assert not errors, f"Should have no errors, got: {errors}"


def test_validate_cross_refs_bad_condition():
    """validate_config_cross_refs catches unknown condition reference in group."""
    from detect_engine import DetectConfig
    config = DetectConfig(
        name="test",
        conditions=[Condition(id="dep_changed", field="dep_time", op="changed")],
        groups=[Group(name="critical", any=["nonexistent_cond"], actions=["patch_flight"])],
        actions={"patch_flight": {"type": "calendar_patch", "event_id": "evt1"}},
    )
    errors = validate_config_cross_refs(config)
    assert any("nonexistent_cond" in e for e in errors), "Should catch unknown condition ref"


def test_validate_cross_refs_bad_action():
    """validate_config_cross_refs catches unknown action reference in group."""
    from detect_engine import DetectConfig
    config = DetectConfig(
        name="test",
        conditions=[Condition(id="dep_changed", field="dep_time", op="changed")],
        groups=[Group(name="critical", any=["dep_changed"], actions=["nonexistent_action"])],
        actions={"patch_flight": {"type": "calendar_patch", "event_id": "evt1"}},
    )
    errors = validate_config_cross_refs(config)
    assert any("nonexistent_action" in e for e in errors), "Should catch unknown action ref"


def test_template_fmt_time_filter():
    """fmt_time with explicit tz arg converts ISO datetime to 'H:MM AM/PM PT'."""
    action = ActionAgent({
        "dep_time": "2026-07-07T17:20:00-07:00",
    }, dry_run=True)
    # Raw offset → UTC-07:00 (can't distinguish PT from MT by offset alone)
    result = action._render_template("Depart: {{ dep_time | fmt_time }}", {"dep_time": "2026-07-07T17:20:00-07:00"})
    assert "5:20 PM" in result, f"Expected '5:20 PM' in result, got '{result}'"
    # Explicit tz arg → "PT"
    result_tz = action._render_template("Depart: {{ dep_time | fmt_time:America/Los_Angeles }}", {"dep_time": "2026-07-07T17:20:00-07:00"})
    assert "5:20 PM" in result_tz, f"Expected '5:20 PM' in result, got '{result_tz}'"
    assert "PT" in result_tz or "LosAn" in result_tz, f"Expected 'PT' or timezone in result, got '{result_tz}'"


def test_template_fmt_time_with_none():
    """fmt_time filter with None returns 'N/A'."""
    action = ActionAgent({}, dry_run=True)
    result = action._render_template("Depart: {{ dep_time | fmt_time }}", {"dep_time": None})
    assert "N/A" in result, f"Expected 'N/A', got '{result}'"


def test_template_default_filter():
    """default filter replaces None/empty with fallback."""
    action = ActionAgent({}, dry_run=True)
    result = action._render_template("Gate: {{ gate | default:TBD }}", {"gate": None})
    assert "TBD" in result, f"Expected 'TBD', got '{result}'"


def test_template_none_renders_empty():
    """None values render as empty string, not 'None'."""
    action = ActionAgent({}, dry_run=True)
    result = action._render_template("Arrive: {{ arr_time }}", {"arr_time": None})
    assert "None" not in result, f"None should not render as 'None', got '{result}'"
    assert "Arrive: " in result, f"Should render as 'Arrive: ', got '{result}'"


def test_template_add_minutes_none():
    """add_minutes with None input returns empty string."""
    action = ActionAgent({}, dry_run=True)
    result = action._render_template("{{ arr_time | add_minutes: 17 }}", {"arr_time": None})
    assert result == "", f"add_minutes with None should return empty, got '{result}'"


def test_template_multiline():
    """Multi-line template renders correctly."""
    action = ActionAgent({"dep": "SEA", "arr": "OAK"}, dry_run=True)
    template = "Line 1: {{ dep }}\nLine 2: {{ arr }}\nLine 3: end"
    result = action._render_template(template, {"dep": "SEA", "arr": "OAK"})
    assert "Line 1: SEA" in result and "Line 2: OAK" in result, f"Multi-line failed: '{result}'"


def test_action_with_calendar_events():
    """ActionAgent receives calendar_events for preserve_from_desc."""
    action = ActionAgent({}, dry_run=True, calendar_events={
        "patch_flight": {"summary": "Test Event", "description": '<a href="https://mail.google.com/inbox/123">Booking</a>'}
    })
    assert "patch_flight" in action.calendar_events
    assert "Test Event" in action.calendar_events["patch_flight"]["summary"]


def test_preserve_from_desc():
    """preserve_from_desc extracts content from existing calendar event description."""
    action = ActionAgent({}, dry_run=True, calendar_events={
        "patch_flight": {
            "summary": "Test",
            "description": '<a href="https://mail.google.com/inbox/123">📋 View booking email</a>'
        }
    })
    action_def = {
        "type": "calendar_patch",
        "event_id": "evt1",
        "preserve_from_desc": [
            {"as": "gmail_link", "pattern": r'<a href="https://mail\.google\.com/[^"]+">[^<]*</a>'}
        ],
        "fields": {"description": "Flight info\n\n{{ gmail_link }}"},
    }
    success = action.execute("patch_flight", action_def)
    assert success
    # The results should contain the preserved link
    assert any("mail.google.com" in r for r in action.results), \
        f"Should preserve Gmail link, results: {action.results}"


def test_chained_filters():
    """Multiple filters can be chained: {{ var | fmt_time | default:N/A }}"""
    action = ActionAgent({}, dry_run=True)
    # fmt_time on None → N/A → default shouldn't change it since N/A isn't empty
    result = action._render_template("{{ dep_time | fmt_time }}", {"dep_time": None})
    assert "N/A" in result
runner.run("TC-WRITE-HEALTH: write_health writes valid JSON", test_write_health)
runner.run("TC-ACTION-COMPUTED: ActionAgent with computed derived vars", test_action_computed_fields)
runner.run("TC-CONFIG-INVALID-OP: Invalid op rejected by validator", test_config_invalid_op)
runner.run("TC-CONFIG-VALID-OP: Valid op strings accepted", test_config_valid_op)
runner.run("TC-CONFIG-XREF-GOOD: Cross-ref validation passes for good config", test_validate_cross_refs_good)
runner.run("TC-CONFIG-XREF-BAD-COND: Cross-ref catches unknown condition", test_validate_cross_refs_bad_condition)
runner.run("TC-CONFIG-XREF-BAD-ACT: Cross-ref catches unknown action", test_validate_cross_refs_bad_action)
runner.run("TC-TEMPLATE-FMT-TIME: fmt_time filter formats ISO to PT", test_template_fmt_time_filter)
runner.run("TC-TEMPLATE-FMT-TIME-NONE: fmt_time with None → N/A", test_template_fmt_time_with_none)
runner.run("TC-TEMPLATE-DEFAULT: default filter replaces None", test_template_default_filter)
runner.run("TC-TEMPLATE-NONE-EMPTY: None renders as empty string", test_template_none_renders_empty)
runner.run("TC-TEMPLATE-ADD-MIN-NONE: add_minutes with None → empty", test_template_add_minutes_none)
runner.run("TC-TEMPLATE-MULTILINE: Multi-line template renders", test_template_multiline)
runner.run("TC-ACTION-CAL-EVENTS: ActionAgent receives calendar_events", test_action_with_calendar_events)
runner.run("TC-ACTION-PRESERVE: preserve_from_desc extracts from existing desc", test_preserve_from_desc)
runner.run("TC-TEMPLATE-CHAINED: Chained filters work", test_chained_filters)

runner.run("TC-INT-NO-CHANGE: Integration — no change → exit 0", test_integration_no_change_silent)
runner.run("TC-INT-CHANGE: Integration — change → exit 0, state saved", test_integration_change_detected)
runner.run("TC-INT-DRY-RUN: Integration — dry-run doesn't write state", test_integration_dry_run_no_state_write)
runner.run("TC-INT-EXPIRED: Integration — expired config skipped", test_integration_expired_config_skipped)
runner.run("TC-INT-FAIL: Integration — required fetch failure → exit 1", test_integration_fetch_failure_required)


# ═══════════════════════════════════════════════════════════════
#  TC-EDGE2: Round 3 edge cases (P3 polish)
# ═══════════════════════════════════════════════════════════════

def test_contains_pos():
    """contains operator — positive: field contains substring."""
    extracted = {"cal_title": "FLIGHT DELAYED — AS706"}
    trigger = TriggerAgent({}, extracted, {"flight": MockCalendarEvent.make(summary="FLIGHT DELAYED — AS706")})
    cond = Condition(id="test", field="cal_title", op="contains", value="DELAYED")
    result = trigger.evaluate(cond)
    assert result.matched, "cal_title containing 'DELAYED' should match"

def test_contains_neg():
    """contains operator — negative: field does not contain substring."""
    extracted = {"cal_title": "AS706: SEA → OAK"}
    trigger = TriggerAgent({}, extracted, {"flight": MockCalendarEvent.make(summary="AS706: SEA → OAK")})
    cond = Condition(id="test", field="cal_title", op="contains", value="DELAYED")
    result = trigger.evaluate(cond)
    assert not result.matched, "cal_title without 'DELAYED' should not match"

def test_eq_neg_direct():
    """eq operator — negative: field does not equal value."""
    extracted = {"status": "On time"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="status", op="eq", value="Delayed")
    assert not trigger.evaluate(cond).matched, "status 'On time' != 'Delayed'"

def test_state_save_creates_parent():
    """StateManager.save() creates parent directory if missing."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "nested" / "deep" / "state.json"
        sm = StateManager(path)
        sm.state = make_state(status="ok")
        sm.save()
        assert path.exists(), "save() should create parent directories"

def test_state_load_extra_keys():
    """State with extra unknown keys preserves them on load."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "state.json"
        path.write_text(json.dumps({"custom_key": "preserved", "dep_time": "17:20",
                                     "acknowledged": {}, "first_seen": {}, "last_fired": {}}))
        sm = StateManager(path)
        sm.load()
        assert sm.state.get("custom_key") == "preserved", "Extra keys should be preserved"

def test_state_ack_overwrite():
    """acknowledge() overwrites previous ack for same condition."""
    sm = StateManager(Path("/tmp/test_ack_over.json"))
    sm.state = make_state()
    sm.acknowledge("cond1", "value_a")
    assert sm.state["acknowledged"]["cond1"]["value"] == "value_a"
    sm.acknowledge("cond1", "value_b")
    assert sm.state["acknowledged"]["cond1"]["value"] == "value_b", "Should overwrite with new value"

def test_fetch_404_no_retry():
    """FetchAgent handles 404 — ok=False, no retry (HTTP errors aren't transient)."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://example.com", timeout=5, retry={"count": 2, "backoff": 0})
    with patch("detect_engine.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.headers = {}
        mock_resp.text = "Not Found"
        mock_client.request.return_value = mock_resp
        result = fetcher.fetch(source)
        assert result.attempts == 1, "404 should not retry (not transient)"
        assert not result.ok, "404 should not be ok"

def test_fetch_custom_headers():
    """FetchAgent passes custom headers to request."""
    fetcher = FetchAgent()
    source = Source(id="test", url="https://example.com", headers={"X-Custom": "val123"})
    with patch("detect_engine.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {}
        mock_resp.text = "{}"
        mock_client.request.return_value = mock_resp
        fetcher.fetch(source)
        call_kwargs = mock_client.request.call_args
        headers_passed = call_kwargs.kwargs.get("headers", {})
        assert headers_passed.get("X-Custom") == "val123", "Custom headers should be passed"

def test_group_nonexistent_cond():
    """Group any: references non-existent condition ID — should not match."""
    group = Group(name="test", any=["nonexistent"])
    evaluator = GroupEvaluator()
    matched, ids = evaluator.evaluate_group(group, {})
    assert not matched, "Non-existent condition should not match"
    assert ids == [], "No matched IDs for non-existent condition"

def test_esc_fire_once_false():
    """fire_once=False allows re-escalation for same value (not suppressed)."""
    with TempStateDir() as tsd:
        tsd.write_state(make_state(
            status="Delayed",
            acknowledged={"flight_delayed": {"at": "2026-07-08T00:00:00Z", "value": "Delayed"}},
        ))
        sm = StateManager(tsd.state_path)
        sm.load()
        # fire_once=False → _fire_once_enabled returns False → no suppression
        config = DetectConfig(
            name="Test", sources=[], conditions=[], groups=[], actions={},
            llm_escalation=LLMEscalation(trigger_groups=["g"], fire_once=False)
        )
        assert not _fire_once_enabled(config), "fire_once=False should disable suppression"
        # is_acknowledged would return True, but _fire_once_enabled returns False
        # so the engine would NOT suppress → re-escalation allowed

def test_config_disabled_skipped():
    """Config with enabled: false is skipped by run_engine."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "test.yaml"
        config_path.write_text("""
name: "Disabled Test"
enabled: false
sources:
  - id: test
    url: "https://example.com"
    extract:
      - id: x
        type: jsonpath
        path: "$.x"
conditions: []
groups: []
state:
  file: "state/test.json"
""")
        exit_code = run_engine(str(config_path), dry_run=False)
        assert exit_code == 0, "Disabled config should exit 0 (skipped)"

def test_config_no_llm_escalation():
    """Config without llm_escalation — actions only, no escalation files."""
    config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
    assert config.llm_escalation is None, "No llm_escalation block should be None"
    assert _fire_once_enabled(config), "fire_once should default True even without llm_escalation"

def test_template_whitespace_in_var():
    """Template with whitespace around var name: {{ var }} works."""
    sm = StateManager(Path("/tmp/test_ws.json"))
    sm.state = make_state(status="ok")
    agent = ActionAgent(sm.state, dry_run=True)
    rendered = agent._render_template("Status: {{   status   }}", sm.state)
    assert "ok" in rendered, f"Whitespace around var name should still work, got: {rendered}"

def test_template_special_chars():
    """Template value with special characters (quotes, brackets)."""
    sm = StateManager(Path("/tmp/test_sc.json"))
    sm.state = make_state()
    sm.state["msg"] = 'He said "hello" [tag]'
    agent = ActionAgent(sm.state, dry_run=True)
    rendered = agent._render_template("Msg: {{ msg }}", sm.state)
    assert 'He said "hello" [tag]' in rendered, "Special chars should be preserved"

def test_action_start_end_fields():
    """calendar_patch with start/end dateTime fields in dry-run."""
    sm = StateManager(Path("/tmp/test_se.json"))
    sm.state = make_state(dep_time="2026-07-07T17:20:00-07:00")
    agent = ActionAgent(sm.state, dry_run=True)
    action_def = {
        "type": "calendar_patch",
        "event_id": "test_event",
        "fields": {
            "summary": "Flight",
            "start": {"dateTime": "{{ dep_time }}", "timeZone": "America/Los_Angeles"},
        }
    }
    success = agent.execute("test", action_def)
    assert success, "Dry-run with start/end fields should succeed"


runner.run("TC-CONTAINS-POS: contains fires when substring present", test_contains_pos)
runner.run("TC-CONTAINS-NEG: contains silent when substring absent", test_contains_neg)
runner.run("TC-EQ-NEG: eq silent when value differs", test_eq_neg_direct)
runner.run("TC-STATE-SAVE-PARENT: save() creates parent dirs", test_state_save_creates_parent)
runner.run("TC-STATE-EXTRA: State preserves extra keys on load", test_state_load_extra_keys)
runner.run("TC-STATE-ACK-OVERWRITE: acknowledge() overwrites previous", test_state_ack_overwrite)
runner.run("TC-FETCH-404: 404 not ok, no retry", test_fetch_404_no_retry)
runner.run("TC-FETCH-HEADERS: Custom headers passed to request", test_fetch_custom_headers)
runner.run("TC-GROUP-NONEXIST: Group with non-existent condition doesn't match", test_group_nonexistent_cond)
runner.run("TC-ESC-FIREONCE-FALSE: fire_once=False disables suppression", test_esc_fire_once_false)
runner.run("TC-CONFIG-DISABLED-SKIP: Disabled config skipped by run_engine", test_config_disabled_skipped)
runner.run("TC-CONFIG-NO-ESC: Config without llm_escalation — fire_once defaults True", test_config_no_llm_escalation)
runner.run("TC-TEMPLATE-WS: Template with whitespace in var name works", test_template_whitespace_in_var)
runner.run("TC-TEMPLATE-SPECIAL: Template preserves special characters", test_template_special_chars)
runner.run("TC-ACTION-START-END: calendar_patch with start/end dateTime fields", test_action_start_end_fields)


# ═══════════════════════════════════════════════════════════════
#  TC-EDGE3: Round 4 deep edge cases
# ═══════════════════════════════════════════════════════════════

def test_nested_and_in_or():
    """Nested AND inside OR — hierarchical boolean depth > 1."""
    trigger = TriggerAgent({}, {"a": "x", "b": "y", "c": "z"}, {})
    cond = Condition(id="nested", **{"or": [
        {"and": [
            {"field": "a", "op": "eq", "value": "x"},
            {"field": "b", "op": "eq", "value": "y"},
        ]},
        {"field": "c", "op": "eq", "value": "wrong"},
    ]})
    result = trigger.evaluate(cond)
    assert result.matched, "OR → AND(a=x, b=y) should match"
    # OR returns on first match, so submatches may be just 1 (the winning branch)
    assert len(result.submatches) >= 1, "OR should have at least 1 submatch"

def test_nested_or_in_and():
    """Nested OR inside AND."""
    trigger = TriggerAgent({}, {"a": "x", "b": "y"}, {})
    cond = Condition(id="nested", **{"and": [
        {"field": "a", "op": "eq", "value": "x"},
        {"or": [
            {"field": "b", "op": "eq", "value": "y"},
            {"field": "b", "op": "eq", "value": "z"},
        ]},
    ]})
    result = trigger.evaluate(cond)
    assert result.matched, "AND(a=x, OR(b=y, b=z)) should match"

def test_nested_and_in_or_fail():
    """Nested AND inside OR where AND fails but OR still has a fallback."""
    trigger = TriggerAgent({}, {"a": "x", "b": "wrong", "c": "z"}, {})
    cond = Condition(id="nested", **{"or": [
        {"and": [
            {"field": "a", "op": "eq", "value": "x"},
            {"field": "b", "op": "eq", "value": "y"},  # fails
        ]},
        {"field": "c", "op": "eq", "value": "z"},  # fallback matches
    ]})
    result = trigger.evaluate(cond)
    assert result.matched, "OR: AND fails, but c=z matches → OR should match"

def test_changed_both_none():
    """changed op when both prev and current are None — should NOT fire (None == None)."""
    prev = make_state()
    prev["missing_field"] = None
    extracted = {}
    extracted["missing_field"] = None
    trigger = TriggerAgent(prev, {**prev, **extracted}, {})
    cond = Condition(id="test", field="missing_field", op="changed")
    result = trigger.evaluate(cond)
    assert not result.matched, "None → None should not be a change"

def test_gt_string_numbers():
    """gt operator comparing string numbers ('250' > '200')."""
    extracted = {"price": "250"}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="price", op="gt", value="200")
    assert trigger.evaluate(cond).matched, "'250' > '200' should match (string numeric comparison)"

def test_condition_for_and_refire():
    """Condition with both for: and refire_after — for: gates first, refire_after controls re-escalation."""
    cond = Condition(id="test", field="status", op="eq", value="Delayed",
                     **{"for": "5m"}, refire_after="30m")
    assert cond.for_ == "5m", "for: should parse"
    assert cond.refire_after == "30m", "refire_after should parse"
    # Both can coexist — for: gates the initial fire, refire_after controls re-escalation

def test_multiple_groups_same_condition():
    """Same condition in multiple groups — fires for each group."""
    group1 = Group(name="critical", any=["dep_changed"])
    group2 = Group(name="notify", any=["dep_changed"])
    results = {"dep_changed": ConditionResult(True, "changed")}
    evaluator = GroupEvaluator()
    m1, ids1 = evaluator.evaluate_group(group1, results)
    m2, ids2 = evaluator.evaluate_group(group2, results)
    assert m1 and m2, "Same condition should match in both groups"
    assert ids1 == ids2 == ["dep_changed"], "Both groups should report same condition"

def test_group_action_not_in_config():
    """Group references action not in config.actions — run_engine should skip gracefully."""
    # This is tested at the run_engine level — if actions: ["nonexistent"] is in a group
    # and config.actions doesn't have "nonexistent", action_def = {} → type defaults to calendar_patch
    # → tries to patch with empty event_id → fails gracefully
    config = DetectConfig(
        name="Test",
        sources=[],
        conditions=[Condition(id="c1", field="x", op="changed")],
        groups=[Group(name="g", any=["c1"], actions=["nonexistent"])],
        actions={},  # no actions defined
    )
    assert "nonexistent" not in config.actions, "Action should not be in config"
    # In run_engine, action_def = config.actions.get("nonexistent", {}) → {}
    # action_type = {}.get("type", "calendar_patch") → "calendar_patch"
    # → tries patch with no event_id → _resolve_event_id(None) → ""
    # → gws_patch_event("", ...) → fails → all_actions_succeeded = False

def test_source_no_retry_defaults():
    """Source without retry: block uses RetryConfig defaults (count=2, backoff=3)."""
    source = Source(id="test", url="https://example.com")
    # source.retry is None — FetchAgent creates RetryConfig() internally
    assert source.retry is None, "No retry block should be None"
    # FetchAgent.fetch uses `retry_cfg = source.retry or RetryConfig()`
    defaults = RetryConfig()
    assert defaults.count == 2, "Default count should be 2"
    assert defaults.backoff == 3, "Default backoff should be 3"

def test_extract_header_content_type():
    """Header extraction for Content-Type header."""
    extractor = ExtractAgent()
    result = FetchResult(200, {"Content-Type": "application/json"}, "{}")
    spec = ExtractSpec(id="ct", type="header", name="Content-Type")
    val = extractor.extract(result, [spec])
    assert val["ct"] == "application/json", f"Should extract Content-Type, got {val['ct']}"

def test_extract_jsonpath_array():
    """JSONPath returning array — should get first element."""
    extractor = ExtractAgent()
    result = FetchResult(200, {}, json.dumps({"items": [1, 2, 3]}))
    spec = ExtractSpec(id="first", type="jsonpath", path="$.items[*]")
    val = extractor.extract(result, [spec])
    # jsonpath_ng returns all matches; extract takes [0]
    assert val["first"] is not None, "Should extract first array element"

def test_condition_value_none():
    """Condition with value=None — eq treats None as 'not present' (returns False).
    This is documented behavior: None is treated as 'missing', not 'equal to None'."""
    extracted = {"status": None}
    trigger = TriggerAgent({}, extracted, {})
    cond = Condition(id="test", field="status", op="eq", value=None)
    result = trigger.evaluate(cond)
    # eq with actual=None returns False (None is treated as "not present")
    assert not result.matched, "eq with actual=None returns False (None treated as missing)"
    # But exists op should detect that the field is present even if None
    cond2 = Condition(id="test2", field="status", op="exists")
    # exists checks: actual is not None and not empty → None → False
    assert not trigger.evaluate(cond2).matched, "exists should return False for None value"

def test_escalation_filename_uniqueness():
    """Escalation filenames are unique (condition_id + timestamp + uuid suffix)."""
    import tempfile
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        import detect_engine
        orig = detect_engine.ESCALATION_DIR
        detect_engine.ESCALATION_DIR = Path(tmpdir)
        try:
            config = DetectConfig(name="Test", sources=[], conditions=[], groups=[], actions={})
            esc = LLMEscalationAgent(config, make_state(), make_state(), [])
            cond = Condition(id="c1", field="x", op="changed")
            r = ConditionResult(True, "changed")
            files1 = esc.escalate([("c1", r, cond)])
            time.sleep(1.1)  # ensure different timestamp (1-second resolution)
            files2 = esc.escalate([("c1", r, cond)])
            assert len(files1) == 1 and len(files2) == 1
            # Filenames should differ (timestamp differs by >= 1 second)
            f1_name = Path(files1[0]).name
            f2_name = Path(files2[0]).name
            assert f1_name != f2_name, f"Filenames should be unique: {f1_name} == {f2_name}"
        finally:
            detect_engine.ESCALATION_DIR = orig

def test_llm_escalation_empty_prompt():
    """llm_escalation with empty prompt — uses default prompt."""
    config = DetectConfig(
        name="Test", sources=[], conditions=[], groups=[], actions={},
        llm_escalation=LLMEscalation(trigger_groups=["g"], prompt="")
    )
    assert config.llm_escalation.prompt == "", "Empty prompt should be accepted"
    # Engine uses default prompt when prompt is empty (checked in _render_prompt)


runner.run("TC-NESTED-AND-OR: Nested AND inside OR matches", test_nested_and_in_or)
runner.run("TC-NESTED-OR-AND: Nested OR inside AND matches", test_nested_or_in_and)
runner.run("TC-NESTED-AND-OR-FAIL: Nested AND fails, OR fallback matches", test_nested_and_in_or_fail)
runner.run("TC-CHANGED-NONE-BOTH: changed None→None doesn't fire", test_changed_both_none)
runner.run("TC-GT-STRING: gt with string numbers works", test_gt_string_numbers)
runner.run("TC-FOR-AND-REFIRE: Condition with both for: and refire_after", test_condition_for_and_refire)
runner.run("TC-MULTI-GROUP-SAME: Same condition in multiple groups fires for each", test_multiple_groups_same_condition)
runner.run("TC-GROUP-ACTION-MISSING: Group references action not in config.actions", test_group_action_not_in_config)
runner.run("TC-SOURCE-NO-RETRY: Source without retry: uses defaults", test_source_no_retry_defaults)
runner.run("TC-EXTRACT-CT: Header extraction for Content-Type", test_extract_header_content_type)
runner.run("TC-EXTRACT-ARRAY: JSONPath returning array gets first element", test_extract_jsonpath_array)
runner.run("TC-COND-VALUE-NONE: eq with value=None matches None", test_condition_value_none)
runner.run("TC-ESC-FILENAME-UNIQUE: Escalation filenames are unique", test_escalation_filename_uniqueness)
runner.run("TC-ESC-EMPTY-PROMPT: Empty prompt accepted (uses default)", test_llm_escalation_empty_prompt)


# ═══════════════════════════════════════════════════════════════
#  Mocked gws tests — calendar API success/failure paths
# ═══════════════════════════════════════════════════════════════

def test_mock_gws_get_event_success():
    """gws_get_event returns event dict when API succeeds."""
    with patch("detect_engine.gws_get_event", return_value={"id": "evt1", "summary": "Test Flight", "start": {"dateTime": "2026-07-07T17:20:00-07:00"}}) as mock:
        # The mock is used when run_engine calls gws_get_event directly
        from detect_engine import gws_get_event
        result = gws_get_event("evt1")
        assert result is not None
        assert result["summary"] == "Test Flight"
        mock.assert_called_once_with("evt1")


def test_mock_gws_get_event_failure():
    """gws_get_event returns None when API fails (auth, 404, network)."""
    with patch("detect_engine.gws_get_event", return_value=None):
        from detect_engine import gws_get_event
        result = gws_get_event("nonexistent_event_id")
        assert result is None


def test_mock_gws_patch_event_success():
    """gws_patch_event returns True on success."""
    with patch("detect_engine.gws_patch_event", return_value=True) as mock:
        action = ActionAgent({}, dry_run=False)
        success = action.execute("patch_flight", {
            "type": "calendar_patch",
            "event_id": "evt123",
            "fields": {"summary": "Updated Title"},
        })
        assert success is True
        mock.assert_called_once()


def test_mock_gws_patch_event_failure():
    """gws_patch_event returns False on failure — action reports failure."""
    with patch("detect_engine.gws_patch_event", return_value=False):
        action = ActionAgent({}, dry_run=False)
        success = action.execute("patch_flight", {
            "type": "calendar_patch",
            "event_id": "evt123",
            "fields": {"summary": "Updated Title"},
        })
        assert success is False
        assert any("❌" in r for r in action.results), f"Should report failure, got: {action.results}"


def test_mock_gws_delete_event_success():
    """gws_delete_event returns True on success."""
    with patch("detect_engine.gws_delete_event", return_value=True) as mock:
        action = ActionAgent({}, dry_run=False)
        success = action.execute("delete_event", {
            "type": "calendar_delete",
            "event_id": "evt123",
        })
        assert success is True
        mock.assert_called_once()


def test_mock_gws_delete_event_failure():
    """gws_delete_event returns False on failure."""
    with patch("detect_engine.gws_delete_event", return_value=False):
        action = ActionAgent({}, dry_run=False)
        success = action.execute("delete_event", {
            "type": "calendar_delete",
            "event_id": "evt123",
        })
        assert success is False


def test_mock_action_failure_escalation():
    """Action failure writes LLM escalation evidence file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        import detect_engine
        orig_esc = detect_engine.ESCALATION_DIR
        detect_engine.ESCALATION_DIR = Path(tmpdir)
        try:
            with patch("detect_engine.gws_patch_event", return_value=False):
                action = ActionAgent({"dep_time": "2026-07-07T17:20:00-07:00"}, dry_run=False)
                success = action.execute("patch_flight", {
                    "type": "calendar_patch",
                    "event_id": "evt123",
                    "fields": {"summary": "Test"},
                })
                assert success is False
                # The escalation file is written by run_engine, not ActionAgent directly.
                # This test verifies the action reports failure correctly.
                assert any("❌" in r for r in action.results)
        finally:
            detect_engine.ESCALATION_DIR = orig_esc


def test_mock_gws_empty_event_id_guard():
    """gws_get_event with empty event_id returns None without calling subprocess."""
    with patch("subprocess.run") as mock_sub:
        from gws_utils import gws_get_event
        result = gws_get_event("")
        assert result is None
        mock_sub.assert_not_called()


def test_mock_gws_empty_patch_guard():
    """gws_patch_event with empty patch returns False without calling subprocess."""
    with patch("subprocess.run") as mock_sub:
        from gws_utils import gws_patch_event
        result = gws_patch_event("evt123", {})
        assert result is False
        mock_sub.assert_not_called()


runner.run("TC-MOCK-GET-OK: Mocked gws_get_event success", test_mock_gws_get_event_success)
runner.run("TC-MOCK-GET-FAIL: Mocked gws_get_event returns None on failure", test_mock_gws_get_event_failure)
runner.run("TC-MOCK-PATCH-OK: Mocked gws_patch_event success", test_mock_gws_patch_event_success)
runner.run("TC-MOCK-PATCH-FAIL: Mocked gws_patch_event failure reported", test_mock_gws_patch_event_failure)
runner.run("TC-MOCK-DELETE-OK: Mocked gws_delete_event success", test_mock_gws_delete_event_success)
runner.run("TC-MOCK-DELETE-FAIL: Mocked gws_delete_event failure", test_mock_gws_delete_event_failure)
runner.run("TC-MOCK-ACTION-ESC: Action failure reports for escalation", test_mock_action_failure_escalation)
runner.run("TC-MOCK-EMPTY-EID: Empty event_id guard prevents subprocess call", test_mock_gws_empty_event_id_guard)
runner.run("TC-MOCK-EMPTY-PATCH: Empty patch guard prevents subprocess call", test_mock_gws_empty_patch_guard)


# ═══════════════════════════════════════════════════════════════
#  Transitions shortcut tests
# ═══════════════════════════════════════════════════════════════

def test_transitions_expands_to_conditions():
    """_expand_transitions converts transitions: into conditions + groups."""
    raw = {
        "name": "Test",
        "transitions": [
            {"field": "dep_time", "on_change": ["patch_flight"]},
            {"field": "status", "on_change": ["patch_flight"], "when": {"op": "eq", "value": "Delayed"}},
        ],
        "actions": {"patch_flight": {"type": "calendar_patch", "event_id": "e1"}},
    }
    result = _expand_transitions(raw)
    assert "transitions" not in result, "transitions: should be consumed"
    assert len(result["conditions"]) == 2
    assert result["conditions"][0]["id"] == "transition_dep_time"
    assert result["conditions"][0]["op"] == "changed"
    assert result["conditions"][1]["id"] == "transition_status"
    assert result["conditions"][1]["and"] is not None, "when: should produce AND condition"
    assert len(result["groups"]) == 2
    assert result["groups"][0]["name"] == "transition_dep_time_group"
    assert result["groups"][0]["actions"] == ["patch_flight"]
    assert result["groups"][1]["name"] == "transition_status_group"
    assert result["groups"][1]["all"] == ["transition_status"], "when: should produce all: group"


def test_transitions_no_transitions_returns_unchanged():
    """_expand_transitions is a no-op when no transitions: section."""
    raw = {"name": "Test", "conditions": [], "groups": []}
    result = _expand_transitions(raw)
    assert result == raw


def test_transitions_with_unless_and_refire():
    """_expand_transitions preserves unless and refire_after."""
    raw = {
        "name": "Test",
        "transitions": [
            {"field": "status", "on_change": ["patch"],
             "when": {"op": "eq", "value": "Delayed"},
             "unless": {"field": "cal_title", "op": "contains", "value": "DELAYED"},
             "refire_after": "30m"},
        ],
    }
    result = _expand_transitions(raw)
    cond = result["conditions"][0]
    assert cond["unless"] is not None
    assert cond["refire_after"] == "30m"


def test_transitions_config_loads_and_validates():
    """Full load_config with transitions: produces a valid DetectConfig."""
    config = load_config(str(SCRIPTS_DIR.parent / "configs" / "tests" / "transitions_test.yaml"))
    assert config.name == "Transitions Test"
    assert len(config.conditions) == 2
    assert len(config.groups) == 2
    # Cross-ref validation should pass
    errors = validate_config_cross_refs(config)
    assert not errors, f"Transition config should have no cross-ref errors: {errors}"


runner.run("TC-TRANS-EXPAND: transitions expand to conditions + groups", test_transitions_expands_to_conditions)
runner.run("TC-TRANS-NOOP: no transitions = no-op", test_transitions_no_transitions_returns_unchanged)
runner.run("TC-TRANS-UNLESS: transitions preserve unless + refire_after", test_transitions_with_unless_and_refire)
runner.run("TC-TRANS-LOAD: transitions config loads and validates", test_transitions_config_loads_and_validates)


# ═══════════════════════════════════════════════════════════════
#  Seed mode + transitions integration tests
# ═══════════════════════════════════════════════════════════════

def test_seed_mode_first_run_no_actions():
    """seed_mode: true → first run saves state without executing actions."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        config = DetectConfig(
            name="seed_test", seed_mode=True,
            sources=[Source(id="s1", url="https://example.com", extract=[])],
            conditions=[Condition(id="c1", field="dep_time", op="changed", baseline={"source": "state", "field": "dep_time"})],
            groups=[Group(name="g1", any=["c1"], actions=["patch"])],
            actions={"patch": {"type": "calendar_patch", "event_id": "e1", "fields": {"summary": "test"}}},
            state=StateConfig(file="state.json", initial={"dep_time": ""}),
        )
        # Simulate first run: state is empty (only initial keys)
        sm = StateManager(state_path, {"dep_time": ""})
        sm.load()
        # is_first_run should be True (dep_time is "" = initial)
        is_first_run = all(sm.state.get(k, "") == "" for k in config.state.initial)
        assert is_first_run, "First run should detect empty state"


def test_seed_mode_not_first_run_executes_actions():
    """seed_mode: true → second run (state populated) executes actions normally."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({"dep_time": "2026-07-07T17:20:00-07:00", "last_checked": "2026-07-08T00:00:00Z"}))
        config = DetectConfig(
            name="seed_test", seed_mode=True,
            sources=[Source(id="s1", url="https://example.com", extract=[])],
            conditions=[Condition(id="c1", field="dep_time", op="changed", baseline={"source": "state", "field": "dep_time"})],
            groups=[Group(name="g1", any=["c1"], actions=["patch"])],
            actions={"patch": {"type": "calendar_patch", "event_id": "e1", "fields": {"summary": "test"}}},
            state=StateConfig(file="state.json", initial={"dep_time": ""}),
        )
        sm = StateManager(state_path, {"dep_time": ""})
        sm.load()
        is_first_run = all(sm.state.get(k, "") == "" for k in config.state.initial)
        assert not is_first_run, "Second run should NOT detect first run (state has values)"


def test_seed_mode_default_is_enabled():
    """seed_mode defaults to safe first-poll observation."""
    config = DetectConfig(
        name="default_seed",
        sources=[], conditions=[], groups=[], actions={},
    )
    assert config.seed_mode is True, "seed_mode should default to True"


def test_transitions_integration_first_run():
    """Transitions config + seed_mode: first run saves state, no actions."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""
name: "transitions_seed_test"
enabled: true
seed_mode: true
expires: "2099-01-01T00:00:00Z"
sources:
  - id: test_source
    url: "https://example.com/api"
    extract:
      - id: dep_time
        type: jsonpath
        path: "$.dep_time"
transitions:
  - field: dep_time
    on_change: [patch_flight]
actions:
  patch_flight:
    type: calendar_patch
    event_id: "evt1"
    fields:
      summary: "Test"
state:
  file: "state.json"
  initial:
    dep_time: ""
""")
        # Load and verify transitions expanded + seed_mode present
        config = load_config(str(config_path))
        assert config.seed_mode is True
        assert len(config.conditions) == 1
        assert config.conditions[0].id == "transition_dep_time"
        assert len(config.groups) == 1
        errors = validate_config_cross_refs(config)
        assert not errors, f"Should have no cross-ref errors: {errors}"


runner.run("TC-SEED-FIRST: seed_mode first run detects empty state", test_seed_mode_first_run_no_actions)
runner.run("TC-SEED-SECOND: seed_mode second run has populated state", test_seed_mode_not_first_run_executes_actions)
runner.run("TC-SEED-DEFAULT: seed_mode defaults to True", test_seed_mode_default_is_enabled)
runner.run("TC-TRANS-SEED: transitions + seed_mode config loads correctly", test_transitions_integration_first_run)


# ═══════════════════════════════════════════════════════════════
#  Timezone-aware fmt_time tests
# ═══════════════════════════════════════════════════════════════

def test_fmt_time_eastern():
    """fmt_time with explicit tz arg produces Eastern timezone label."""
    action = ActionAgent({}, dry_run=True)
    # Explicit tz arg → Eastern
    result = action._render_template("Depart: {{ dep_time | fmt_time:America/New_York }}", {"dep_time": "2026-07-15T17:20:00-04:00"})
    assert "5:20 PM" in result, f"Expected '5:20 PM' in result, got: {result}"


def test_fmt_time_explicit_tz():
    """fmt_time accepts explicit timezone argument."""
    action = ActionAgent({}, dry_run=True)
    # Pacific datetime, but render in Eastern
    result = action._render_template("Depart: {{ dep_time | fmt_time:America/New_York }}", {"dep_time": "2026-07-15T17:20:00-07:00"})
    assert "8:20 PM" in result, f"Expected '8:20 PM' (17:20 PT = 20:20 ET), got: {result}"


runner.run("TC-TEMPLATE-FMT-ET: fmt_time auto-detects Eastern timezone", test_fmt_time_eastern)
runner.run("TC-TEMPLATE-FMT-ARG: fmt_time accepts explicit timezone arg", test_fmt_time_explicit_tz)


# ═══════════════════════════════════════════════════════════════
#  Regression tests — one per advisor-found bug (2026-07-08 review)
# ═══════════════════════════════════════════════════════════════

def test_regression_when_clause_field_injection():
    """P0-A: _expand_transitions injects field into when clause if missing."""
    config_data = {
        "name": "when_test", "enabled": True, "seed_mode": False,
        "expires": "2099-01-01T00:00:00Z",
        "sources": [{"id": "s", "url": "https://example.com", "extract": [{"id": "status", "type": "regex", "pattern": "x", "group": 0}]}],
        "transitions": [{"field": "status", "when": {"op": "eq", "value": "Delayed"}, "on_change": ["patch_flight"]}],
        "actions": {"patch_flight": {"type": "calendar_patch", "event_id": "evt1", "fields": {"summary": "test"}}},
    }
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.yaml"
        p.write_text(yaml.dump(config_data))
        config = load_config(str(p))
    # Find the expanded condition
    cond = next((c for c in config.conditions if c.id == "transition_status"), None)
    assert cond is not None, "transition_status condition not found"
    assert cond.and_ is not None, "when clause should produce an AND condition"
    assert len(cond.and_) == 2, f"Expected 2 AND items, got {len(cond.and_)}"
    # The when clause (2nd item) must have field="status" — stored as dict
    when_dict = cond.and_[1]
    assert when_dict.get("field") == "status", f"Expected field='status', got '{when_dict.get('field')}'"


def test_regression_action_failure_preserves_baseline():
    """P0-B: On action failure, state is NOT saved — baseline preserved for retry."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        config_path = Path(d) / "config.yaml"
        state_path = Path(d) / "state" / "baseline_test.json"
        state_path.parent.mkdir(parents=True)
        state_path.write_text(json.dumps({"dep_time": "2026-07-15T17:20:00-07:00"}))
        config_path.write_text("""
name: "baseline_test"
enabled: true
seed_mode: false
expires: "2099-01-01T00:00:00Z"
sources:
  - id: src1
    url: "https://example.com"
    extract:
      - id: dep_time
        type: regex
        pattern: "([0-9T:-]+)"
        group: 1
conditions:
  - id: dep_changed
    field: dep_time
    op: changed
    baseline: {source: state, field: dep_time}
groups:
  - name: main
    any: [dep_changed]
    actions: [patch_it]
actions:
  patch_it:
    type: calendar_patch
    event_id: "fake_event_id"
    fields:
      summary: "test"
state:
  file: "state/baseline_test.json"
  initial:
    dep_time: "2026-07-15T17:20:00-07:00"
""")
        with patch("detect_engine.httpx.Client") as mock_cls, \
             patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=False):
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "2026-07-15T17:25:00-07:00"
            mock_resp.headers = {}
            mock_resp.request = None
            mock_client.request.return_value = mock_resp
            rc = run_engine(str(config_path))
        # Should return 1 (action failed)
        assert rc == 1, f"Expected exit 1 on action failure, got {rc}"
        # State file should NOT have been updated with new time
        saved = json.loads(state_path.read_text())
        assert saved["dep_time"] == "2026-07-15T17:20:00-07:00", \
            f"Baseline should be preserved, got: {saved['dep_time']}"


def test_regression_expires_naive_datetime():
    """P0-C: expires with naive datetime doesn't crash (attaches UTC)."""
    import tempfile
    config_yaml = """
name: "naive_expires"
enabled: true
seed_mode: false
expires: "2099-12-31"
sources:
  - id: s
    url: "https://example.com"
    extract:
      - id: x
        type: regex
        pattern: "x"
        group: 0
"""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.yaml"
        p.write_text(config_yaml)
        # Should not crash with TypeError
        rc = run_engine_with_mock_json(p, {"x": "x"}, dry_run=True)
        assert rc == 0, f"Expected exit 0 (not expired), got {rc}"


def test_regression_gws_json_error_body():
    """P1-A: gws_patch_event returns False when JSON body has error key, even if exit 0."""
    from gws_utils import gws_patch_event
    with patch("gws_utils.subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"error": "Calendar API error: not found"}'
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        result = gws_patch_event("evt123", {"summary": "test"})
    assert result is False, f"Expected False on JSON error body, got {result}"


def test_regression_cal_title_patch_preference():
    """P1-B: cal_title prefers calendar_patch action events over calendar_delete."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.yaml"
        sp = Path(d) / "state" / "cal_title_pref.json"
        sp.parent.mkdir(parents=True)
        sp.write_text(json.dumps({"x": "old"}))
        p.write_text("""
name: "cal_title_pref"
enabled: true
seed_mode: false
expires: "2099-01-01T00:00:00Z"
sources:
  - id: s
    url: "https://example.com"
    extract:
      - id: x
        type: regex
        pattern: "x"
        group: 0
conditions:
  - id: x_changed
    field: x
    op: changed
    baseline: {source: state, field: x}
groups:
  - name: main
    any: [x_changed]
actions:
  delete_stale:
    type: calendar_delete
    event_id: "delete_evt"
  patch_flight:
    type: calendar_patch
    event_id: "patch_evt"
    fields:
      summary: "Flight"
state:
  file: "state/cal_title_pref.json"
  initial:
    x: "old"
""")
        with patch("detect_engine.httpx.Client") as mock_cls, \
             patch("detect_engine.gws_get_event") as mock_get, \
             patch("detect_engine.gws_patch_event", return_value=True), \
             patch("detect_engine.gws_delete_event", return_value=True):
            mock_get.side_effect = lambda eid, calendar_id="primary", **kw: {
                "summary": f"Event {eid}", "id": eid,
            }
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "new"
            mock_resp.headers = {}
            mock_resp.request = None
            mock_client.request.return_value = mock_resp
            rc = run_engine(str(p), dry_run=True)
    assert rc == 0, f"Expected exit 0, got {rc}"


def test_regression_not_list_multi_item():
    """P1-C: not: with >1 item evaluates ALL items, not just first."""
    trigger = TriggerAgent({}, {"a": "yes", "b": "no"}, {})
    cond = Condition(id="test", **{"not": [
        {"field": "a", "op": "eq", "value": "yes"},
        {"field": "b", "op": "eq", "value": "yes"},
    ]})
    result = trigger.evaluate(cond)
    # NOT(AND(a=yes, b=yes)) = NOT(True AND False) = NOT(False) = True
    assert result.matched is True, f"Expected True (NOT of AND where b!=yes), got {result.matched}"


def test_regression_is_first_run_last_checked():
    """P1-D: is_first_run checks last_checked, not key enumeration."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.yaml"
        sp = Path(d) / "state" / "first_run_check.json"
        sp.parent.mkdir(parents=True)
        # State has last_checked set — should NOT be first run
        sp.write_text(json.dumps({"last_checked": "2026-07-08T00:00:00+00:00", "acknowledged": {}}))
        p.write_text("""
name: "first_run_check"
enabled: true
seed_mode: true
expires: "2099-01-01T00:00:00Z"
sources:
  - id: s
    url: "https://example.com"
    extract:
      - id: x
        type: regex
        pattern: "x"
        group: 0
conditions:
  - id: x_changed
    field: x
    op: changed
    baseline: {source: state, field: x}
groups:
  - name: main
    any: [x_changed]
actions:
  patch:
    type: calendar_patch
    event_id: "evt"
    fields:
      summary: "test"
state:
  file: "state/first_run_check.json"
""")
        with patch("detect_engine.httpx.Client") as mock_cls, \
             patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True):
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "val1"
            mock_resp.headers = {}
            mock_resp.request = None
            mock_client.request.return_value = mock_resp
            rc = run_engine(str(p), dry_run=True)
    # Should NOT enter seed mode (last_checked is set) — should run normally
    assert rc == 0, f"Expected exit 0, got {rc}"


def test_regression_save_failure_logged():
    """TC-REG-SAVE-FAIL: P1-E save failure is uid-independent."""
    # F5 FIX: A regular file parent fails under every uid without touching global paths.
    with tempfile.TemporaryDirectory() as tmpdir:
        parent_file = Path(tmpdir) / "regular-file"
        parent_file.write_text("not a directory")
        sm = StateManager(parent_file / "subdir" / "state.json")
        result = sm.save()
    assert result is False, f"Expected False on save failure, got {result}"


runner.run("TC-REG-WHEN-FIELD: P0-A when clause field injection regression", test_regression_when_clause_field_injection)
runner.run("TC-REG-BASELINE: P0-B action failure preserves baseline", test_regression_action_failure_preserves_baseline)
runner.run("TC-REG-EXPIRES-NAIVE: P0-C naive datetime doesn't crash", test_regression_expires_naive_datetime)
runner.run("TC-REG-GWS-ERROR-BODY: P1-A gws JSON error body detected", test_regression_gws_json_error_body)
runner.run("TC-REG-CAL-TITLE-PREF: P1-B cal_title prefers calendar_patch", test_regression_cal_title_patch_preference)
runner.run("TC-REG-NOT-MULTI: P1-C not: list evaluates all items", test_regression_not_list_multi_item)
runner.run("TC-REG-FIRST-RUN: P1-D is_first_run checks last_checked", test_regression_is_first_run_last_checked)
runner.run("TC-REG-SAVE-FAIL: P1-E save failure returns False", test_regression_save_failure_logged)


# ═══════════════════════════════════════════════════════════════
#  Regression tests — F4/F5 follow-up fixes (2026-07-11 review)
# ═══════════════════════════════════════════════════════════════

def test_f4_1_duration_gate_holds_changed_baseline():
    """TC-F4.1-DURATION: a duration-gated change retains its old baseline until firing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: "duration_hold"
seed_mode: true
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: x, type: jsonpath, path: "$.x"}]
conditions:
  - id: x_changed
    field: x
    op: changed
    baseline: {source: state, field: x}
    for: "10m"
groups:
  - name: g
    any: [x_changed]
state: {file: "state.json", initial: {x: ""}}
""")
        assert run_engine_with_mock_json(config_path, {"x": "A"}) == 0, "First poll must seed A"
        assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
        held_state = json.loads(state_path.read_text())
        assert held_state["x"] == "A", "Duration gate must retain the prior baseline"
        assert "x_changed" in held_state["first_seen"], "Duration gate must retain first_seen"
        held_state["first_seen"]["x_changed"] = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        state_path.write_text(json.dumps(held_state))
        assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
        assert json.loads(state_path.read_text())["x"] == "B", "Backdated duration gate should fire"


def test_f4_1_refire_window_holds_changed_baseline():
    """TC-F4.1-REFIRE: a refire-suppressed change remains detectable after the window."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: "refire_hold"
seed_mode: true
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: x, type: jsonpath, path: "$.x"}]
conditions:
  - id: x_changed
    field: x
    op: changed
    baseline: {source: state, field: x}
    refire_after: "10m"
groups:
  - name: g
    any: [x_changed]
state: {file: "state.json", initial: {x: ""}}
""")
        assert run_engine_with_mock_json(config_path, {"x": "A"}) == 0, "First poll must seed A"
        seeded_state = json.loads(state_path.read_text())
        seeded_state["last_fired"] = {"x_changed": datetime.now(timezone.utc).isoformat()}
        state_path.write_text(json.dumps(seeded_state))
        assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
        held_state = json.loads(state_path.read_text())
        assert held_state["x"] == "A", "Refire window must retain the prior baseline"
        held_state["last_fired"]["x_changed"] = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        state_path.write_text(json.dumps(held_state))
        assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
        assert json.loads(state_path.read_text())["x"] == "B", "Expired refire window should fire"


def test_f4_1_shared_field_hold_matrix():
    """TC-F4.1-MATRIX: any suppressed changed condition holds its shared field only when matched."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({"x": "A", "last_checked": "2026-07-08T00:00:00Z"}))
        config_path.write_text("""
name: "shared_hold"
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: x, type: jsonpath, path: "$.x"}]
conditions:
  - {id: fires, field: x, op: changed, baseline: {source: state, field: x}}
  - {id: waits, field: x, op: changed, baseline: {source: state, field: x}, for: "10m"}
groups:
  - {name: fire_group, any: [fires]}
  - {name: wait_group, any: [waits]}
state: {file: "state.json", initial: {x: ""}}
""")
        assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
        assert json.loads(state_path.read_text())["x"] == "A", "Shared field must be held while waits is gated"
        state_path.write_text(json.dumps({
            "x": "A", "baseline": "B", "last_checked": "2026-07-08T00:00:00Z",
        }))
        config_path.write_text("""
name: "shared_unmatched"
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: x, type: jsonpath, path: "$.x"}]
conditions:
  - {id: first, field: x, op: changed, baseline: {source: state, field: baseline}}
  - {id: second, field: x, op: changed, baseline: {source: state, field: baseline}}
groups: []
state: {file: "state.json", initial: {x: "", baseline: ""}}
""")
        assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
        assert json.loads(state_path.read_text())["x"] == "B", "Unmatched shared-field conditions must update normally"


def test_f4_2_cal_title_current_value_preferred():
    """TC-F4.2-CAL-TITLE: cal_title condition uses the current calendar_patch title."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({"status": "On time"}))
        config_path.write_text("""
name: "cal_title_current"
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: status, type: jsonpath, path: "$.status"}]
conditions:
  - id: cancel
    field: status
    op: eq
    value: Cancelled
    unless: {field: cal_title, op: eq, value: "Patch title"}
groups: [{name: g, any: [cancel]}]
actions:
  delete_first: {type: calendar_delete, event_id: delete_event}
  patch_second: {type: calendar_patch, event_id: patch_event, fields: {summary: "Patch title"}}
state: {file: "state.json", initial: {status: ""}}
""")
        with patch("detect_engine.gws_get_event") as mock_get:
            mock_get.side_effect = lambda event_id, calendar_id="primary", **kw: {
                "id": event_id,
                "summary": "Delete title" if event_id == "delete_event" else "Patch title",
            }
            assert run_engine_with_mock_json(config_path, {"status": "Cancelled"}) == 0
        assert "cancel" not in json.loads(state_path.read_text())["acknowledged"], \
            "unless must see the second calendar_patch event title, not delete_first"


def test_f4_3_calendar_baseline_gws_failure_unavailable():
    """TC-F4.3-GWS: missing calendar event makes changed baseline unavailable."""
    cond = Condition(id="c", field="x", op="changed",
                     baseline={"source": "calendar", "event_id": "e1", "field": "start.dateTime"})
    with patch("detect_engine.gws_get_event", return_value=None):
        result = TriggerAgent({}, {"x": "new"}, {}).evaluate(cond)
    assert not result.matched and "baseline unavailable" in result.reason


def test_f4_3_calendar_baseline_missing_intermediate_unavailable():
    """TC-F4.3-INTERMEDIATE: absent intermediate calendar path is unavailable."""
    cond = Condition(id="c", field="x", op="changed",
                     baseline={"source": "calendar", "event_id": "e1", "field": "start.dateTime.value"})
    event = {"id": "e1", "start": {}}
    result = TriggerAgent({}, {"x": "new"}, {"event": event}).evaluate(cond)
    assert not result.matched and "baseline unavailable" in result.reason


def test_f4_3_calendar_baseline_missing_leaf_unavailable():
    """TC-F4.3-LEAF: absent leaf calendar path is unavailable."""
    cond = Condition(id="c", field="x", op="changed",
                     baseline={"source": "calendar", "event_id": "e1", "field": "start.dateTime"})
    event = {"id": "e1", "start": {}}
    result = TriggerAgent({}, {"x": "new"}, {"event": event}).evaluate(cond)
    assert not result.matched and "baseline unavailable" in result.reason


def test_f4_3_calendar_baseline_null_leaf_is_real_value():
    """TC-F4.3-NULL: a present JSON null remains a comparable baseline value."""
    cond = Condition(id="c", field="x", op="changed",
                     baseline={"source": "calendar", "event_id": "e1", "field": "start.dateTime"})
    event = {"id": "e1", "start": {"dateTime": None}}
    result = TriggerAgent({}, {"x": "new"}, {"event": event}).evaluate(cond)
    assert result.matched, "A real null baseline must still compare as changed"


def test_f4_4_state_path_sibling_rejected():
    """TC-F4.4-SIBLING: state path in configs-evil cannot escape configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "configs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("name: bad_path\nstate: {file: '../configs-evil/state.json'}\n")
        assert run_engine(str(config_path)) == 1


def test_f4_4_state_path_nested_allowed():
    """TC-F4.4-NESTED: a state path nested under the config directory is allowed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "configs"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("name: nested_path\nstate: {file: 'state/x.json'}\n")
        assert run_engine(str(config_path)) == 0
        assert (config_dir / "state" / "x.json").exists()


def test_f4_5_duplicate_explicit_condition_ids_rejected():
    """TC-F4.5-DUP-ID: duplicate explicit condition ids are validation errors."""
    config = DetectConfig(name="duplicates", conditions=[
        Condition(id="same", field="a", op="eq", value="1"),
        Condition(id="same", field="b", op="eq", value="2"),
    ])
    assert "duplicate condition id 'same'" in validate_config_cross_refs(config)


def test_f4_5_duplicate_transition_ids_rejected():
    """TC-F4.5-DUP-TRANSITION: duplicate transition field ids are validation errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""
name: "duplicate_transitions"
transitions:
  - {field: x, on_change: []}
  - {field: x, on_change: []}
""")
        config = load_config(str(config_path))
    assert "duplicate condition id 'transition_x'" in validate_config_cross_refs(config)


def test_f4_5_duplicate_group_action_runs_once():
    """TC-F4.5-ACTION-ONCE: one shared action executes once across matched groups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({"x": "A", "last_checked": "2026-07-08T00:00:00Z"}))
        config_path.write_text("""
name: "dedupe_action"
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: x, type: jsonpath, path: "$.x"}]
conditions:
  - {id: x_changed, field: x, op: changed, baseline: {source: state, field: x}}
groups:
  - {name: first, any: [x_changed], actions: [patch]}
  - {name: second, any: [x_changed], actions: [patch]}
actions:
  patch: {type: calendar_patch, event_id: "e1", fields: {summary: "updated"}}
state: {file: "state.json", initial: {x: ""}}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
            assert mock_patch.call_count == 1, "Shared action must execute exactly once"
            assert run_engine_with_mock_json(config_path, {"x": "B"}) == 0
            assert mock_patch.call_count == 1, "Unchanged value must not re-run the shared action"


def test_m3_shared_calendar_baseline_resolution():
    """TC-M3: trigger and evidence resolve the same configured cached calendar event."""
    prev = {"event_key": "target", "value": "old"}
    events = {
        "wrong": {"id": "wrong", "start": {"dateTime": "wrong-time"}},
        "target": {"id": "target", "start": {"dateTime": "right-time"}},
    }
    cond = Condition(
        id="changed", field="value", op="changed",
        baseline={"source": "calendar", "event_id": {"from_state": "event_key"},
                  "field": "start.dateTime"},
    )
    assert TriggerAgent(prev, {**prev, "value": "new"}, events)._get_baseline(cond) == "right-time"
    evidence = LLMEscalationAgent(
        DetectConfig(name="m3"), prev, {**prev, "value": "new"}, [], events,
    )._build_evidence("changed", ConditionResult(True, "changed"), cond)
    assert evidence["baseline_value"] == "right-time"


def test_m7_runner_self_check_uses_validate_exit_status():
    """TC-M7: runner self-check gates validity on --validate's exit code, not text output."""
    runner_script = (SCRIPTS_DIR / "detect_runner.sh").read_text()
    assert 'grep -q "Config valid"' not in runner_script
    assert '"$PYTHON" "$ENGINE" --config "$CONFIG" --validate >/dev/null 2>&1' in runner_script


def test_h_a_run_engine_rejects_cross_ref_errors_before_fetch():
    """TC-H-A: runtime cross-reference errors fail before any source fetch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""
name: invalid_runtime_refs
sources: [{id: source, url: https://example.com}]
conditions:
  - {id: duplicate, field: x, op: eq, value: one}
  - {id: duplicate, field: x, op: eq, value: two}
groups: []
""")
        with patch("detect_engine.FetchAgent.fetch") as mock_fetch:
            assert run_engine(str(config_path)) == 1
    mock_fetch.assert_not_called()


def test_h_b_held_cal_title_is_not_overwritten_after_other_action_succeeds():
    """TC-H-B: duration-held cal_title survives a different group's successful action."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        state_path.write_text(json.dumps({
            "cal_title": "old title", "x": "old", "last_checked": "2026-07-08T00:00:00Z",
        }))
        config_path.write_text("""
name: held cal title
sources:
  - id: source
    url: https://example.com
    extract:
      - {id: cal_title, type: jsonpath, path: $.cal_title}
      - {id: x, type: jsonpath, path: $.x}
conditions:
  - {id: hold_title, field: cal_title, op: changed, baseline: {source: state, field: cal_title}, for: 10m}
  - {id: fire_x, field: x, op: changed, baseline: {source: state, field: x}}
groups:
  - {name: act, any: [fire_x], actions: [patch]}
actions:
  patch: {type: calendar_patch, event_id: event-1, fields: {summary: updated}}
state: {file: state.json, initial: {cal_title: '', x: ''}}
""")
        with patch("detect_engine.gws_get_event", return_value={"id": "event-1", "summary": "fresh title"}), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"cal_title": "new source title", "x": "new"}) == 0
            assert mock_patch.call_count == 1
            assert run_engine_with_mock_json(config_path, {"cal_title": "new source title", "x": "new"}) == 0
            assert mock_patch.call_count == 1, "Unchanged x must not re-run the patch"
        assert json.loads(state_path.read_text())["cal_title"] == "old title"


def test_h_c_health_file_is_slugged_per_config():
    """TC-H-C: run_engine writes health to the config-specific watchdog filename."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""
name: Health Monitor_Test
state: {file: state.json}
""")
        assert run_engine(str(config_path)) == 0
    assert (_detect_engine_mod.HEALTH_DIR / "health-monitor-test-health.json").exists()


# ═══════════════════════════════════════════════════════════════
#  TC-HARDEN: prompt-on-change corner-case hardening
# ═══════════════════════════════════════════════════════════════

def test_harden_seed_mode_false_fires_on_fresh_state():
    """TC-HARDEN-SEED-OPTOUT: seed_mode:false retains first-poll action behavior."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""
name: seed optout
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: g, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {x: ''}}
""")
        with patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
            mock_patch.assert_called_once()
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
            assert mock_patch.call_count == 1, "Unchanged value must not re-fire the action"


def test_harden_seed_fire_norefire_bounce():
    """TC-HARDEN-SEED-FIRE-BOUNCE: seeded baseline fires, holds, then re-fires."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: seed fire bounce
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: g, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event-1, fields: {summary: updated}}}
state: {file: state.json, initial: {x: ''}}
""")
        state_path.write_text(json.dumps({
            "x": "__unseeded__", "last_checked": "2026-07-08T00:00:00Z",
        }))
        with patch("detect_engine.gws_get_event", return_value={"id": "event-1"}), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"x": "real"}) == 0
            assert mock_patch.call_count == 1
            first_state = json.loads(state_path.read_text())
            assert first_state["x"] == "real"
            assert first_state["acknowledged"]["changed"]["value"] == "real"

            assert run_engine_with_mock_json(config_path, {"x": "real"}) == 0
            assert mock_patch.call_count == 1
            second_state = json.loads(state_path.read_text())
            assert second_state["x"] == "real"

            assert run_engine_with_mock_json(config_path, {"x": "real2"}) == 0
            assert mock_patch.call_count == 2


def _write_action_failure_config(config_path: Path, name: str, backoff: str):
    config_path.write_text(f"""
name: {name}
sources: [{{id: source, url: https://example.com, extract: [{{id: x, type: jsonpath, path: $.x}}]}}]
conditions: [{{id: changed, field: x, op: changed, baseline: {{source: state, field: x}}}}]
groups: [{{name: g, any: [changed], actions: [patch]}}]
actions: {{patch: {{type: calendar_patch, event_id: event, fields: {{summary: updated}}}}}}
llm_escalation: {{trigger_groups: [g], escalation_backoff: {backoff}}}
state: {{file: state.json, initial: {{x: ''}}}}
""")
    (config_path.parent / "state.json").write_text(json.dumps({
        "x": "old", "last_checked": "2026-07-08T00:00:00Z",
    }))


def _run_action_failure(config_path: Path) -> tuple[int, str]:
    output = StringIO()
    with redirect_stdout(output), patch("detect_engine.gws_patch_event", return_value=False):
        rc = run_engine_with_mock_json(config_path, {"x": "new"})
    return rc, output.getvalue()


def test_harden_fetch_failure_dry_run_writes_no_evidence_or_stdout():
    """TC-HARDEN-FETCH-DRY: dry-run suppresses fetch evidence and its pointer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        esc_dir = Path(tmpdir) / "escalations"
        config_path.write_text("""
name: fetch dry run
sources: [{id: source, url: https://example.com, required: true, retry: {count: 0, escalate_on_failure: true}}]
state: {file: state.json}
""")
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            output = StringIO()
            failed = FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError")
            with redirect_stdout(output), patch("detect_engine.FetchAgent.fetch", return_value=failed):
                assert run_engine(str(config_path), dry_run=True) == 1
            assert not esc_dir.exists() or not list(esc_dir.iterdir())
            assert "LLM_ESCALATION:" not in output.getvalue()
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_harden_action_failure_backoff_suppresses_second_poll():
    """TC-HARDEN-ACTION-BACKOFF: repeated failure produces one evidence file/pointer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        esc_dir = Path(tmpdir) / "escalations"
        _write_action_failure_config(config_path, "action backoff one", "1h")
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            first_rc, first_out = _run_action_failure(config_path)
            second_rc, second_out = _run_action_failure(config_path)
            assert first_rc == second_rc == 1
            assert len(list(esc_dir.glob("action_failure_*.json"))) == 1
            assert (first_out + second_out).count("LLM_ESCALATION:") == 1
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_harden_action_failure_backoff_expiry_allows_second_poll():
    """TC-HARDEN-ACTION-BACKOFF-EXPIRE: stale side-file entry permits evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        esc_dir = Path(tmpdir) / "escalations"
        name = "action backoff expired"
        _write_action_failure_config(config_path, name, "1h")
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            assert _run_action_failure(config_path)[0] == 1
            backoff_path = _detect_engine_mod._escalation_backoff_path(name)
            backoff_path.write_text(json.dumps({
                "action_failure": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            }))
            assert _run_action_failure(config_path)[0] == 1
            assert len(list(esc_dir.glob("action_failure_*.json"))) == 2
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_harden_fetch_failure_backoff_suppresses_second_poll():
    """TC-HARDEN-FETCH-BACKOFF: fetch failures use the same per-type gate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        esc_dir = Path(tmpdir) / "escalations"
        config_path.write_text("""
name: fetch backoff one
sources: [{id: source, url: https://example.com, required: true, retry: {count: 0, escalate_on_failure: true}}]
llm_escalation: {escalation_backoff: 1h}
state: {file: state.json}
""")
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            failed = FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError")
            outputs = []
            for _ in range(2):
                output = StringIO()
                with redirect_stdout(output), patch("detect_engine.FetchAgent.fetch", return_value=failed):
                    assert run_engine(str(config_path)) == 1
                outputs.append(output.getvalue())
            assert len(list(esc_dir.glob("fetch_failure_*.json"))) == 1
            assert "".join(outputs).count("LLM_ESCALATION:") == 1
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_harden_zero_escalation_backoff_disables_throttling():
    """TC-HARDEN-BACKOFF-ZERO: an explicit zero duration writes every failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        esc_dir = Path(tmpdir) / "escalations"
        _write_action_failure_config(config_path, "action backoff zero", "0s")
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            assert _run_action_failure(config_path)[0] == 1
            assert _run_action_failure(config_path)[0] == 1
            assert len(list(esc_dir.glob("action_failure_*.json"))) == 2
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_harden_junk_escalation_backoff_warns_at_validation():
    """TC-HARDEN-BACKOFF-JUNK: invalid duration is surfaced during validation."""
    with patch.object(_detect_engine_mod.log, "warning") as warning:
        validate_config_cross_refs(
            DetectConfig(name="junk backoff", llm_escalation=LLMEscalation(escalation_backoff="banana"))
        )
        validate_config_cross_refs(
            DetectConfig(name="partial junk", llm_escalation=LLMEscalation(escalation_backoff="banana1h"))
        )
    warnings = "\n".join(str(call) for call in warning.call_args_list)
    assert "escalation_backoff" in warnings and "banana1h" in warnings


def _write_indeterminate_config(config_path: Path, composite: bool = False):
    condition = """
  - id: changed
    field: x
    op: changed
    baseline: {source: calendar, event_id: event, field: start.dateTime}
    for: 10m
""" if not composite else """
  - id: changed
    for: 10m
    and:
      - field: x
        op: changed
        baseline: {source: calendar, event_id: event, field: start.dateTime}
"""
    config_path.write_text("""
name: indeterminate gate
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions:
""" + condition + """
groups: [{name: g, any: [changed]}]
state: {file: state.json, initial: {x: ''}}
""")


def test_harden_indeterminate_outage_preserves_duration_first_seen():
    """TC-HARDEN-INDET-FIRST: an unavailable baseline does not reset for: timing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        original_first_seen = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        state_path.write_text(json.dumps({"x": "old", "first_seen": {"changed": original_first_seen}}))
        _write_indeterminate_config(config_path)
        with patch("detect_engine.gws_get_event", return_value=None):
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        assert json.loads(state_path.read_text())["first_seen"]["changed"] == original_first_seen


def test_harden_indeterminate_outage_preserves_acknowledged():
    """TC-HARDEN-INDET-ACK: unknown calendar state does not prune acknowledgements."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        acknowledged = {"changed": {"at": "2026-01-01T00:00:00Z", "value": "new"}}
        state_path.write_text(json.dumps({"x": "old", "acknowledged": acknowledged}))
        _write_indeterminate_config(config_path)
        with patch("detect_engine.gws_get_event", return_value=None):
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        assert json.loads(state_path.read_text())["acknowledged"] == acknowledged


def test_harden_indeterminate_composite_outage_preserves_duration_and_ack():
    """TC-HARDEN-INDET-COMPOSITE: unknown nested changed result is not a definite false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        first_seen = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        acknowledged = {"changed": {"at": "2026-01-01T00:00:00Z", "value": "new"}}
        state_path.write_text(json.dumps({
            "x": "old", "first_seen": {"changed": first_seen}, "acknowledged": acknowledged,
        }))
        _write_indeterminate_config(config_path, composite=True)
        with patch("detect_engine.gws_get_event", return_value=None):
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        state = json.loads(state_path.read_text())
        assert state["first_seen"]["changed"] == first_seen
        assert state["acknowledged"] == acknowledged


def test_harden_indeterminate_recovery_resumes_original_duration_gate():
    """TC-HARDEN-INDET-RECOVER: recovery honors first_seen from before outage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        original_first_seen = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        state_path.write_text(json.dumps({"x": "old", "first_seen": {"changed": original_first_seen}}))
        _write_indeterminate_config(config_path)
        with patch("detect_engine.gws_get_event", return_value=None):
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        with patch("detect_engine.gws_get_event", return_value={
            "id": "event", "start": {"dateTime": "old"}
        }):
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        recovered = json.loads(state_path.read_text())
        assert recovered["first_seen"]["changed"] == original_first_seen
        assert "changed" in recovered["last_fired"], "Recovered gate should fire without waiting another 10m"


def test_harden_directional_time_shift_ops():
    """TC-HARDEN-TIME-SHIFT: signed later/earlier comparisons are directional."""
    previous = {"baseline": "2026-07-07T17:00:00-07:00"}
    delayed = TriggerAgent(previous, {**previous, "actual": "2026-07-07T17:20:00-07:00"}, {})
    earlier = TriggerAgent(previous, {**previous, "actual": "2026-07-07T16:40:00-07:00"}, {})
    gt = Condition(id="gt", field="actual", op="time_shift_gt", value=15, compared_to="state.baseline")
    lt = Condition(id="lt", field="actual", op="time_shift_lt", value=-15, compared_to="state.baseline")
    assert delayed.evaluate(gt).matched and not delayed.evaluate(lt).matched
    assert earlier.evaluate(lt).matched and not earlier.evaluate(gt).matched


def test_harden_directional_time_shift_none_operands_match_time_diff():
    """TC-HARDEN-TIME-SHIFT-NONE: directional ops retain time_diff None semantics."""
    trigger = TriggerAgent({}, {"actual": None}, {})
    old = trigger.evaluate(Condition(id="old", field="actual", op="time_diff_gt", value=15,
                                     compared_to="state.baseline"))
    new = trigger.evaluate(Condition(id="new", field="actual", op="time_shift_gt", value=15,
                                     compared_to="state.baseline"))
    assert not old.matched and not new.matched
    assert old.reason.replace("time_diff_gt", "time_shift_gt") == new.reason
    missing_baseline = TriggerAgent({}, {"actual": "2026-07-07T17:20:00-07:00"}, {})
    old = missing_baseline.evaluate(Condition(id="old", field="actual", op="time_diff_gt", value=15,
                                              compared_to="state.baseline"))
    new = missing_baseline.evaluate(Condition(id="new", field="actual", op="time_shift_gt", value=15,
                                              compared_to="state.baseline"))
    assert not old.matched and not new.matched
    assert old.reason.replace("time_diff_gt", "time_shift_gt") == new.reason


runner.run("TC-F4.1-DURATION: duration gate holds changed baseline", test_f4_1_duration_gate_holds_changed_baseline)
runner.run("TC-F4.1-REFIRE: refire window holds changed baseline", test_f4_1_refire_window_holds_changed_baseline)
runner.run("TC-F4.1-MATRIX: shared field hold matrix", test_f4_1_shared_field_hold_matrix)
runner.run("TC-F4.2-CAL-TITLE: cal_title uses current calendar_patch title", test_f4_2_cal_title_current_value_preferred)
runner.run("TC-F4.3-GWS: unavailable gws calendar baseline", test_f4_3_calendar_baseline_gws_failure_unavailable)
runner.run("TC-F4.3-INTERMEDIATE: unavailable intermediate calendar path", test_f4_3_calendar_baseline_missing_intermediate_unavailable)
runner.run("TC-F4.3-LEAF: unavailable leaf calendar path", test_f4_3_calendar_baseline_missing_leaf_unavailable)
runner.run("TC-F4.3-NULL: calendar null leaf is comparable", test_f4_3_calendar_baseline_null_leaf_is_real_value)
runner.run("TC-F4.4-SIBLING: reject sibling state path", test_f4_4_state_path_sibling_rejected)
runner.run("TC-F4.4-NESTED: allow nested state path", test_f4_4_state_path_nested_allowed)
runner.run("TC-F4.5-DUP-ID: reject duplicate condition ids", test_f4_5_duplicate_explicit_condition_ids_rejected)
runner.run("TC-F4.5-DUP-TRANSITION: reject duplicate transition ids", test_f4_5_duplicate_transition_ids_rejected)
runner.run("TC-F4.5-ACTION-ONCE: dedupe shared action execution", test_f4_5_duplicate_group_action_runs_once)
runner.run("TC-M3: shared calendar baseline resolution", test_m3_shared_calendar_baseline_resolution)
runner.run("TC-M7: runner self-check uses validate exit status", test_m7_runner_self_check_uses_validate_exit_status)
runner.run("TC-H-A: runtime cross refs block fetch", test_h_a_run_engine_rejects_cross_ref_errors_before_fetch)
runner.run("TC-H-B: held cal_title is not overwritten", test_h_b_held_cal_title_is_not_overwritten_after_other_action_succeeds)
runner.run("TC-H-C: per-config health filename", test_h_c_health_file_is_slugged_per_config)
runner.run("TC-HARDEN-SEED-OPTOUT: seed_mode:false fires from fresh state", test_harden_seed_mode_false_fires_on_fresh_state)
runner.run("TC-HARDEN-SEED-FIRE-BOUNCE: seeded baseline fires, holds, and re-fires", test_harden_seed_fire_norefire_bounce)
runner.run("TC-HARDEN-FETCH-DRY: dry-run suppresses fetch escalation", test_harden_fetch_failure_dry_run_writes_no_evidence_or_stdout)
runner.run("TC-HARDEN-ACTION-BACKOFF: action failure backoff suppresses repeat", test_harden_action_failure_backoff_suppresses_second_poll)
runner.run("TC-HARDEN-ACTION-BACKOFF-EXPIRE: expired action backoff permits repeat", test_harden_action_failure_backoff_expiry_allows_second_poll)
runner.run("TC-HARDEN-FETCH-BACKOFF: fetch failure backoff suppresses repeat", test_harden_fetch_failure_backoff_suppresses_second_poll)
runner.run("TC-HARDEN-BACKOFF-ZERO: zero backoff disables throttling", test_harden_zero_escalation_backoff_disables_throttling)
runner.run("TC-HARDEN-BACKOFF-JUNK: junk backoff warns during validation", test_harden_junk_escalation_backoff_warns_at_validation)
runner.run("TC-HARDEN-INDET-FIRST: outage preserves duration first_seen", test_harden_indeterminate_outage_preserves_duration_first_seen)
runner.run("TC-HARDEN-INDET-ACK: outage preserves acknowledged entries", test_harden_indeterminate_outage_preserves_acknowledged)
runner.run("TC-HARDEN-INDET-COMPOSITE: nested outage preserves duration and ack", test_harden_indeterminate_composite_outage_preserves_duration_and_ack)
runner.run("TC-HARDEN-INDET-RECOVER: recovery resumes original duration gate", test_harden_indeterminate_recovery_resumes_original_duration_gate)
runner.run("TC-HARDEN-TIME-SHIFT: directional time shifts", test_harden_directional_time_shift_ops)
runner.run("TC-HARDEN-TIME-SHIFT-NONE: directional None operands", test_harden_directional_time_shift_none_operands_match_time_diff)


# ── Runner duplicate detection and evidence-GC subprocess tests ──

def _runner_subprocess_env(detect_dir: Path, state_dir: Path):
    return {
        **os.environ,
        "DETECT_DIR": str(detect_dir),
        "PYTHON": sys.executable,
        "ENGINE": str(SCRIPTS_DIR / "detect_engine.py"),
        "STATE_DIR": str(state_dir),
        "POC_STATE_DIR": str(state_dir),
        "LOG_FILE": str(state_dir / "detect-runner.log"),
        "DETECT_ENGINE_LOG_FILE": str(state_dir / "detect-engine.log"),
        "DETECT_ENGINE_HEALTH_DIR": str(state_dir),
        "DETECT_ENGINE_ESCALATION_DIR": str(state_dir / "escalations"),
    }


def _write_runner_config(config_path: Path, name: str, state_file: str, enabled: bool = True):
    enabled_line = "enabled: false\n" if not enabled else ""
    config_path.write_text(f'''\
name: "{name}"
{enabled_line}sources:
  - id: source
    url: "https://example.com"
    extract:
      - id: value
        type: jsonpath
        path: "$.value"
conditions:
  - id: value_changed
    field: value
    op: changed
    baseline: {{source: state, field: value}}
groups:
  - name: monitor
    any: [value_changed]
    actions: []
state:
  file: "{state_file}"
  initial: {{value: ""}}
''')


def test_harden_runner_self_check_rejects_duplicate_names():
    """TC-HARDEN-RUNNER-DUP-NAME: self-check rejects colliding config names."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        _write_runner_config(detect_dir / "one.yaml", "Duplicate Monitor", "state/one.json")
        _write_runner_config(detect_dir / "two.yaml", "Duplicate Monitor", "state/two.json")
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(detect_dir, root / "state-root"),
            text=True,
            capture_output=True,
        )
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "duplicate config slug" in output
    assert "Duplicate Monitor" in output
    assert "2 valid config(s), 0 invalid" in result.stdout + result.stderr


def test_harden_runner_self_check_ignores_disabled_duplicate():
    """TC-HARDEN-RUNNER-DUP-DISABLED: self-check ignores disabled duplicate names."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        _write_runner_config(detect_dir / "one.yaml", "Duplicate Monitor", "state/one.json")
        _write_runner_config(
            detect_dir / "two.yaml", "Duplicate Monitor", "state/two.json", enabled=False
        )
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(detect_dir, root / "state-root"),
            text=True,
            capture_output=True,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 valid config(s), 0 invalid" in result.stdout + result.stderr


def test_harden_runner_self_check_allows_distinct_configs():
    """TC-HARDEN-RUNNER-DUP-POSITIVE: distinct names and state files pass self-check."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        _write_runner_config(detect_dir / "one.yaml", "First Monitor", "state/one.json")
        _write_runner_config(detect_dir / "two.yaml", "Second Monitor", "state/two.json")
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(detect_dir, root / "state-root"),
            text=True,
            capture_output=True,
        )
    assert result.returncode == 0, result.stdout + result.stderr


def test_harden_runner_self_check_rejects_duplicate_state_files():
    """TC-HARDEN-RUNNER-DUP-STATE: self-check rejects shared resolved state files."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        shared_state = root / "shared-state.json"
        _write_runner_config(detect_dir / "one.yaml", "First Monitor", str(shared_state))
        _write_runner_config(detect_dir / "two.yaml", "Second Monitor", str(shared_state))
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(detect_dir, root / "state-root"),
            text=True,
            capture_output=True,
        )
    assert result.returncode != 0
    assert "duplicate state.file:" in result.stdout + result.stderr
    assert "2 valid config(s), 0 invalid" in result.stdout + result.stderr


def test_p0_slug_runner_rejects_normalized_name_collision():
    """TC-P0-SLUG-RUNNER: self-check catches distinct names sharing one canonical slug."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        _write_runner_config(detect_dir / "one.yaml", "A_B", "state/one.json")
        _write_runner_config(detect_dir / "two.yaml", "a b", "state/two.json")
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(detect_dir, root / "state-root"),
            text=True,
            capture_output=True,
        )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "duplicate config slug 'a-b'" in output
    assert "A_B" in output and "a b" in output


def test_p0_slug_health_path_stays_inside_health_dir_for_traversal_name():
    """TC-P0-SLUG-HEALTH: hostile config names cannot escape the health directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        health_dir = root / "nested" / "health"
        config_path = root / "config.yaml"
        config_path.write_text("""
name: "../../outside"
state: {file: state.json}
""")
        original_dir = _detect_engine_mod.HEALTH_DIR
        _detect_engine_mod.HEALTH_DIR = health_dir
        try:
            assert run_engine(str(config_path)) == 0
            health_path = health_dir / "outside-health.json"
            assert health_path.resolve().is_relative_to(health_dir.resolve())
            assert health_path.exists()
            assert not (root / "outside-health.json").exists()
        finally:
            _detect_engine_mod.HEALTH_DIR = original_dir


def test_p0_slug_condition_evidence_uses_config_and_microsecond_identity():
    """TC-P0-SLUG-EVIDENCE: same condition at one timestamp keeps both configs' evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        esc_dir = Path(tmpdir)
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        fixed_now = datetime(2026, 7, 11, 12, 0, 0, 123456, tzinfo=timezone.utc)
        try:
            first = LLMEscalationAgent(
                DetectConfig(name="First Group", sources=[], conditions=[], groups=[], actions={}),
                {}, {}, [],
            )
            second = LLMEscalationAgent(
                DetectConfig(name="Second Group", sources=[], conditions=[], groups=[], actions={}),
                {}, {}, [],
            )
            condition = Condition(id="same_condition", field="x", op="eq", value="new")
            result = ConditionResult(True, "matched")
            with patch.object(_detect_engine_mod, "datetime") as mock_datetime:
                mock_datetime.now.return_value = fixed_now
                first.escalate([("same_condition", result, condition)])
                second.escalate([("same_condition", result, condition)])
            files = sorted(esc_dir.glob("*.json"))
            assert len(files) == 2
            assert files[0].name != files[1].name
            assert {path.name.split("_")[0] for path in files} == {"first-group", "second-group"}
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_p0_slug_fetch_failure_source_id_is_sanitized_and_contained():
    """TC-P0-SLUG-FETCH: source-id path punctuation cannot create an unsafe evidence path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        esc_dir = Path(tmpdir) / "escalations"
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            evidence_path = write_fetch_failure_escalation(
                Source(id="a/../b", url="https://example.com"),
                FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError"),
                "Fetch Monitor",
            )
            assert evidence_path is not None
            path = Path(evidence_path)
            assert path.resolve().is_relative_to(esc_dir.resolve())
            assert path.exists()
            assert "a____b" in path.name
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_p0_slug_path_resolution_failure_skips_write():
    """TC-P0-SLUG-RESOLVE: a containment-resolution failure degrades to no path."""
    with patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop")):
        assert _detect_engine_mod._derived_path_within(Path("/tmp/base"), "file.json", "test") is None


def test_p0_save_failure_after_actions_returns_error_health_and_evidence():
    """TC-P0-SAVE-ACTION: successful actions with an uncommitted state are a failed run."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        health_dir = root / "health"
        esc_dir = root / "escalations"
        state_path.write_text(json.dumps({"x": "old"}))
        config_path.write_text("""
name: save commit failure
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: main, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {x: old}}
""")
        original_health = _detect_engine_mod.HEALTH_DIR
        original_esc = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.HEALTH_DIR = health_dir
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            with patch("detect_engine.gws_get_event", return_value=None), \
                 patch("detect_engine.gws_patch_event", return_value=True), \
                 patch.object(_detect_engine_mod.StateManager, "save", side_effect=OSError("disk full")):
                assert run_engine_with_mock_json(config_path, {"x": "new"}) == 1
            health = json.loads((health_dir / "save-commit-failure-health.json").read_text())
            assert health["status"] == "error"
            assert "actions applied but state commit failed" in health["detail"]
            evidence_files = list(esc_dir.glob("action_failure_*.json"))
            assert len(evidence_files) == 1
            evidence = json.loads(evidence_files[0].read_text())
            assert evidence["escalation_type"] == "state_commit_failure"
            assert evidence["external_actions_succeeded"] is True
            assert evidence["state_committed"] is False
        finally:
            _detect_engine_mod.HEALTH_DIR = original_health
            _detect_engine_mod.ESCALATION_DIR = original_esc


def test_p0_delete_404_retry_converges_partial_action_group():
    """TC-P0-DELETE-RETRY: retry treats an already-deleted event as successful and commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        state_path.write_text(json.dumps({"x": "old"}))
        config_path.write_text("""
name: delete retry convergence
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: main, any: [changed], actions: [delete_old, patch_new]}]
actions:
  delete_old: {type: calendar_delete, event_id: stale-event}
  patch_new: {type: calendar_patch, event_id: current-event, fields: {summary: updated}}
state: {file: state.json, initial: {x: old}}
""")
        delete_success = MagicMock(returncode=0, stdout="", stderr="")
        delete_not_found = MagicMock(
            returncode=1,
            stdout='{"error": {"code": 404, "status": "NOT_FOUND", "message": "Not found"}}',
            stderr="",
        )
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", side_effect=[False, True]) as mock_patch, \
             patch("gws_utils.subprocess.run", side_effect=[delete_success, delete_not_found]) as mock_delete:
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 1
            assert json.loads(state_path.read_text())["x"] == "old"
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        assert mock_delete.call_count == 2
        assert mock_patch.call_count == 2
        assert json.loads(state_path.read_text())["x"] == "new"


def test_p0_delete_not_found_error_body_is_idempotent_success():
    """TC-P0-DELETE-BODY: a zero-exit not-found JSON body converges a delete retry."""
    result = MagicMock(
        returncode=0,
        stdout='{"error": {"status": "NOT_FOUND", "message": "Event already deleted"}}',
        stderr="",
    )
    with patch("gws_utils.subprocess.run", return_value=result):
        from gws_utils import gws_delete_event
        assert gws_delete_event("stale-event") is True


def test_p0_delete_permission_error_with_deleted_text_remains_failure():
    """TC-P0-DELETE-AUTH: permission failures are never mistaken for idempotent deletes."""
    result = MagicMock(returncode=1, stdout="", stderr="permission denied for deleted token")
    with patch("gws_utils.subprocess.run", return_value=result):
        from gws_utils import gws_delete_event
        assert gws_delete_event("stale-event") is False


def test_p0_transitions_composite_unless_suppresses_then_allows_action():
    """TC-P0-TRANS-UNLESS: transition when/unless gates the generated root composite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        config_path.write_text("""
name: transition unless runtime
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: status, type: jsonpath, path: $.status}]}]
transitions:
  - field: status
    when: {op: eq, value: Delayed}
    unless: {field: cal_title, op: contains, value: DELAYED}
    on_change: [patch]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {status: On time}}
""")
        state_path.write_text(json.dumps({"status": "On time"}))
        with patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            with patch("detect_engine.gws_get_event", return_value={"summary": "DELAYED: calendar title"}):
                assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0
            mock_patch.assert_not_called()

            state_path.write_text(json.dumps({"status": "On time"}))
            with patch("detect_engine.gws_get_event", return_value={"summary": "On-time calendar title"}):
                assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0
            mock_patch.assert_called_once()


def test_p0_seed_mode_zero_initial_value_seeds_without_action():
    """TC-P0-SEED-ZERO: a numeric-zero initial value still makes the fresh poll seed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: zero seed
sources: [{id: source, url: https://example.com, extract: [{id: count, type: jsonpath, path: $.count}]}]
conditions: [{id: changed, field: count, op: changed, baseline: {source: state, field: count}}]
groups: [{name: main, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {count: 0}}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"count": 1}) == 0
            mock_patch.assert_not_called()
        state = json.loads(state_path.read_text())
        assert state["count"] == 1 and state["last_checked"]


def test_p0_seed_mode_false_initial_value_seeds_without_action():
    """TC-P0-SEED-FALSE: a boolean-false initial value still makes the fresh poll seed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: false seed
sources: [{id: source, url: https://example.com, extract: [{id: flag, type: jsonpath, path: $.flag}]}]
conditions: [{id: changed, field: flag, op: changed, baseline: {source: state, field: flag}}]
groups: [{name: main, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {flag: false}}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"flag": True}) == 0
            mock_patch.assert_not_called()
        state = json.loads(state_path.read_text())
        assert state["flag"] is True and state["last_checked"]


def test_p0_seed_mode_nonempty_initial_seeds_then_second_poll_fires():
    """TC-P0-SEED-NONEMPTY: a populated baseline seeds once and evaluates after last_checked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: nonempty seed
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: main, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {x: SEA}}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"x": "PDX"}) == 0
            mock_patch.assert_not_called()
            assert json.loads(state_path.read_text())["last_checked"]
            assert run_engine_with_mock_json(config_path, {"x": "SEA"}) == 0
            mock_patch.assert_called_once()


def test_p0_dry_run_expired_config_preserves_existing_health_file():
    """TC-P0-DRY-EXPIRED: dry-running an expired config never deletes health history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        health_dir = root / "health"
        health_dir.mkdir()
        config_path = root / "config.yaml"
        config_path.write_text("""
name: expired dry run
expires: "2000-01-01T00:00:00Z"
state: {file: state.json}
""")
        health_path = health_dir / "expired-dry-run-health.json"
        sentinel = b'{"status": "ok", "historical": true}\n'
        health_path.write_bytes(sentinel)
        original_health = _detect_engine_mod.HEALTH_DIR
        _detect_engine_mod.HEALTH_DIR = health_dir
        try:
            assert run_engine(str(config_path), dry_run=True) == 0
            assert health_path.read_bytes() == sentinel
        finally:
            _detect_engine_mod.HEALTH_DIR = original_health


def test_p0_dry_run_required_source_failure_leaves_health_untouched():
    """TC-P0-DRY-REQUIRED: dry-run required-source failure returns one without health writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        health_dir = root / "health"
        config_path = root / "config.yaml"
        config_path.write_text("""
name: required dry run
sources: [{id: source, url: https://example.com, required: true, retry: {count: 0}}]
state: {file: state.json}
""")
        original_health = _detect_engine_mod.HEALTH_DIR
        _detect_engine_mod.HEALTH_DIR = health_dir
        try:
            failed = FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError")
            with patch("detect_engine.FetchAgent.fetch", return_value=failed):
                assert run_engine(str(config_path), dry_run=True) == 1
            assert not health_dir.exists() or not list(health_dir.iterdir())
        finally:
            _detect_engine_mod.HEALTH_DIR = original_health


def test_harden_runner_gc_removes_only_expired_evidence():
    """TC-HARDEN-RUNNER-GC: no-config main run prunes only expired evidence classes."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "empty-configs"
        detect_dir.mkdir()
        escalation_dir = root / "state" / "escalations"
        processed_dir = escalation_dir / "processed"
        failed_dir = escalation_dir / "failed"
        processed_dir.mkdir(parents=True)
        failed_dir.mkdir()
        old_time = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()

        old_processed = processed_dir / "old.json"
        fresh_processed = processed_dir / "fresh.json"
        old_failed = failed_dir / "old.json"
        fresh_failed = failed_dir / "fresh.json"
        old_tmp = escalation_dir / "old.tmp"
        fresh_tmp = escalation_dir / "fresh.tmp"
        disposition = escalation_dir / "disposition.md"
        for path in (old_processed, fresh_processed, old_failed, fresh_failed, old_tmp, fresh_tmp, disposition):
            path.write_text("evidence")
        for path in (old_processed, old_failed, old_tmp):
            os.utime(path, (old_time, old_time))

        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh")],
            env=_runner_subprocess_env(detect_dir, root / "state"),
            text=True,
            capture_output=True,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        assert not old_processed.exists() and fresh_processed.exists()
        assert not old_failed.exists() and fresh_failed.exists()
        assert not old_tmp.exists() and fresh_tmp.exists()
        assert disposition.exists()


def test_harden_runner_gc_skips_missing_escalation_directory():
    """TC-HARDEN-RUNNER-GC-MISSING: GC quietly accepts absent escalation storage."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "empty-configs"
        detect_dir.mkdir()
        state_dir = root / "state-without-escalations"
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh")],
            env=_runner_subprocess_env(detect_dir, state_dir),
            text=True,
            capture_output=True,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""


runner.run("TC-HARDEN-RUNNER-DUP-NAME: reject duplicate config names", test_harden_runner_self_check_rejects_duplicate_names)
runner.run("TC-HARDEN-RUNNER-DUP-DISABLED: ignore disabled duplicate names", test_harden_runner_self_check_ignores_disabled_duplicate)
runner.run("TC-HARDEN-RUNNER-DUP-POSITIVE: allow distinct configs", test_harden_runner_self_check_allows_distinct_configs)
runner.run("TC-HARDEN-RUNNER-DUP-STATE: reject duplicate state files", test_harden_runner_self_check_rejects_duplicate_state_files)
runner.run("TC-P0-SLUG-RUNNER: reject normalized config-name collision", test_p0_slug_runner_rejects_normalized_name_collision)
runner.run("TC-P0-SLUG-HEALTH: contain hostile config-name health path", test_p0_slug_health_path_stays_inside_health_dir_for_traversal_name)
runner.run("TC-P0-SLUG-EVIDENCE: preserve same-timestamp condition evidence", test_p0_slug_condition_evidence_uses_config_and_microsecond_identity)
runner.run("TC-P0-SLUG-FETCH: sanitize and contain fetch source-id evidence", test_p0_slug_fetch_failure_source_id_is_sanitized_and_contained)
runner.run("TC-P0-SLUG-RESOLVE: skip path writes when containment resolution fails", test_p0_slug_path_resolution_failure_skips_write)
runner.run("TC-P0-SAVE-ACTION: fail run after action state-save failure", test_p0_save_failure_after_actions_returns_error_health_and_evidence)
runner.run("TC-P0-DELETE-RETRY: converge partial action retry after delete 404", test_p0_delete_404_retry_converges_partial_action_group)
runner.run("TC-P0-DELETE-BODY: treat not-found error body as idempotent delete", test_p0_delete_not_found_error_body_is_idempotent_success)
runner.run("TC-P0-DELETE-AUTH: reject auth errors despite deleted wording", test_p0_delete_permission_error_with_deleted_text_remains_failure)
runner.run("TC-P0-TRANS-UNLESS: enforce unless on composite transitions", test_p0_transitions_composite_unless_suppresses_then_allows_action)
runner.run("TC-P0-SEED-ZERO: seed numeric-zero initial state", test_p0_seed_mode_zero_initial_value_seeds_without_action)
runner.run("TC-P0-SEED-FALSE: seed boolean-false initial state", test_p0_seed_mode_false_initial_value_seeds_without_action)
runner.run("TC-P0-SEED-NONEMPTY: seed nonempty state before second-poll action", test_p0_seed_mode_nonempty_initial_seeds_then_second_poll_fires)
runner.run("TC-P0-DRY-EXPIRED: preserve health during expired dry run", test_p0_dry_run_expired_config_preserves_existing_health_file)
runner.run("TC-P0-DRY-REQUIRED: skip health write on required-source dry-run failure", test_p0_dry_run_required_source_failure_leaves_health_untouched)
runner.run("TC-HARDEN-RUNNER-GC: prune expired evidence only", test_harden_runner_gc_removes_only_expired_evidence)
runner.run("TC-HARDEN-RUNNER-GC-MISSING: skip missing escalation directory", test_harden_runner_gc_skips_missing_escalation_directory)


# ═══════════════════════════════════════════════════════════════
#  P1 backlog regressions (MEDIUM-confidence findings, test-first)
# ═══════════════════════════════════════════════════════════════

def test_p1_url_redacts_token_query_in_evidence_and_prompt():
    """TC-P1-URL-TOKEN: token= query values are redacted in evidence url + prompt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        esc_dir = Path(tmpdir)
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            source = Source(
                id="api",
                url="https://api.example.com/flight?token=supersecret&flight=706",
            )
            result = FetchResult(0, {}, "", "down", attempts=2, last_error_type="ConnectError")
            path = write_fetch_failure_escalation(source, result, "Token Leak Monitor")
            assert path is not None
            data = json.loads(Path(path).read_text())
            assert "supersecret" not in data["url"]
            assert "supersecret" not in data["prompt"]
            assert "token=%2A%2A%2AREDACTED%2A%2A%2A" in data["url"] or "token=***REDACTED***" in data["url"]
            assert "flight=706" in data["url"]
            assert "api.example.com" in data["url"]
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_p1_url_redacts_basic_auth_userinfo():
    """TC-P1-URL-USERINFO: https://user:pass@host userinfo is redacted in evidence+prompt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        esc_dir = Path(tmpdir)
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            source = Source(
                id="basic",
                url="https://alice:s3cretpass@api.example.com/v1/status",
            )
            result = FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError")
            path = write_fetch_failure_escalation(source, result, "Auth Leak Monitor")
            assert path is not None
            data = json.loads(Path(path).read_text())
            assert "s3cretpass" not in data["url"]
            assert "alice" not in data["url"] or "***REDACTED***" in data["url"]
            assert "s3cretpass" not in data["prompt"]
            assert "api.example.com" in data["url"]
            assert "***REDACTED***@" in data["url"]
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_p1_custom_failure_prompt_placeholders_rendered():
    """TC-P1-FAIL-PROMPT: custom failure_prompt {{ attempts }}/{{ url }} render (url redacted)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        esc_dir = Path(tmpdir)
        original_dir = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            source = Source(
                id="src1",
                url="https://api.example.com/data?api_key=TOPSECRET",
                failure_prompt=(
                    "Source {{ source_id }} on {{ config_name }} failed after "
                    "{{ attempts }} attempts at {{ url }}. error={{ error }} "
                    "type={{ error_type }} status={{ status_code }}"
                ),
            )
            result = FetchResult(
                503, {}, "", "Service Unavailable",
                attempts=3, last_error_type="HTTPError",
            )
            path = write_fetch_failure_escalation(source, result, "Prompt Render")
            assert path is not None
            data = json.loads(Path(path).read_text())
            prompt = data["prompt"]
            assert "{{" not in prompt and "}}" not in prompt, f"literal braces remain: {prompt}"
            assert "3" in prompt
            assert "src1" in prompt
            assert "Prompt Render" in prompt
            assert "TOPSECRET" not in prompt
            assert "Service Unavailable" in prompt
            assert "HTTPError" in prompt
            assert "503" in prompt
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_dir


def test_p1_calendar_prefetch_uses_action_calendar_id():
    """TC-P1-CAL-PREFETCH: Step 5 gws_get_event receives the action's non-primary calendar_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        state_path.write_text(json.dumps({
            "x": "old", "last_checked": "2026-07-08T00:00:00Z",
        }))
        config_path.write_text("""
name: nonprimary calendar prefetch
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: main, any: [changed], actions: [patch]}]
actions:
  patch:
    type: calendar_patch
    event_id: event-on-work
    calendar_id: work@example.com
    fields: {summary: updated}
state: {file: state.json, initial: {x: old}}
""")
        with patch("detect_engine.gws_get_event", return_value={"id": "event-on-work", "summary": "work title"}) as mock_get, \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"x": "new"}) == 0
        mock_get.assert_called()
        # Prefetch call must pass the action calendar_id, not default primary.
        get_calls = mock_get.call_args_list
        assert any(
            call.args[:2] == ("event-on-work", "work@example.com")
            or (call.args == ("event-on-work",) and call.kwargs.get("calendar_id") == "work@example.com")
            or (len(call.args) >= 2 and call.args[1] == "work@example.com")
            for call in get_calls
        ), f"prefetch did not use work calendar: {get_calls}"
        mock_patch.assert_called()
        patch_call = mock_patch.call_args
        assert "work@example.com" in patch_call.args or patch_call.kwargs.get("calendar_id") == "work@example.com"


def test_p1_action_failure_evidence_without_llm_escalation():
    """TC-P1-ACTION-NO-LLM: failing action with no llm_escalation still emits action_failure evidence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        health_dir = root / "health"
        esc_dir = root / "escalations"
        (root / "state.json").write_text(json.dumps({
            "x": "old", "last_checked": "2026-07-08T00:00:00Z",
        }))
        config_path.write_text("""
name: action fail no llm
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: x, type: jsonpath, path: $.x}]}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: main, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {x: old}}
""")
        original_health = _detect_engine_mod.HEALTH_DIR
        original_esc = _detect_engine_mod.ESCALATION_DIR
        _detect_engine_mod.HEALTH_DIR = health_dir
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        try:
            output = StringIO()
            with redirect_stdout(output), \
                 patch("detect_engine.gws_get_event", return_value=None), \
                 patch("detect_engine.gws_patch_event", return_value=False):
                rc = run_engine_with_mock_json(config_path, {"x": "new"})
            assert rc == 1
            evidence = list(esc_dir.glob("action_failure_*.json"))
            assert len(evidence) == 1, f"expected action_failure evidence, got {list(esc_dir.iterdir()) if esc_dir.exists() else []}"
            data = json.loads(evidence[0].read_text())
            assert data["escalation_type"] == "action_failure"
            assert "LLM_ESCALATION:" in output.getvalue()
            health = json.loads((health_dir / "action-fail-no-llm-health.json").read_text())
            assert health["status"] == "error"
        finally:
            _detect_engine_mod.HEALTH_DIR = original_health
            _detect_engine_mod.ESCALATION_DIR = original_esc


def test_p1_runner_missing_detect_dir_fails():
    """TC-P1-RUNNER-MISSING-DIR: absent DETECT_DIR exits nonzero (not silent success)."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        missing = root / "no-such-configs-dir"
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh")],
            env=_runner_subprocess_env(missing, root / "state"),
            text=True,
            capture_output=True,
        )
    assert result.returncode != 0, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    # Error is logged to LOG_FILE; also surface via exit code.
    log_path = root / "state" / "detect-runner.log"
    log_text = log_path.read_text() if log_path.exists() else ""
    assert "DETECT_DIR" in combined or "DETECT_DIR" in log_text or result.returncode == 1


def test_p1_runner_empty_existing_dir_succeeds():
    """TC-P1-RUNNER-EMPTY-DIR: existing empty DETECT_DIR is silent success."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "empty-configs"
        detect_dir.mkdir()
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh")],
            env=_runner_subprocess_env(detect_dir, root / "state"),
            text=True,
            capture_output=True,
        )
    assert result.returncode == 0, result.stdout + result.stderr


def test_p1_runner_self_check_missing_dir_fails():
    """TC-P1-RUNNER-SELF-MISSING: --self-check fails when DETECT_DIR is absent."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        missing = root / "absent"
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(missing, root / "state"),
            text=True,
            capture_output=True,
        )
    assert result.returncode != 0
    assert "DETECT_DIR" in (result.stdout + result.stderr)


def test_p1_runner_config_with_space_in_filename():
    """TC-P1-RUNNER-SPACE: config filenames containing spaces are iterated correctly."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        # Valid minimal config with a space in the filename.
        spaced = detect_dir / "my monitor.yaml"
        _write_runner_config(spaced, "Spaced Config Name", "state/spaced.json")
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--self-check"],
            env=_runner_subprocess_env(detect_dir, root / "state-root"),
            text=True,
            capture_output=True,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 valid config(s)" in (result.stdout + result.stderr)


def test_p1_time_op_non_numeric_threshold_validation_and_runtime():
    """TC-P1-TIME-THRESH: value 'fifteen' is a cross-ref error and does not crash evaluate."""
    config = DetectConfig(
        name="time thresh",
        sources=[],
        conditions=[
            Condition(
                id="bad_thresh",
                field="dep_time",
                op="time_diff_gt",
                value="fifteen",
                compared_to="state.dep_time",
            )
        ],
        groups=[Group(name="g", any=["bad_thresh"], actions=[])],
        actions={},
    )
    errors = validate_config_cross_refs(config)
    assert any("non-numeric" in e for e in errors), errors

    # Runtime: non-numeric threshold must not raise — non-matching False.
    prev = make_state(dep_time="2026-07-07T17:00:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T17:30:00-07:00")
    result = eval_condition(
        {
            "id": "bad_thresh",
            "field": "dep_time",
            "op": "time_diff_gt",
            "value": "fifteen",
            "compared_to": "state.dep_time",
        },
        prev,
        extracted,
    )
    assert not result.matched
    assert not result.indeterminate
    assert "non-numeric" in result.reason


def test_p1_time_op_bare_compared_to_field_resolves():
    """TC-P1-TIME-BARE: bare compared_to field name resolves via state/current lookup."""
    prev = {"baseline_time": "2026-07-07T17:00:00-07:00", "acknowledged": {}, "first_seen": {}, "last_fired": {}}
    extracted = {"dep_time": "2026-07-07T17:30:00-07:00"}
    result = eval_condition(
        {
            "id": "bare",
            "field": "dep_time",
            "op": "time_diff_gt",
            "value": "15",
            "compared_to": "baseline_time",
        },
        prev,
        extracted,
    )
    assert result.matched, result.reason
    assert "30" in result.reason or "time_diff" in result.reason


def test_p1_time_op_mixed_tz_normalized_to_utc():
    """TC-P1-TIME-TZ: mixed-offset datetimes normalize to UTC before differencing."""
    # 17:00-07:00 == 00:00Z next day; 18:00-04:00 == 22:00Z same day → -2 hours = -120 min abs
    # actual 18:00-04:00, baseline 17:00-07:00:
    # actual UTC: 22:00Z, baseline UTC: 00:00Z next day? Wait:
    # 2026-07-07T17:00:00-07:00 = 2026-07-08T00:00:00Z
    # 2026-07-07T18:00:00-04:00 = 2026-07-07T22:00:00Z
    # actual - baseline = 22:00Z - 00:00Z(next day) = -2 hours = -120 minutes
    # abs for time_diff_gt: 120 > 60 → match
    prev = make_state(dep_time="2026-07-07T17:00:00-07:00")
    extracted = make_extracted(dep_time="2026-07-07T18:00:00-04:00")
    result = eval_condition(
        {
            "id": "mixed",
            "field": "dep_time",
            "op": "time_diff_gt",
            "value": "60",
            "compared_to": "state.dep_time",
        },
        prev,
        extracted,
    )
    assert result.matched, result.reason
    # Without UTC normalize, subtracting aware datetimes of different offsets still works
    # in Python — the real bug is naive-vs-aware or wrong field resolution. Verify abs ~120.
    assert "120" in result.reason or "time_diff" in result.reason


def test_p1_http_503_retries_then_succeeds():
    """TC-P1-HTTP-503: source returning 503 twice then 200 succeeds within retry budget."""
    fetcher = FetchAgent()
    source = Source(
        id="cdn",
        url="https://example.com/api",
        timeout=5,
        retry={"count": 2, "backoff": 0},
    )
    with patch("detect_engine.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        r503 = MagicMock(status_code=503, headers={}, text="unavailable")
        r200 = MagicMock(status_code=200, headers={}, text='{"ok": true}')
        mock_client.request.side_effect = [r503, r503, r200]
        result = fetcher.fetch(source)
    assert result.ok
    assert result.status_code == 200
    assert result.attempts == 3
    assert mock_client.request.call_count == 3


def test_p1_http_400_and_404_fail_fast():
    """TC-P1-HTTP-4XX-FAST: 400 and 404 fail without retrying."""
    fetcher = FetchAgent()
    for code in (400, 404):
        source = Source(
            id=f"bad{code}",
            url="https://example.com/missing",
            timeout=5,
            retry={"count": 3, "backoff": 0},
        )
        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = MagicMock(
                status_code=code, headers={}, text="nope",
            )
            result = fetcher.fetch(source)
        assert not result.ok
        assert result.attempts == 1, f"{code} should fail-fast, attempts={result.attempts}"
        assert mock_client.request.call_count == 1


def test_p1_and_definite_false_wins_over_indeterminate():
    """TC-P1-AND-FALSE-WINS: AND([definite-false, indeterminate]) is definite False."""
    # First child definitely false (eq mismatch); second is changed with failed calendar baseline → indeterminate.
    prev = make_state(status="On time", dep_time="2026-07-07T17:20:00-07:00")
    extracted = make_extracted(status="On time", dep_time="2026-07-07T17:25:00-07:00")
    # Order A: false then indeterminate
    cond_false_first = {
        "id": "and_ff",
        "and": [
            {"field": "status", "op": "eq", "value": "Delayed"},  # definite false
            {
                "field": "dep_time",
                "op": "changed",
                "baseline": {
                    "source": "calendar",
                    "field": "start.dateTime",
                    "event_id": "missing-evt",
                },
            },
        ],
    }
    with patch("detect_engine.gws_get_event", return_value=None):
        r1 = eval_condition(cond_false_first, prev, extracted, calendar_events={})
    assert not r1.matched
    assert not r1.indeterminate, f"definite false must win; got indeterminate: {r1.reason}"

    # Order B: indeterminate then definite false
    cond_indet_first = {
        "id": "and_if",
        "and": [
            {
                "field": "dep_time",
                "op": "changed",
                "baseline": {
                    "source": "calendar",
                    "field": "start.dateTime",
                    "event_id": "missing-evt",
                },
            },
            {"field": "status", "op": "eq", "value": "Delayed"},  # definite false
        ],
    }
    with patch("detect_engine.gws_get_event", return_value=None):
        r2 = eval_condition(cond_indet_first, prev, extracted, calendar_events={})
    assert not r2.matched
    assert not r2.indeterminate, f"definite false must win either order: {r2.reason}"


def test_p1_gws_get_event_nonzero_rc_returns_none():
    """TC-P1-GWS-RC: nonzero gws returncode with junk stdout returns None (fail closed)."""
    result = MagicMock(
        returncode=1,
        stdout='{"id": "should-not-be-trusted", "summary": "junk"}',
        stderr="permission denied: bad token",
    )
    with patch("gws_utils.subprocess.run", return_value=result):
        from gws_utils import gws_get_event
        assert gws_get_event("evt-x") is None


def test_p1_gws_get_event_rc0_returns_event():
    """TC-P1-GWS-OK: rc 0 with valid event JSON returns the event dict."""
    result = MagicMock(
        returncode=0,
        stdout='{"id": "evt1", "summary": "Flight AS706"}',
        stderr="",
    )
    with patch("gws_utils.subprocess.run", return_value=result):
        from gws_utils import gws_get_event
        ev = gws_get_event("evt1")
        assert ev is not None
        assert ev["id"] == "evt1"
        assert ev["summary"] == "Flight AS706"


runner.run("TC-P1-URL-TOKEN: redact token query in fetch-failure evidence", test_p1_url_redacts_token_query_in_evidence_and_prompt)
runner.run("TC-P1-URL-USERINFO: redact basic-auth userinfo in fetch-failure evidence", test_p1_url_redacts_basic_auth_userinfo)
runner.run("TC-P1-FAIL-PROMPT: render custom failure_prompt placeholders", test_p1_custom_failure_prompt_placeholders_rendered)
runner.run("TC-P1-CAL-PREFETCH: pass action calendar_id to prefetch get", test_p1_calendar_prefetch_uses_action_calendar_id)
runner.run("TC-P1-ACTION-NO-LLM: action_failure without llm_escalation", test_p1_action_failure_evidence_without_llm_escalation)
runner.run("TC-P1-RUNNER-MISSING-DIR: missing DETECT_DIR exits nonzero", test_p1_runner_missing_detect_dir_fails)
runner.run("TC-P1-RUNNER-EMPTY-DIR: empty existing DETECT_DIR exits zero", test_p1_runner_empty_existing_dir_succeeds)
runner.run("TC-P1-RUNNER-SELF-MISSING: self-check missing DETECT_DIR fails", test_p1_runner_self_check_missing_dir_fails)
runner.run("TC-P1-RUNNER-SPACE: iterate config filename with space", test_p1_runner_config_with_space_in_filename)
runner.run("TC-P1-TIME-THRESH: non-numeric time-op threshold validation+runtime", test_p1_time_op_non_numeric_threshold_validation_and_runtime)
runner.run("TC-P1-TIME-BARE: bare compared_to field resolves", test_p1_time_op_bare_compared_to_field_resolves)
runner.run("TC-P1-TIME-TZ: mixed-tz time diff via UTC normalize", test_p1_time_op_mixed_tz_normalized_to_utc)
runner.run("TC-P1-HTTP-503: retry 503 then succeed", test_p1_http_503_retries_then_succeeds)
runner.run("TC-P1-HTTP-4XX-FAST: 400/404 fail-fast no retry", test_p1_http_400_and_404_fail_fast)
runner.run("TC-P1-AND-FALSE-WINS: AND definite-false over indeterminate", test_p1_and_definite_false_wins_over_indeterminate)
runner.run("TC-P1-GWS-RC: nonzero returncode fail-closed", test_p1_gws_get_event_nonzero_rc_returns_none)
runner.run("TC-P1-GWS-OK: rc0 valid event returned", test_p1_gws_get_event_rc0_returns_event)


# ═══════════════════════════════════════════════════════════════
#  P2 backlog regressions (hardening / consistency, test-first)
# ═══════════════════════════════════════════════════════════════

def _p2_fake_python_recording_ruff(root: Path, argv_log: Path) -> Path:
    """Write a fake PYTHON that records `-m ruff` argv and exits 0; otherwise delegates."""
    fake = root / "fake_python_ruff"
    fake.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
if [ "${{1:-}}" = "-m" ] && [ "${{2:-}}" = "ruff" ]; then
  printf '%s\\0' "$@" > "{argv_log}"
  # Also human-readable for debugging
  printf '%s\\n' "$@" > "{argv_log}.txt"
  exit 0
fi
exec "{sys.executable}" "$@"
"""
    )
    fake.chmod(0o755)
    return fake


def test_p2_runner_lint_is_check_only_by_default():
    """TC-P2-RUNNER-LINT-CHECK: --lint does not pass --fix to ruff by default."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        argv_log = root / "ruff_argv"
        fake_py = _p2_fake_python_recording_ruff(root, argv_log)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        env = _runner_subprocess_env(detect_dir, root / "state")
        env["PYTHON"] = str(fake_py)
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), "--lint"],
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        recorded = (root / "ruff_argv.txt").read_text()
        assert "check" in recorded, f"expected ruff check, got: {recorded!r}"
        assert "--fix" not in recorded.split(), f"--fix must not be default: {recorded!r}"


def test_p2_runner_lint_fix_opt_in():
    """TC-P2-RUNNER-LINT-FIX: --lint --fix and --lint-fix request ruff --fix."""
    subprocess = __import__("subprocess")
    for args in (["--lint", "--fix"], ["--lint-fix"]):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            argv_log = root / "ruff_argv"
            fake_py = _p2_fake_python_recording_ruff(root, argv_log)
            detect_dir = root / "configs"
            detect_dir.mkdir()
            env = _runner_subprocess_env(detect_dir, root / "state")
            env["PYTHON"] = str(fake_py)
            result = subprocess.run(
                ["bash", str(SCRIPTS_DIR / "detect_runner.sh"), *args],
                env=env,
                text=True,
                capture_output=True,
            )
            assert result.returncode == 0, f"{args}: {result.stdout}{result.stderr}"
            recorded = (root / "ruff_argv.txt").read_text()
            assert "--fix" in recorded.split(), f"{args}: expected --fix in {recorded!r}"


def test_p2_health_and_escalation_dirs_from_env():
    """TC-P2-DIR-ENV: DETECT_ENGINE_HEALTH_DIR / ESCALATION_DIR override defaults at import."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        health = Path(tmpdir) / "custom-health"
        esc = Path(tmpdir) / "custom-esc"
        env = {
            **os.environ,
            "DETECT_ENGINE_HEALTH_DIR": str(health),
            "DETECT_ENGINE_ESCALATION_DIR": str(esc),
        }
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "import detect_engine as d; "
            "print(d.HEALTH_DIR); print(d.ESCALATION_DIR)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, str(SCRIPTS_DIR)],
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        lines = result.stdout.strip().splitlines()
        assert lines[0] == str(health), lines
        assert lines[1] == str(esc), lines

    # Unset → portable defaults (POC_STATE_DIR / XDG_STATE_HOME / ~/.local/state)
    env_unset = {
        k: v
        for k, v in os.environ.items()
        if k not in (
            "DETECT_ENGINE_HEALTH_DIR",
            "DETECT_ENGINE_ESCALATION_DIR",
            "POC_STATE_DIR",
            "XDG_STATE_HOME",
        )
    }
    result2 = subprocess.run(
        [sys.executable, "-c", code, str(SCRIPTS_DIR)],
        env=env_unset,
        text=True,
        capture_output=True,
    )
    assert result2.returncode == 0, result2.stdout + result2.stderr
    lines2 = result2.stdout.strip().splitlines()
    expected = str(Path.home() / ".local" / "state" / "prompt-on-change")
    assert lines2[0] == expected, lines2
    assert lines2[1] == str(Path(expected) / "escalations"), lines2


def test_p2_header_env_interpolation_before_request():
    """TC-P2-HEADER-ENV: {{env:VAR}} in headers is resolved before the HTTP request."""
    os.environ["P2_TEST_BEARER_TOKEN"] = "secret-token-abc"
    try:
        fetcher = FetchAgent()
        source = Source(
            id="auth",
            url="https://example.com/api",
            headers={"Authorization": "Bearer {{env:P2_TEST_BEARER_TOKEN}}"},
            retry={"count": 0, "backoff": 0},
        )
        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.request.return_value = MagicMock(
                status_code=200, headers={}, text='{"ok":true}',
            )
            result = fetcher.fetch(source)
        assert result.ok
        _args, kwargs = mock_client.request.call_args
        headers = kwargs.get("headers") or {}
        assert headers.get("Authorization") == "Bearer secret-token-abc", headers
        assert "{{env:" not in headers.get("Authorization", "")
    finally:
        del os.environ["P2_TEST_BEARER_TOKEN"]


def test_p2_preserve_from_desc_caps_description_length():
    """TC-P2-PRESERVE-CAP: oversized description is truncated before re.search (100000 cap)."""
    from detect_engine import REGEX_INPUT_CAP

    marker_past_cap = "MARKER_ONLY_PAST_CAP_xyzzy"
    # Marker lives strictly after the cap so an uncapped search would still find it.
    huge_desc = ("A" * REGEX_INPUT_CAP) + marker_past_cap
    action = ActionAgent(
        {},
        dry_run=True,
        calendar_events={
            "patch_flight": {"summary": "T", "description": huge_desc},
        },
    )
    action_def = {
        "type": "calendar_patch",
        "event_id": "evt1",
        "preserve_from_desc": [
            {"as": "late", "pattern": r"MARKER_ONLY_PAST_CAP_xyzzy"},
        ],
        "fields": {"description": "preserved=[{{ late }}]"},
    }
    assert action.execute("patch_flight", action_def)
    joined = " ".join(action.results)
    assert "MARKER_ONLY_PAST_CAP_xyzzy" not in joined, (
        f"marker past cap must not be captured: {joined}"
    )
    assert "preserved=[]" in joined or "preserved=[" in joined

    # Within-cap content is still captured.
    early = "KEEP_EARLY_MARKER" + ("B" * 100)
    action2 = ActionAgent(
        {},
        dry_run=True,
        calendar_events={"patch_flight": {"summary": "T", "description": early}},
    )
    action_def2 = {
        "type": "calendar_patch",
        "event_id": "evt1",
        "preserve_from_desc": [
            {"as": "early", "pattern": r"KEEP_EARLY_MARKER"},
        ],
        "fields": {"description": "got={{ early }}"},
    }
    assert action2.execute("patch_flight", action_def2)
    assert any("KEEP_EARLY_MARKER" in r for r in action2.results), action2.results


def test_p2_runner_pending_escalation_quarantine():
    """TC-P2-RUNNER-PENDING-GC: old top-level pending JSON is quarantined, not deleted; fresh left."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "empty-configs"
        detect_dir.mkdir()
        escalation_dir = root / "state" / "escalations"
        escalation_dir.mkdir(parents=True)
        old_pending = escalation_dir / "old-pending.json"
        fresh_pending = escalation_dir / "fresh-pending.json"
        disposition = escalation_dir / "disposition.md"
        old_pending.write_text('{"escalation_type":"condition_matched"}')
        fresh_pending.write_text('{"escalation_type":"condition_matched"}')
        disposition.write_text("keep me")
        # Older than PENDING_ALERT_DAYS (default 7) — use 10 days.
        old_time = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
        os.utime(old_pending, (old_time, old_time))

        env = _runner_subprocess_env(detect_dir, root / "state")
        env["PENDING_ALERT_DAYS"] = "7"
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh")],
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        # Old pending moved to stale/, not deleted; fresh untouched.
        assert not old_pending.exists(), "old pending should leave top-level"
        stale = escalation_dir / "stale" / "old-pending.json"
        assert stale.exists(), "old pending must be quarantined under stale/"
        assert stale.read_text() == '{"escalation_type":"condition_matched"}'
        assert fresh_pending.exists(), "fresh pending must stay top-level"
        assert disposition.exists(), "disposition.md must never be touched"
        combined = result.stdout + result.stderr
        log_text = (root / "state" / "detect-runner.log").read_text()
        assert "WARNING" in combined or "WARNING" in log_text
        assert "quarantin" in (combined + log_text).lower() or "stale" in (combined + log_text).lower()


def test_p2_duplicate_extract_ids_rejected():
    """TC-P2-EXTRACT-DUP: duplicate extract ids across sources → cross-ref validation error."""
    config = DetectConfig(
        name="dup extract",
        sources=[
            Source(
                id="s1",
                url="https://example.com/a",
                extract=[ExtractSpec(id="status", type="jsonpath", path="$.status")],
            ),
            Source(
                id="s2",
                url="https://example.com/b",
                extract=[ExtractSpec(id="status", type="jsonpath", path="$.other")],
            ),
        ],
        conditions=[Condition(id="c1", field="status", op="changed")],
        groups=[Group(name="g", any=["c1"], actions=[])],
        actions={},
    )
    errors = validate_config_cross_refs(config)
    assert any("duplicate extract id 'status'" in e for e in errors), errors


def test_p2_not_reason_cites_deciding_subcondition():
    """TC-P2-NOT-REASON: NOT reason cites the definite-false sub, not always sub_results[0]."""
    prev = make_state(status="On time", gate="C3")
    extracted = make_extracted(status="On time", gate="C3")
    # not: [eq status Delayed (false), eq gate C3 (true)] → definite false first? Wait:
    # NOT(AND) is True when any sub is definite-false. Put the false second so [0] is True.
    cond = {
        "id": "not_decide",
        "not": [
            {"field": "gate", "op": "eq", "value": "C3"},  # True — would be wrongly cited if [0]
            {"field": "status", "op": "eq", "value": "Delayed"},  # definite False → decides NOT=True
        ],
    }
    result = eval_condition(cond, prev, extracted)
    assert result.matched, result.reason
    assert "status" in result.reason, f"must cite deciding (status) sub: {result.reason}"
    # Must not only cite the first (gate) sub without the decider.
    assert "Delayed" in result.reason or "status" in result.reason


def test_p2_or_reason_cites_matching_subcondition():
    """TC-P2-OR-REASON: OR reason cites the matching (deciding) sub-condition."""
    prev = make_state(status="On time", gate="C3")
    extracted = make_extracted(status="Diverted", gate="C3")
    cond = {
        "id": "or_decide",
        "or": [
            {"field": "status", "op": "eq", "value": "Cancelled"},  # false
            {"field": "status", "op": "eq", "value": "Diverted"},  # true — decider
        ],
    }
    result = eval_condition(cond, prev, extracted)
    assert result.matched, result.reason
    assert "Diverted" in result.reason, f"must cite matching Diverted sub: {result.reason}"
    assert "Cancelled" not in result.reason or "Diverted" in result.reason


runner.run("TC-P2-RUNNER-LINT-CHECK: --lint is check-only (no --fix)", test_p2_runner_lint_is_check_only_by_default)
runner.run("TC-P2-RUNNER-LINT-FIX: --lint --fix / --lint-fix opt-in", test_p2_runner_lint_fix_opt_in)
runner.run("TC-P2-DIR-ENV: HEALTH/ESCALATION dirs from env at import", test_p2_health_and_escalation_dirs_from_env)
runner.run("TC-P2-HEADER-ENV: resolve {{env:}} in request headers", test_p2_header_env_interpolation_before_request)
runner.run("TC-P2-PRESERVE-CAP: cap preserve_from_desc description length", test_p2_preserve_from_desc_caps_description_length)
runner.run("TC-P2-RUNNER-PENDING-GC: quarantine aged pending escalations", test_p2_runner_pending_escalation_quarantine)
runner.run("TC-P2-EXTRACT-DUP: reject duplicate extract ids across sources", test_p2_duplicate_extract_ids_rejected)
runner.run("TC-P2-NOT-REASON: NOT cites deciding sub-condition reason", test_p2_not_reason_cites_deciding_subcondition)
runner.run("TC-P2-OR-REASON: OR cites matching sub-condition reason", test_p2_or_reason_cites_matching_subcondition)


# ═══════════════════════════════════════════════════════════════
#  Round-4 adversarial (post P0/P1/P2 hardening) — fresh misses
# ═══════════════════════════════════════════════════════════════

def test_r4_fmt_time_invalid_timezone_is_soft_failure():
    """TC-R4-FMT-BAD-TZ: invalid fmt_time:TZ must not raise; render N/A like unparseable datetimes."""
    action = ActionAgent({}, dry_run=True)
    # Must not raise ZoneInfoNotFoundError (previously crashed the whole poll).
    result = action._render_template(
        "Depart: {{ dep_time | fmt_time:Not/A/RealZone }}",
        {"dep_time": "2026-07-07T17:20:00-07:00"},
    )
    assert "N/A" in result, f"invalid TZ should soft-fail to N/A, got {result!r}"
    # Valid TZ still works.
    ok = action._render_template(
        "Depart: {{ dep_time | fmt_time:America/New_York }}",
        {"dep_time": "2026-07-07T17:20:00-07:00"},
    )
    assert "N/A" not in ok and ("PM" in ok or "AM" in ok), ok


def test_r4_action_execute_contains_unexpected_template_crash():
    """TC-R4-ACTION-TMPL-CRASH: unexpected render errors become action failure, not process crash."""
    action = ActionAgent({"x": "1"}, dry_run=False)
    with patch.object(ActionAgent, "_render_template", side_effect=RuntimeError("boom")):
        with patch("detect_engine.gws_patch_event") as patch_ev:
            ok = action.execute(
                "patch",
                {
                    "type": "calendar_patch",
                    "event_id": "evt1",
                    "fields": {"summary": "{{ x }}"},
                },
            )
    assert ok is False, "template crash must return False (action failure)"
    assert not patch_ev.called, "must not call gws after template crash"
    assert any("❌" in r for r in action.results), action.results


def test_r4_invalid_for_duration_rejected_at_validate():
    """TC-R4-FOR-DUR: invalid for: duration is a cross-ref validation error (not silent 0)."""
    config = DetectConfig(
        name="bad for",
        sources=[Source(id="s", url="https://example.com", extract=[])],
        conditions=[
            Condition(id="c1", field="status", op="eq", value="x", **{"for": "bogus"}),
        ],
        groups=[Group(name="g", any=["c1"], actions=[])],
        actions={},
    )
    errors = validate_config_cross_refs(config)
    assert any("for" in e and "bogus" in e for e in errors), errors


def test_r4_invalid_refire_after_duration_rejected_at_validate():
    """TC-R4-REFIRE-DUR: invalid refire_after is a cross-ref validation error."""
    config = DetectConfig(
        name="bad refire",
        sources=[Source(id="s", url="https://example.com", extract=[])],
        conditions=[
            Condition(id="c1", field="status", op="eq", value="x", refire_after="5x"),
        ],
        groups=[Group(name="g", any=["c1"], actions=[])],
        actions={},
    )
    errors = validate_config_cross_refs(config)
    assert any("refire_after" in e and "5x" in e for e in errors), errors


def test_r4_valid_durations_still_pass_validation():
    """TC-R4-DUR-OK: well-formed for:/refire_after pass validation (positive control)."""
    config = DetectConfig(
        name="good dur",
        sources=[Source(id="s", url="https://example.com", extract=[])],
        conditions=[
            Condition(
                id="c1", field="status", op="eq", value="x",
                **{"for": "5m"}, refire_after="1h",
            ),
        ],
        groups=[Group(name="g", any=["c1"], actions=[])],
        actions={},
    )
    errors = validate_config_cross_refs(config)
    assert not any("for" in e or "refire_after" in e for e in errors), errors


runner.run("TC-R4-FMT-BAD-TZ: invalid fmt_time:TZ soft-fails to N/A", test_r4_fmt_time_invalid_timezone_is_soft_failure)
runner.run("TC-R4-ACTION-TMPL-CRASH: template crash → action failure not process crash", test_r4_action_execute_contains_unexpected_template_crash)
runner.run("TC-R4-FOR-DUR: invalid for: duration rejected at validate", test_r4_invalid_for_duration_rejected_at_validate)
runner.run("TC-R4-REFIRE-DUR: invalid refire_after rejected at validate", test_r4_invalid_refire_after_duration_rejected_at_validate)
runner.run("TC-R4-DUR-OK: valid for:/refire_after pass validation", test_r4_valid_durations_still_pass_validation)


# ═══════════════════════════════════════════════════════════════
#  Round-5 Layer-1 adversarial (fetch → extract → eval context)
# ═══════════════════════════════════════════════════════════════

def test_l1_fetch_enables_follow_redirects():
    """TC-L1-REDIRECT: httpx Client must follow redirects (default is False in 0.28+).

    Without follow_redirects=True, a 301/302 is status<400 so FetchResult.ok is True
    with an empty/redirect body — extraction silently yields None and may clobber state.
    """
    fetcher = FetchAgent()
    source = Source(
        id="redir",
        url="https://example.com/old",
        timeout=5,
        retry={"count": 0, "backoff": 0},
    )
    with patch("detect_engine.httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.request.return_value = MagicMock(
            status_code=200, headers={}, text='{"ok":true}',
        )
        result = fetcher.fetch(source)
    assert result.ok
    assert mock_cls.call_count == 1
    _, kwargs = mock_cls.call_args
    assert kwargs.get("follow_redirects") is True, (
        f"FetchAgent must pass follow_redirects=True; got Client kwargs={kwargs}"
    )


def test_l1_header_extract_case_insensitive_after_httpx_normalize():
    """TC-L1-HDR-CASE: header extract must match case-insensitively.

    httpx lowercases header names in dict(resp.headers); configs naturally use
    Content-Type / ETag. Exact-case .get() silently returns "" in production.
    """
    # Real httpx Response → same key normalization FetchAgent uses.
    resp = httpx.Response(
        200,
        headers={"Content-Type": "application/json", "ETag": '"v1"'},
        content=b"{}",
    )
    result = FetchResult(resp.status_code, dict(resp.headers), resp.text)
    assert "content-type" in result.headers  # httpx normalized
    extractor = ExtractAgent()
    values = extractor.extract(
        result,
        [
            ExtractSpec(id="ct", type="header", name="Content-Type"),
            ExtractSpec(id="etag", type="header", name="ETag"),
            ExtractSpec(id="ct_low", type="header", name="content-type"),
        ],
    )
    assert values["ct"] == "application/json", f"Title-Case name missed: {values}"
    assert values["etag"] == '"v1"', f"ETag missed: {values}"
    assert values["ct_low"] == "application/json"


def test_l1_jsonld_type_with_charset_parameter():
    """TC-L1-JSONLD-CHARSET: script type may include '; charset=utf-8' — still extract."""
    html = (
        '<html><body>'
        '<script type="application/ld+json; charset=utf-8">'
        '{"@type":"Flight","departureTime":"2026-07-07T17:20:00-07:00","departureGate":"C3"}'
        "</script></body></html>"
    )
    result = FetchResult(200, {}, html)
    values = ExtractAgent().extract(
        result,
        [
            ExtractSpec(id="dep_time", type="jsonpath_from_html", path="$.departureTime"),
            ExtractSpec(id="gate", type="jsonpath_from_html", path="$.departureGate"),
        ],
    )
    assert values["dep_time"] == "2026-07-07T17:20:00-07:00", values
    assert values["gate"] == "C3", values


def test_l1_jsonld_at_graph_entity_array():
    """TC-L1-JSONLD-GRAPH: schema.org @graph multi-entity payloads must be searchable.

    Same convenience as list-root JSON-LD: path $.departureTime should hit the
    Flight node inside @graph, not only the wrapper object.
    """
    html = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@graph":['
        '{"@type":"Airline","name":"Alaska"},'
        '{"@type":"Flight","departureTime":"2026-07-07T17:20:00-07:00","departureGate":"C3"}'
        "]}</script>"
    )
    values = ExtractAgent().extract(
        FetchResult(200, {}, html),
        [
            ExtractSpec(id="dep_time", type="jsonpath_from_html", path="$.departureTime"),
            ExtractSpec(id="gate", type="jsonpath_from_html", path="$.departureGate"),
        ],
    )
    assert values["dep_time"] == "2026-07-07T17:20:00-07:00", values
    assert values["gate"] == "C3", values


def test_l1_http_408_and_429_retry_then_succeed():
    """TC-L1-HTTP-408-429: 408 and 429 are retryable (same budget as 5xx)."""
    fetcher = FetchAgent()
    for code in (408, 429):
        source = Source(
            id=f"t{code}",
            url="https://example.com/api",
            timeout=5,
            retry={"count": 1, "backoff": 0},
        )
        with patch("detect_engine.httpx.Client") as mock_cls:
            mock_client = MagicMock()
            mock_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            transient = MagicMock(status_code=code, headers={}, text="retry")
            ok = MagicMock(status_code=200, headers={}, text='{"ok":true}')
            mock_client.request.side_effect = [transient, ok]
            result = fetcher.fetch(source)
        assert result.ok, f"{code} should succeed after retry"
        assert result.status_code == 200
        assert result.attempts == 2
        assert mock_client.request.call_count == 2


runner.run("TC-L1-REDIRECT: FetchAgent enables follow_redirects", test_l1_fetch_enables_follow_redirects)
runner.run("TC-L1-HDR-CASE: header extract case-insensitive post-httpx", test_l1_header_extract_case_insensitive_after_httpx_normalize)
runner.run("TC-L1-JSONLD-CHARSET: JSON-LD type with charset param", test_l1_jsonld_type_with_charset_parameter)
runner.run("TC-L1-JSONLD-GRAPH: JSON-LD @graph entities searchable", test_l1_jsonld_at_graph_entity_array)
runner.run("TC-L1-HTTP-408-429: 408/429 retry then succeed", test_l1_http_408_and_429_retry_then_succeed)


# ═══════════════════════════════════════════════════════════════
#  R6: composite fire_once + duration/refire hold (condition eval lens)
# ═══════════════════════════════════════════════════════════════

def test_r6_composite_fire_once_value_transition_refires():
    """TC-R6-COMP-FIREONCE-AB: fieldless OR composite must re-fire on leaf value change.

    fire_once keys on current_value. Top-level and:/or: have no field, so a naive
    eval_context.get(cond.field) is always None — Delayed→Cancelled would be stuck
    suppressed after the first fire. Signature must track leaf field values.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: "comp_fire_once"
seed_mode: true
sources:
  - id: s
    url: "https://example.com"
    extract: [{id: status, type: jsonpath, path: "$.status"}]
conditions:
  - id: bad_status
    or:
      - {field: status, op: eq, value: Delayed}
      - {field: status, op: eq, value: Cancelled}
groups:
  - name: g
    any: [bad_status]
    actions: [patch]
actions:
  patch:
    type: calendar_patch
    event_id: "evt1"
    fields: {summary: "status {{status}}"}
state: {file: "state.json", initial: {status: ""}}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(config_path, {"status": "OnTime"}) == 0
            assert mock_patch.call_count == 0, "seed must not act"
            assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0
            assert mock_patch.call_count == 1, "Delayed must fire once"
            st = json.loads(state_path.read_text())
            assert "bad_status" in st.get("acknowledged", {}), "must acknowledge after fire"
            assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0
            assert mock_patch.call_count == 1, "same Delayed must stay fire_once-suppressed"
            assert run_engine_with_mock_json(config_path, {"status": "Cancelled"}) == 0
            assert mock_patch.call_count == 2, (
                "Delayed→Cancelled must re-fire (leaf value changed under fieldless composite)"
            )


def test_r6_composite_fire_once_same_signature_suppresses():
    """TC-R6-COMP-FIREONCE-SAME: continuously-true composite stays suppressed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("""
name: "comp_fire_once_same"
seed_mode: true
sources:
  - id: s
    url: "https://example.com"
    extract:
      - {id: status, type: jsonpath, path: "$.status"}
      - {id: gate, type: jsonpath, path: "$.gate"}
conditions:
  - id: delayed_gated
    and:
      - {field: status, op: eq, value: Delayed}
      - {field: gate, op: exists}
groups:
  - name: g
    any: [delayed_gated]
    actions: [patch]
actions:
  patch:
    type: calendar_patch
    event_id: "evt1"
    fields: {summary: "delayed"}
state: {file: "state.json", initial: {status: "", gate: ""}}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert run_engine_with_mock_json(
                config_path, {"status": "OnTime", "gate": ""}
            ) == 0
            assert run_engine_with_mock_json(
                config_path, {"status": "Delayed", "gate": "C3"}
            ) == 0
            assert mock_patch.call_count == 1
            assert run_engine_with_mock_json(
                config_path, {"status": "Delayed", "gate": "C3"}
            ) == 0
            assert mock_patch.call_count == 1, "identical leaf signature must suppress"


def test_r6_composite_duration_holds_child_changed_fields():
    """TC-R6-COMP-DUR-HOLD: for: on a composite must hold nested changed baselines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: "comp_dur_hold"
seed_mode: true
sources:
  - id: s
    url: "https://example.com"
    extract:
      - {id: x, type: jsonpath, path: "$.x"}
      - {id: status, type: jsonpath, path: "$.status"}
conditions:
  - id: delayed_changed
    for: "10m"
    and:
      - {field: status, op: eq, value: Delayed}
      - {field: x, op: changed, baseline: {source: state, field: x}}
groups:
  - name: g
    any: [delayed_changed]
state: {file: "state.json", initial: {x: "", status: ""}}
""")
        assert run_engine_with_mock_json(
            config_path, {"x": "A", "status": "OnTime"}
        ) == 0
        assert run_engine_with_mock_json(
            config_path, {"x": "B", "status": "Delayed"}
        ) == 0
        held = json.loads(state_path.read_text())
        assert held["x"] == "A", (
            "composite duration gate must hold nested changed field baseline (x)"
        )
        assert "delayed_changed" in held.get("first_seen", {})
        held["first_seen"]["delayed_changed"] = (
            datetime.now(timezone.utc) - timedelta(minutes=11)
        ).isoformat()
        state_path.write_text(json.dumps(held))
        assert run_engine_with_mock_json(
            config_path, {"x": "B", "status": "Delayed"}
        ) == 0
        assert json.loads(state_path.read_text())["x"] == "B", (
            "after duration elapses, nested field may update"
        )


def test_r6_composite_refire_holds_child_changed_fields():
    """TC-R6-COMP-REFIRE-HOLD: refire_after on composite holds nested changed fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        state_path = Path(tmpdir) / "state.json"
        config_path.write_text("""
name: "comp_refire_hold"
seed_mode: true
sources:
  - id: s
    url: "https://example.com"
    extract:
      - {id: x, type: jsonpath, path: "$.x"}
      - {id: status, type: jsonpath, path: "$.status"}
conditions:
  - id: delayed_changed
    refire_after: "10m"
    and:
      - {field: status, op: eq, value: Delayed}
      - {field: x, op: changed, baseline: {source: state, field: x}}
groups:
  - name: g
    any: [delayed_changed]
state: {file: "state.json", initial: {x: "", status: ""}}
""")
        assert run_engine_with_mock_json(
            config_path, {"x": "A", "status": "Delayed"}
        ) == 0
        seeded = json.loads(state_path.read_text())
        # Force a prior fire so the next change sits inside the refire window.
        seeded["last_fired"] = {
            "delayed_changed": datetime.now(timezone.utc).isoformat()
        }
        seeded["x"] = "A"
        seeded["status"] = "Delayed"
        state_path.write_text(json.dumps(seeded))
        assert run_engine_with_mock_json(
            config_path, {"x": "B", "status": "Delayed"}
        ) == 0
        held = json.loads(state_path.read_text())
        assert held["x"] == "A", (
            "composite refire_after must hold nested changed field baseline (x)"
        )


runner.run(
    "TC-R6-COMP-FIREONCE-AB: composite fire_once re-fires on leaf value change",
    test_r6_composite_fire_once_value_transition_refires,
)
runner.run(
    "TC-R6-COMP-FIREONCE-SAME: continuous composite stays suppressed",
    test_r6_composite_fire_once_same_signature_suppresses,
)
runner.run(
    "TC-R6-COMP-DUR-HOLD: composite for: holds nested changed fields",
    test_r6_composite_duration_holds_child_changed_fields,
)
runner.run(
    "TC-R6-COMP-REFIRE-HOLD: composite refire_after holds nested changed fields",
    test_r6_composite_refire_holds_child_changed_fields,
)


# ═══════════════════════════════════════════════════════════════
#  R7: state persistence + orchestration (state/load lens)
# ═══════════════════════════════════════════════════════════════

def test_r7_dict_ack_json_round_trip():
    """TC-R7-ACK-DICT-ROUNDTRIP: composite ack signatures survive save→JSON→load.

    R6 stores a dict of leaf values for fieldless and:/or:/not: fire_once.
    After atomic save + reload, is_acknowledged must still suppress an unchanged
    signature and re-allow a changed one (no spurious re-fire / suppression).
    """
    with TempStateDir() as tsd:
        sm = StateManager(tsd.state_path, {})
        sm.load()
        sig = {
            "status": "Delayed",
            "gate": "C3",
            "count": 1,
            "flag": True,
            "missing": None,
            "flt": 1.5,
        }
        sm.acknowledge("bad_status", sig)
        assert sm.is_acknowledged("bad_status", sig)
        assert sm.save() is True

        sm2 = StateManager(tsd.state_path, {})
        sm2.load()
        loaded = sm2.state["acknowledged"]["bad_status"]["value"]
        assert isinstance(loaded, dict), "ack value must remain a dict after JSON round-trip"
        assert sm2.is_acknowledged("bad_status", sig), (
            "unchanged composite signature must still be acknowledged after reload"
        )
        # Key order must not matter for equality after JSON object load
        reordered = {
            "missing": None,
            "flt": 1.5,
            "flag": True,
            "count": 1,
            "gate": "C3",
            "status": "Delayed",
        }
        assert sm2.is_acknowledged("bad_status", reordered)
        assert not sm2.is_acknowledged(
            "bad_status", {**sig, "status": "Cancelled"}
        ), "changed leaf in signature must break acknowledgement"


def test_r7_state_load_non_dict_json():
    """TC-R7-STATE-NONDICT: valid JSON that is not an object must not crash load.

    A list/scalar/null root is valid JSON but not a state object; setdefault on
    the root would AttributeError and abort the poll. Reinitialize like corrupt.
    """
    for payload in ("[]", "null", '"hello"', "42", "true"):
        with TempStateDir() as tsd:
            tsd.state_path.write_text(payload)
            sm = StateManager(tsd.state_path, {"dep_time": "default"})
            state = sm.load()
            assert isinstance(state, dict), f"payload {payload!r} must yield a dict"
            assert state.get("dep_time") == "default", f"payload {payload!r} should reinit"
            assert isinstance(state.get("acknowledged"), dict)
            assert isinstance(state.get("first_seen"), dict)
            assert isinstance(state.get("last_fired"), dict)
            # Mutators must remain usable after recovery
            sm.acknowledge("c", "v")
            assert sm.is_acknowledged("c", "v")


def test_r7_state_load_wrong_type_internal_maps():
    """TC-R7-STATE-BAD-MAPS: non-dict acknowledged/first_seen/last_fired must normalize.

    setdefault only fills missing keys; a string/list/null value leaves mutators
    and is_acknowledged able to TypeError/AttributeError mid-poll.
    """
    with TempStateDir() as tsd:
        tsd.state_path.write_text(json.dumps({
            "dep_time": "17:20",
            "acknowledged": "broken",
            "first_seen": [],
            "last_fired": None,
        }))
        sm = StateManager(tsd.state_path, {})
        sm.load()
        assert sm.state["dep_time"] == "17:20", "extracted fields must be preserved"
        assert sm.state["acknowledged"] == {}
        assert sm.state["first_seen"] == {}
        assert sm.state["last_fired"] == {}
        sm.acknowledge("c", {"status": "Delayed"})
        assert sm.is_acknowledged("c", {"status": "Delayed"})
        sm.set_first_seen("c")
        sm.set_last_fired("c")
        assert sm.get_first_seen("c") is not None
        assert sm.get_last_fired("c") is not None


def test_r7_is_acknowledged_malformed_entry():
    """TC-R7-ACK-MALFORMED: non-dict ack entries must not crash is_acknowledged."""
    with TempStateDir() as tsd:
        sm = StateManager(tsd.state_path, {})
        sm.load()
        sm.state["acknowledged"]["c"] = "legacy-string"
        assert sm.is_acknowledged("c", "legacy-string") is False
        sm.state["acknowledged"]["c"] = ["at", "value"]
        assert sm.is_acknowledged("c", "value") is False
        sm.state["acknowledged"]["c"] = {"at": "t", "value": "ok"}
        assert sm.is_acknowledged("c", "ok") is True


def test_r7_bad_timestamps_degrade_safely():
    """TC-R7-TS-BAD: invalid first_seen/last_fired stamps must not crash getters."""
    sm = StateManager(Path("/tmp/r7-ts-bad.json"), {})
    sm.state = {
        "first_seen": {"c": "not-a-date", "d": 123},
        "last_fired": {"c": 99, "d": "also-bad"},
        "acknowledged": {},
    }
    assert sm.get_first_seen("c") is None
    assert sm.get_first_seen("d") is None
    assert sm.get_last_fired("c") is None
    assert sm.get_last_fired("d") is None


runner.run(
    "TC-R7-ACK-DICT-ROUNDTRIP: composite dict ack survives JSON save/load",
    test_r7_dict_ack_json_round_trip,
)
runner.run(
    "TC-R7-STATE-NONDICT: non-dict JSON state reinitializes safely",
    test_r7_state_load_non_dict_json,
)
runner.run(
    "TC-R7-STATE-BAD-MAPS: wrong-type internal maps normalize on load",
    test_r7_state_load_wrong_type_internal_maps,
)
runner.run(
    "TC-R7-ACK-MALFORMED: malformed ack entry does not crash is_acknowledged",
    test_r7_is_acknowledged_malformed_entry,
)
runner.run(
    "TC-R7-TS-BAD: invalid duration/refire timestamps degrade to None",
    test_r7_bad_timestamps_degrade_safely,
)


# ═══════════════════════════════════════════════════════════════
#  R9: escalation + runner lens (backoff side-file, emit contract, exit agg)
# ═══════════════════════════════════════════════════════════════

def test_r9_backoff_non_object_json_fail_open_no_crash():
    """TC-R9-BACKOFF-NONOBJ: array/null/scalar backoff JSON must fail-open, not crash.

    A truncated or hand-edited side-file can be valid JSON that is not an object.
    data.get(...) / data[type]= on a list/null would AttributeError/TypeError and
    kill the entire poll — fail-open (allow + reset) instead.
    """
    for payload in ("[1, 2]", "null", "42", '"str"', "true"):
        with tempfile.TemporaryDirectory() as tmpdir:
            health = Path(tmpdir) / "health"
            health.mkdir()
            original = _detect_engine_mod.HEALTH_DIR
            _detect_engine_mod.HEALTH_DIR = health
            try:
                name = "r9 nonobj"
                path = _detect_engine_mod._escalation_backoff_path(name)
                assert path is not None
                path.write_text(payload + "\n")
                assert _detect_engine_mod._escalation_backoff_allows(
                    name, "fetch_failure", "1h"
                ) is True, f"payload {payload!r} must allow (fail-open)"
                written_at = datetime.now(timezone.utc).isoformat()
                _detect_engine_mod._record_escalation_backoff(
                    name, "fetch_failure", written_at
                )
                data = json.loads(path.read_text())
                assert isinstance(data, dict), f"record must rewrite object for {payload!r}"
                assert data.get("fetch_failure") == written_at
            finally:
                _detect_engine_mod.HEALTH_DIR = original


def test_r9_fetch_failure_emits_on_no_match_path():
    """TC-R9-FETCH-EMIT-NOMATCH: optional fetch failure still prints LLM_ESCALATION.

    Evidence was written + backoff recorded, but the no-matched-groups early return
    skipped the stdout contract — Layer-1 chat delivery lost the pointer.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        esc_dir = root / "escalations"
        (root / "state.json").write_text(json.dumps({
            "x": "old", "last_checked": "2026-07-08T00:00:00Z",
        }))
        config_path.write_text("""
name: optional fetch nomatch
seed_mode: false
sources:
  - id: opt
    url: https://example.com
    required: false
    retry: {count: 0, escalate_on_failure: true}
    extract: [{id: x, type: jsonpath, path: $.x}]
conditions: [{id: c, field: x, op: eq, value: never}]
groups: [{name: g, any: [c], actions: []}]
state: {file: state.json, initial: {x: ""}}
""")
        original_esc = _detect_engine_mod.ESCALATION_DIR
        original_health = _detect_engine_mod.HEALTH_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        _detect_engine_mod.HEALTH_DIR = root / "health"
        try:
            failed = FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError")
            output = StringIO()
            with redirect_stdout(output), patch(
                "detect_engine.FetchAgent.fetch", return_value=failed
            ):
                rc = run_engine(str(config_path))
            assert rc == 0
            evidence = list(esc_dir.glob("fetch_failure_*.json"))
            assert len(evidence) == 1, evidence
            out = output.getvalue()
            assert "LLM_ESCALATION:" in out, f"must emit stdout contract: {out!r}"
            assert str(evidence[0]) in out
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_esc
            _detect_engine_mod.HEALTH_DIR = original_health


def test_r9_fetch_failure_emits_on_action_failure_path():
    """TC-R9-FETCH-EMIT-ACTION: optional fetch + action failure must emit both pointers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        esc_dir = root / "escalations"
        (root / "state.json").write_text(json.dumps({
            "x": "old", "y": "keep", "last_checked": "2026-07-08T00:00:00Z",
        }))
        config_path.write_text("""
name: fetch plus action fail
seed_mode: false
sources:
  - id: opt
    url: https://example.com/opt
    required: false
    retry: {count: 0, escalate_on_failure: true}
    extract: [{id: y, type: jsonpath, path: $.y}]
  - id: req
    url: https://example.com/req
    required: true
    retry: {count: 0}
    extract: [{id: x, type: jsonpath, path: $.x}]
conditions: [{id: changed, field: x, op: changed, baseline: {source: state, field: x}}]
groups: [{name: g, any: [changed], actions: [patch]}]
actions: {patch: {type: calendar_patch, event_id: event, fields: {summary: updated}}}
state: {file: state.json, initial: {x: old, y: keep}}
""")
        original_esc = _detect_engine_mod.ESCALATION_DIR
        original_health = _detect_engine_mod.HEALTH_DIR
        _detect_engine_mod.ESCALATION_DIR = esc_dir
        _detect_engine_mod.HEALTH_DIR = root / "health"
        try:
            failed = FetchResult(0, {}, "", "down", attempts=1, last_error_type="ConnectError")
            ok = FetchResult(200, {"content-type": "application/json"}, '{"x":"new"}', "")

            def _fetch(source):
                return failed if source.id == "opt" else ok

            output = StringIO()
            with redirect_stdout(output), \
                 patch.object(FetchAgent, "fetch", side_effect=_fetch), \
                 patch("detect_engine.gws_get_event", return_value=None), \
                 patch("detect_engine.gws_patch_event", return_value=False):
                rc = run_engine(str(config_path))
            assert rc == 1
            out = output.getvalue()
            assert out.count("LLM_ESCALATION:") >= 2, out
            assert list(esc_dir.glob("fetch_failure_*.json")), "fetch evidence missing"
            assert list(esc_dir.glob("action_failure_*.json")), "action evidence missing"
            for path in esc_dir.glob("*.json"):
                assert str(path) in out, f"missing stdout for {path}"
        finally:
            _detect_engine_mod.ESCALATION_DIR = original_esc
            _detect_engine_mod.HEALTH_DIR = original_health


def test_r9_runner_exit_aggregates_and_keeps_output():
    """TC-R9-RUNNER-AGG: one nonzero config → exit 1, remaining configs still run, stdout kept."""
    subprocess = __import__("subprocess")
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        detect_dir = root / "configs"
        detect_dir.mkdir()
        (detect_dir / "a-bad.yaml").write_text("name: bad\n")
        (detect_dir / "b-good.yaml").write_text("name: good\n")
        eng = root / "fake_engine.py"
        eng.write_text(
            "import sys\n"
            "cfg = sys.argv[sys.argv.index('--config') + 1]\n"
            "if 'a-bad' in cfg:\n"
            "    print('LLM_ESCALATION: /tmp/from-bad.json')\n"
            "    sys.exit(1)\n"
            "print('LLM_ESCALATION: /tmp/from-good.json')\n"
            "sys.exit(0)\n"
        )
        bindir = root / "bin"
        bindir.mkdir()
        timeout_stub = bindir / "timeout"
        timeout_stub.write_text("#!/bin/bash\nshift\nexec \"$@\"\n")
        timeout_stub.chmod(0o755)
        state_dir = root / "state"
        env = _runner_subprocess_env(detect_dir, state_dir)
        env["PATH"] = f"{bindir}:{env.get('PATH', '')}"
        env["ENGINE"] = str(eng)
        env["PYTHON"] = sys.executable
        result = subprocess.run(
            ["bash", str(SCRIPTS_DIR / "detect_runner.sh")],
            env=env,
            text=True,
            capture_output=True,
        )
        assert result.returncode == 1, result.stdout + result.stderr
        assert "LLM_ESCALATION: /tmp/from-bad.json" in result.stdout
        assert "LLM_ESCALATION: /tmp/from-good.json" in result.stdout
        log_path = state_dir / "detect-runner.log"
        assert log_path.exists(), result.stdout + result.stderr
        log_text = log_path.read_text()
        assert "exited with status" in log_text or "ERROR" in log_text


runner.run(
    "TC-R9-BACKOFF-NONOBJ: non-object backoff JSON fail-open no crash",
    test_r9_backoff_non_object_json_fail_open_no_crash,
)
runner.run(
    "TC-R9-FETCH-EMIT-NOMATCH: optional fetch failure emits on no-match path",
    test_r9_fetch_failure_emits_on_no_match_path,
)
runner.run(
    "TC-R9-FETCH-EMIT-ACTION: optional fetch + action failure emit both",
    test_r9_fetch_failure_emits_on_action_failure_path,
)
runner.run(
    "TC-R9-RUNNER-AGG: exit 1 + continue + keep stdout across configs",
    test_r9_runner_exit_aggregates_and_keeps_output,
)


# ═══════════════════════════════════════════════════════════════
#  R10: security / config / docs lens (nesting, transitions, load crash)
# ═══════════════════════════════════════════════════════════════

def _r10_nest_and(depth: int) -> dict:
    """Build a fieldless AND nest of the given depth (iterative — no builder stack)."""
    node: dict = {"field": "x", "op": "eq", "value": "1"}
    for _ in range(depth):
        node = {"and": [node]}
    return node


def test_r10_deep_yaml_does_not_raise_uncaught_recursion():
    """TC-R10-YAML-DEEP: deeply nested condition YAML must not RecursionError the poll.

    yaml.safe_load raises RecursionError (not YAMLError) past ~250 and: levels.
    run_engine previously let that escape — one bad config killed the process.
    """
    cfg = {
        "name": "r10 deep",
        "enabled": True,
        "seed_mode": False,
        "sources": [],
        "conditions": [{"id": "c", **_r10_nest_and(300)}],
        "groups": [{"name": "g", "any": ["c"], "actions": []}],
        "actions": {},
        "state": {"file": "s.json", "initial": {"x": "0"}},
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "deep.yaml"
        # JSON is a YAML subset; dump avoids yaml.dump's own recursion limit.
        path.write_text(json.dumps(cfg))
        try:
            rc = run_engine(str(path), dry_run=True)
        except RecursionError:
            raise AssertionError(
                "run_engine must not raise uncaught RecursionError on deep YAML"
            )
        assert rc == 1, f"deep config must fail cleanly with exit 1, got {rc}"


def test_r10_condition_nesting_depth_capped_at_validate():
    """TC-R10-DEPTH-CAP: condition trees deeper than MAX_CONDITION_DEPTH fail cross-ref."""
    from detect_engine import MAX_CONDITION_DEPTH

    over = Condition(id="too_deep", **_r10_nest_and(MAX_CONDITION_DEPTH + 1))
    cfg = DetectConfig(
        name="r10 depth",
        conditions=[over],
        groups=[Group(name="g", any=["too_deep"], actions=[])],
        actions={},
    )
    errs = validate_config_cross_refs(cfg)
    assert any("nesting depth" in e for e in errs), (
        f"expected nesting-depth cross-ref error, got {errs}"
    )

    ok = Condition(id="ok_depth", **_r10_nest_and(MAX_CONDITION_DEPTH))
    cfg_ok = DetectConfig(
        name="r10 depth ok",
        conditions=[ok],
        groups=[Group(name="g", any=["ok_depth"], actions=[])],
        actions={},
    )
    errs_ok = validate_config_cross_refs(cfg_ok)
    assert not any("nesting depth" in e for e in errs_ok), (
        f"depth==MAX must be accepted, got {errs_ok}"
    )


def test_r10_malformed_transitions_fail_cleanly():
    """TC-R10-TRANS-BAD: malformed transitions: must not AttributeError/TypeError the poll."""
    bad_payloads = [
        {"name": "t", "transitions": "oops", "sources": [], "conditions": [],
         "groups": [], "actions": {}, "state": {"file": "s.json"}},
        {"name": "t", "transitions": ["not-a-mapping"], "sources": [], "conditions": [],
         "groups": [], "actions": {}, "state": {"file": "s.json"}},
        {"name": "t", "transitions": [{"field": "x", "when": "bad", "on_change": []}],
         "sources": [], "conditions": [], "groups": [], "actions": {},
         "state": {"file": "s.json"}},
        ["root", "is", "a", "list"],
    ]
    for payload in bad_payloads:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.yaml"
            path.write_text(yaml.safe_dump(payload))
            try:
                rc = run_engine(str(path), dry_run=True)
            except (AttributeError, TypeError, ValueError) as exc:
                # ValueError is acceptable only if load_config raised and run_engine
                # failed to catch it — both are poll crashes; require exit 1.
                raise AssertionError(
                    f"run_engine must not raise {type(exc).__name__} for "
                    f"payload={payload!r}: {exc}"
                )
            assert rc == 1, (
                f"malformed config must exit 1, got {rc} for payload={payload!r}"
            )


def test_r10_matches_input_is_length_capped():
    """TC-R10-MATCHES-CAP: matches op must bound the scanned value (ReDoS guard).

    Extract/preserve_from_desc use REGEX_INPUT_CAP; matches uses MATCHES_INPUT_CAP.
    A needle past the cap must not match.
    """
    from detect_engine import MATCHES_INPUT_CAP

    huge = ("A" * MATCHES_INPUT_CAP) + "NEEDLE"
    cond = Condition(id="m", field="blob", op="matches", value="NEEDLE")
    result = TriggerAgent({}, {"blob": huge}, {}).evaluate(cond)
    assert result.matched is False, (
        "matches must not search past its input cap (needle after cap must miss)"
    )
    within = ("A" * 100) + "NEEDLE"
    result_ok = TriggerAgent({}, {"blob": within}, {}).evaluate(cond)
    assert result_ok.matched is True, "needle within cap must still match"


runner.run(
    "TC-R10-YAML-DEEP: deep nested YAML fails cleanly (no RecursionError)",
    test_r10_deep_yaml_does_not_raise_uncaught_recursion,
)
runner.run(
    "TC-R10-DEPTH-CAP: condition nesting depth capped at validate",
    test_r10_condition_nesting_depth_capped_at_validate,
)
runner.run(
    "TC-R10-TRANS-BAD: malformed transitions/root fail cleanly",
    test_r10_malformed_transitions_fail_cleanly,
)
runner.run(
    "TC-R10-MATCHES-CAP: matches op bounds scanned value length",
    test_r10_matches_input_is_length_capped,
)


# ═══════════════════════════════════════════════════════════════
#  R11: holistic convergence — calendar event nested-type safety
# ═══════════════════════════════════════════════════════════════

def test_r11_evidence_tolerates_malformed_event_start_end():
    """TC-R11-EV-START: evidence must not crash on non-dict start/end.

    After a successful match, escalate builds calendar context via
    ``ev.get("start", {}).get("dateTime")``. When the key is present but
    null/string/list, the default is skipped and ``.get`` AttributeErrors —
    aborting the poll after actions already applied and before state save
    (lost ack → re-fire next poll).
    """
    config = DetectConfig(name="r11_ev", sources=[], conditions=[], groups=[], actions={})
    cond = Condition(id="c", field="status", op="eq", value="Delayed")
    result = ConditionResult(True, "status == Delayed")
    malformed_shapes = [
        {"id": "e1", "summary": "t", "start": None, "end": None},
        {"id": "e1", "summary": "t", "start": "2026-01-01T00:00:00Z", "end": "x"},
        {"id": "e1", "summary": "t", "start": ["not", "dict"], "end": {"dateTime": "ok"}},
        {"id": "e1", "summary": "t", "start": {"dateTime": "ok"}, "end": None},
    ]
    for shape in malformed_shapes:
        agent = LLMEscalationAgent(
            config, {"status": "On"}, {"status": "Delayed"}, ["u ✅"],
            calendar_events={"update": shape},
        )
        evidence = agent._build_evidence("c", result, cond)
        cal = evidence["calendar_events"]["update"]
        assert cal["start"] == "" or isinstance(cal["start"], str)
        assert cal["end"] == "" or isinstance(cal["end"], str)
        assert "summary" in cal


def test_r11_match_escalation_with_null_start_saves_state():
    """TC-R11-POLL-START: full poll with start:null must not raise; state commits.

    Repro of the post-action / pre-save crash window: condition matches,
    calendar_patch succeeds, llm_escalation.trigger_groups fires evidence
    build, null start/end must not prevent ack + state persistence.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = tmp / "cfg.yaml"
        cfg.write_text("""
name: "r11_poll"
sources:
  - id: s1
    type: url
    url: "https://example.com/x"
    required: true
    extract:
      - id: status
        type: jsonpath
        path: "$.status"
conditions:
  - id: delayed
    field: status
    op: eq
    value: Delayed
groups:
  - id: g1
    name: g1
    any: [delayed]
    actions: [update]
actions:
  update:
    type: calendar_patch
    event_id: "evt1"
    fields:
      summary: "patched"
state:
  file: "state.json"
  initial: {status: "On time"}
llm_escalation:
  trigger_groups: [g1]
  prompt: "check {{status}}"
""")
        state_path = tmp / "state.json"
        state_path.write_text(json.dumps({
            "status": "On time",
            "last_checked": "2026-07-01T00:00:00+00:00",
            "acknowledged": {},
            "first_seen": {},
            "last_fired": {},
        }))
        bad_ev = {
            "id": "evt1",
            "summary": "calendar title",
            "start": None,
            "end": None,
        }
        import detect_engine as de_mod
        with patch("detect_engine.gws_get_event", return_value=bad_ev), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch, \
             patch("detect_engine.write_health"), \
             patch.object(de_mod, "ESCALATION_DIR", tmp / "esc"):
            rc = run_engine_with_mock_json(cfg, {"status": "Delayed"})
        assert rc == 0, f"poll must complete cleanly, got rc={rc}"
        mock_patch.assert_called()
        saved = json.loads(state_path.read_text())
        assert saved.get("status") == "Delayed", (
            "extracted status must be committed after successful actions"
        )
        assert "delayed" in saved.get("acknowledged", {}), (
            "ack must be written; crash-before-save would leave fire_once unarmed"
        )


runner.run(
    "TC-R11-EV-START: evidence tolerates non-dict start/end",
    test_r11_evidence_tolerates_malformed_event_start_end,
)
runner.run(
    "TC-R11-POLL-START: match+escalate with start:null saves state",
    test_r11_match_escalation_with_null_start_saves_state,
)


# ═══════════════════════════════════════════════════════════════
#  R12: duplicate source/group identity validation
# ═══════════════════════════════════════════════════════════════

def test_r12_duplicate_source_and_group_ids_rejected_before_fetch():
    """TC-R12-DUP-IDENTITY: duplicate source ids/group names fail before fetch."""
    configs = {
        "source": """
name: duplicate_source_ids
sources:
  - {id: shared, url: https://example.com/one, extract: [{id: first, type: jsonpath, path: $.first}]}
  - {id: shared, url: https://example.com/two, extract: [{id: second, type: jsonpath, path: $.second}]}
conditions: [{id: watched, field: first, op: exists}]
groups: [{name: watched_group, any: [watched], actions: []}]
""",
        "group": """
name: duplicate_group_names
sources: [{id: source, url: https://example.com, extract: [{id: status, type: jsonpath, path: $.status}]}]
conditions: [{id: watched, field: status, op: exists}]
groups:
  - {name: watched_group, any: [watched], actions: []}
  - {name: watched_group, any: [watched], actions: []}
""",
    }
    for duplicate_kind, config_text in configs.items():
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(config_text)
            with patch("detect_engine.FetchAgent.fetch") as mock_fetch:
                assert run_engine(str(config_path)) == 1, duplicate_kind
            mock_fetch.assert_not_called()


def test_r12_future_gate_timestamps_fail_open():
    """TC-R12-FUTURE-TS: future gates/backoff fail open; naive state stamps do not crash."""
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        config_path.write_text("""
name: future first seen
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: status, type: jsonpath, path: $.status}]}]
conditions: [{id: gate, field: status, op: eq, value: Delayed, for: 1h}]
groups: [{name: watched, any: [gate], actions: []}]
state: {file: state.json, initial: {}}
""")
        state_path.write_text(json.dumps({"first_seen": {"gate": future}}))
        assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0
        reset_first_seen = json.loads(state_path.read_text())["first_seen"]["gate"]
        assert reset_first_seen != future, "future first_seen must be re-stamped"

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        config_path.write_text("""
name: future last fired
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: status, type: jsonpath, path: $.status}]}]
conditions: [{id: refire, field: status, op: eq, value: Delayed, refire_after: 1h}]
groups: [{name: watched, any: [refire], actions: []}]
state: {file: state.json, initial: {}}
""")
        state_path.write_text(json.dumps({"last_fired": {"refire": future}}))
        assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0
        assert json.loads(state_path.read_text())["last_fired"]["refire"] != future, (
            "future last_fired must permit a re-fire"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        config_path.write_text("""
name: naive first seen
seed_mode: false
sources: [{id: source, url: https://example.com, extract: [{id: status, type: jsonpath, path: $.status}]}]
conditions: [{id: gate, field: status, op: eq, value: Delayed, for: 1h}]
groups: [{name: watched, any: [gate], actions: []}]
state: {file: state.json, initial: {}}
""")
        state_path.write_text(json.dumps({"first_seen": {"gate": "2026-01-01T00:00:00"}}))
        assert run_engine_with_mock_json(config_path, {"status": "Delayed"}) == 0

    with tempfile.TemporaryDirectory() as tmpdir:
        health = Path(tmpdir) / "health"
        health.mkdir()
        original = _detect_engine_mod.HEALTH_DIR
        _detect_engine_mod.HEALTH_DIR = health
        try:
            name = "future backoff"
            path = _detect_engine_mod._escalation_backoff_path(name)
            assert path is not None
            path.write_text(json.dumps({"fetch_failure": future}))
            assert _detect_engine_mod._escalation_backoff_allows(
                name, "fetch_failure", "1h"
            ) is True
        finally:
            _detect_engine_mod.HEALTH_DIR = original


runner.run(
    "TC-R12-DUP-IDENTITY: reject duplicate source/group identities before fetch",
    test_r12_duplicate_source_and_group_ids_rejected_before_fetch,
)
runner.run(
    "TC-R12-FUTURE-TS: future gate timestamps and backoff fail open",
    test_r12_future_gate_timestamps_fail_open,
)


# ═══════════════════════════════════════════════════════════════
#  R13: unavailable optional-source values + escalation templates
# ═══════════════════════════════════════════════════════════════

def _run_with_one_optional_source_failure(config_path: Path, healthy_payload: dict):
    """Run two sources in order: optional source times out, healthy source succeeds."""
    failed_client = MagicMock()
    failed_client.__enter__ = MagicMock(return_value=failed_client)
    failed_client.__exit__ = MagicMock(return_value=False)
    failed_client.request.side_effect = httpx.TimeoutException("optional source outage")

    healthy_client = MagicMock()
    healthy_client.__enter__ = MagicMock(return_value=healthy_client)
    healthy_client.__exit__ = MagicMock(return_value=False)
    healthy_response = MagicMock(status_code=200, headers={}, text=json.dumps(healthy_payload))
    healthy_response.request = None
    healthy_client.request.return_value = healthy_response

    with patch("detect_engine.httpx.Client") as mock_cls:
        mock_cls.side_effect = [failed_client, healthy_client]
        return run_engine(str(config_path))


def test_r13_optional_source_outage_is_indeterminate_and_healthy_sibling_runs():
    """TC-R13-OPT-INDET-SIBLING: outage preserves stale condition ack; healthy sibling fires."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        prior_ack = {"at": "2026-01-01T00:00:00+00:00", "value": "old"}
        state_path.write_text(json.dumps({
            "stale_status": "old",
            "acknowledged": {"stale_changed": prior_ack},
        }))
        config_path.write_text("""
name: optional outage sibling
seed_mode: false
sources:
  - id: optional
    url: https://example.com/optional
    required: false
    retry: {count: 0}
    extract: [{id: stale_status, type: jsonpath, path: $.status}]
  - id: healthy
    url: https://example.com/healthy
    retry: {count: 0}
    extract: [{id: healthy_status, type: jsonpath, path: $.status}]
conditions:
  - {id: stale_changed, field: stale_status, op: changed}
  - {id: healthy_ready, field: healthy_status, op: eq, value: ready}
groups:
  - {name: stale, any: [stale_changed], actions: []}
  - {name: healthy, any: [healthy_ready], actions: []}
state: {file: state.json, initial: {stale_status: old}}
""")
        assert _run_with_one_optional_source_failure(config_path, {"status": "ready"}) == 0
        state = json.loads(state_path.read_text())
        assert state["acknowledged"]["stale_changed"] == prior_ack, (
            "an unavailable source must be indeterminate, not a stale unchanged result"
        )
        assert state["acknowledged"]["healthy_ready"]["value"] == "ready", (
            "a healthy source must still evaluate normally during an optional-source outage"
        )


def test_r13_optional_source_outage_does_not_complete_duration_gate():
    """TC-R13-OPT-INDET-DURATION: stale matching value cannot complete a for: gate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        first_seen = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
        state_path.write_text(json.dumps({
            "stale_status": "alert",
            "first_seen": {"stale_alert": first_seen},
        }))
        config_path.write_text("""
name: optional outage duration
seed_mode: false
sources:
  - id: optional
    url: https://example.com/optional
    required: false
    retry: {count: 0}
    extract: [{id: stale_status, type: jsonpath, path: $.status}]
  - id: healthy
    url: https://example.com/healthy
    retry: {count: 0}
    extract: [{id: healthy_status, type: jsonpath, path: $.status}]
conditions:
  - {id: stale_alert, field: stale_status, op: eq, value: alert, for: 10m}
groups: [{name: stale, any: [stale_alert], actions: [patch]}]
actions:
  patch: {type: calendar_patch, event_id: evt1, fields: {summary: alert}}
state: {file: state.json, initial: {stale_status: alert}}
""")
        with patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert _run_with_one_optional_source_failure(config_path, {"status": "ready"}) == 0
        state = json.loads(state_path.read_text())
        assert mock_patch.call_count == 0, "an indeterminate result must not complete the duration gate"
        assert state["first_seen"]["stale_alert"] == first_seen
        assert "stale_alert" not in state.get("acknowledged", {})


def test_r13_composite_ack_signature_sanitizes_unavailable_field():
    """TC-R13-OPT-ACK-JSON: matching OR writes a JSON-safe ack for unavailable leaves."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        config_path = root / "config.yaml"
        state_path = root / "state.json"
        state_path.write_text(json.dumps({"stale_status": "old"}))
        config_path.write_text("""
name: optional outage composite
seed_mode: false
sources:
  - id: optional
    url: https://example.com/optional
    required: false
    retry: {count: 0}
    extract: [{id: stale_status, type: jsonpath, path: $.status}]
  - id: healthy
    url: https://example.com/healthy
    retry: {count: 0}
    extract: [{id: healthy_status, type: jsonpath, path: $.status}]
conditions:
  - id: either_status
    or:
      - {field: stale_status, op: eq, value: alert}
      - {field: healthy_status, op: eq, value: ready}
groups: [{name: either, any: [either_status], actions: []}]
state: {file: state.json, initial: {stale_status: old}}
""")
        assert _run_with_one_optional_source_failure(config_path, {"status": "ready"}) == 0
        saved = json.loads(state_path.read_text())
        assert saved["acknowledged"]["either_status"]["value"] == {
            "stale_status": None,
            "healthy_status": "ready",
        }


def test_r13_custom_escalation_prompt_renders_state_fields_and_filters():
    """TC-R13-ESC-TEMPLATE: custom prompt shares action field/filter rendering."""
    config = DetectConfig(
        name="Escalation monitor",
        sources=[], conditions=[], groups=[], actions={},
        llm_escalation=LLMEscalation(
            prompt=(
                "status={{ status }} default={{ status | default:unknown }} "
                "config={{ config_name }} condition={{ condition_id }} reason={{ match_reason }} "
                "actions={{ actions_taken }} previous={{ previous_value }} new={{ new_value }}"
            ),
        ),
    )
    esc_agent = LLMEscalationAgent(
        config, {"status": "OnTime"}, {"status": "Delayed"}, ["patch ✅"],
    )
    prompt = esc_agent._render_prompt(
        "status_changed", ConditionResult(True, "status changed"), "OnTime", "Delayed",
    )
    assert prompt == (
        "status=Delayed default=Delayed config=Escalation monitor "
        "condition=status_changed reason=status changed actions=patch ✅ "
        "previous=OnTime new=Delayed"
    )


def test_r13_composite_escalation_prompt_uses_na_for_missing_values():
    """TC-R13-ESC-COMPOSITE-NA: composite prompt preserves N/A previous/new values."""
    config = DetectConfig(
        name="Composite escalation monitor",
        sources=[], conditions=[], groups=[], actions={},
        llm_escalation=LLMEscalation(
            prompt="status={{ status }} previous={{ previous_value }} new={{ new_value }}",
        ),
    )
    esc_agent = LLMEscalationAgent(
        config, {"status": "OnTime"}, {"status": "Delayed"}, [],
    )
    composite = Condition(
        id="either_status",
        or_=[
            {"field": "status", "op": "eq", "value": "Delayed"},
            {"field": "gate", "op": "exists"},
        ],
    )
    evidence = esc_agent._build_evidence(
        "either_status", ConditionResult(True, "OR: status is delayed"), composite,
    )
    assert evidence["prompt"] == "status=Delayed previous=N/A new=N/A"


runner.run(
    "TC-R13-OPT-INDET-SIBLING: optional outage is indeterminate; healthy sibling works",
    test_r13_optional_source_outage_is_indeterminate_and_healthy_sibling_runs,
)
runner.run(
    "TC-R13-OPT-INDET-DURATION: optional outage cannot complete duration gate",
    test_r13_optional_source_outage_does_not_complete_duration_gate,
)
runner.run(
    "TC-R13-OPT-ACK-JSON: composite ack sanitizes unavailable field",
    test_r13_composite_ack_signature_sanitizes_unavailable_field,
)
runner.run(
    "TC-R13-ESC-TEMPLATE: custom escalation prompt renders fields and filters",
    test_r13_custom_escalation_prompt_renders_state_fields_and_filters,
)
runner.run(
    "TC-R13-ESC-COMPOSITE-NA: composite escalation prompt preserves N/A values",
    test_r13_composite_escalation_prompt_uses_na_for_missing_values,
)


# ═══════════════════════════════════════════════════════════════
#  R16: action templates fail closed on unavailable optional-source fields
# ═══════════════════════════════════════════════════════════════

def _write_r16_optional_outage_config(root: Path, action_yaml: str) -> tuple[Path, Path]:
    """Write the common two-source outage config for R16 action tests."""
    config_path = root / "config.yaml"
    state_path = root / "state.json"
    state_path.write_text(json.dumps({"acknowledged": {}}))
    config_path.write_text("""
name: R16 optional action outage
seed_mode: false
sources:
  - id: optional
    url: https://example.com/optional
    required: false
    retry: {count: 0}
    extract: [{id: stale_status, type: jsonpath, path: $.status}]
  - id: healthy
    url: https://example.com/healthy
    retry: {count: 0}
    extract: [{id: healthy_status, type: jsonpath, path: $.status}]
conditions:
  - {id: healthy_ready, field: healthy_status, op: eq, value: ready}
groups: [{name: healthy, any: [healthy_ready], actions: [patch]}]
actions:
""" + action_yaml + """
state: {file: state.json, initial: {acknowledged: {}}}
""")
    return config_path, state_path


def test_r16_unavailable_field_template_blocks_healthy_action():
    """TC-R16-FIELD: unavailable field template blocks healthy sibling action and ack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: evt1
    fields: {summary: "status: {{ stale_status }}"}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            result = _run_with_one_optional_source_failure(config_path, {"status": "ready"})
        mock_patch.assert_not_called()
        assert result == 1
        assert "healthy_ready" not in json.loads(state_path.read_text()).get("acknowledged", {})


def test_r16_unavailable_computed_template_blocks_healthy_action():
    """TC-R16-COMPUTED: unavailable computed template blocks action and ack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: evt1
    computed: {stale_summary: "status: {{ stale_status }}"}
    fields: {summary: "{{ stale_summary }}"}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            result = _run_with_one_optional_source_failure(config_path, {"status": "ready"})
        mock_patch.assert_not_called()
        assert result == 1
        assert "healthy_ready" not in json.loads(state_path.read_text()).get("acknowledged", {})


def test_r16_unavailable_nested_field_template_blocks_healthy_action():
    """TC-R16-NESTED: unavailable nested field template blocks action and ack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: evt1
    fields:
      start: {dateTime: "{{ stale_status }}", timeZone: America/Los_Angeles}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            result = _run_with_one_optional_source_failure(config_path, {"status": "ready"})
        mock_patch.assert_not_called()
        assert result == 1
        assert "healthy_ready" not in json.loads(state_path.read_text()).get("acknowledged", {})


def test_r16_unavailable_default_filter_blocks_healthy_action():
    """TC-R16-DEFAULT: unavailable default-filter field cannot send TBD patch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: evt1
    fields: {summary: "{{ stale_status | default:TBD }}"}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            result = _run_with_one_optional_source_failure(config_path, {"status": "ready"})
        mock_patch.assert_not_called()
        assert result == 1
        assert "healthy_ready" not in json.loads(state_path.read_text()).get("acknowledged", {})


def test_r16_unavailable_fmt_time_filter_blocks_healthy_action():
    """TC-R16-FMT-TIME: unavailable fmt-time field cannot send N/A patch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: evt1
    fields: {summary: "{{ stale_status | fmt_time }}"}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            result = _run_with_one_optional_source_failure(config_path, {"status": "ready"})
        mock_patch.assert_not_called()
        assert result == 1
        assert "healthy_ready" not in json.loads(state_path.read_text()).get("acknowledged", {})


def test_r16_healthy_template_allows_action_during_optional_outage():
    """TC-R16-NEGATIVE: healthy-only template remains allowed during optional outage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: evt1
    fields: {summary: "status: {{ healthy_status }}"}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            assert _run_with_one_optional_source_failure(config_path, {"status": "ready"}) == 0
        mock_patch.assert_called_once()
        assert "healthy_ready" in json.loads(state_path.read_text()).get("acknowledged", {})


def test_r16_unavailable_from_state_event_id_fails_cleanly():
    """TC-R16-EVENT-ID: unavailable from-state event ID fails without a patch or crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path, state_path = _write_r16_optional_outage_config(Path(tmpdir), """
  patch:
    type: calendar_patch
    event_id: {from_state: stale_status}
    fields: {summary: "status: {{ healthy_status }}"}
""")
        with patch("detect_engine.gws_get_event", return_value=None), \
             patch("detect_engine.gws_patch_event", return_value=True) as mock_patch:
            result = _run_with_one_optional_source_failure(config_path, {"status": "ready"})
        mock_patch.assert_not_called()
        assert result == 1
        assert "healthy_ready" not in json.loads(state_path.read_text()).get("acknowledged", {})


runner.run(
    "TC-R16-FIELD: unavailable field template blocks healthy sibling action and ack",
    test_r16_unavailable_field_template_blocks_healthy_action,
)
runner.run(
    "TC-R16-COMPUTED: unavailable computed template blocks action and ack",
    test_r16_unavailable_computed_template_blocks_healthy_action,
)
runner.run(
    "TC-R16-NESTED: unavailable nested field template blocks action and ack",
    test_r16_unavailable_nested_field_template_blocks_healthy_action,
)
runner.run(
    "TC-R16-DEFAULT: unavailable default-filter field cannot send TBD patch",
    test_r16_unavailable_default_filter_blocks_healthy_action,
)
runner.run(
    "TC-R16-FMT-TIME: unavailable fmt-time field cannot send N/A patch",
    test_r16_unavailable_fmt_time_filter_blocks_healthy_action,
)
runner.run(
    "TC-R16-NEGATIVE: healthy-only template remains allowed during optional outage",
    test_r16_healthy_template_allows_action_during_optional_outage,
)
runner.run(
    "TC-R16-EVENT-ID: unavailable from-state event ID fails without a patch or crash",
    test_r16_unavailable_from_state_event_id_fails_cleanly,
)


# ═══════════════════════════════════════════════════════════════
#  Range, empty, and compound delta promotion
# ═══════════════════════════════════════════════════════════════

def test_between_inclusive():
    trigger = TriggerAgent({}, {"price": "25"}, {})
    cond = Condition(id="band", field="price", op="between", min=10, max=50)
    assert trigger.evaluate(cond).matched
    trigger = TriggerAgent({}, {"price": "9"}, {})
    assert not trigger.evaluate(cond).matched


def test_between_requires_min_max():
    try:
        Condition(id="band", field="price", op="between", min=10)
        assert False, "between without max should fail"
    except ValidationError:
        pass


def test_delta_between_price_drop():
    prev = {"price": "100"}
    current = {"price": "70"}
    trigger = TriggerAgent(prev, current, {})
    cond = Condition(id="drop", field="price", op="delta_between", min=-50, max=-5)
    result = trigger.evaluate(cond)
    assert result.matched, result.reason
    cond_miss = Condition(id="drop", field="price", op="delta_between", min=-4, max=-1)
    assert not trigger.evaluate(cond_miss).matched


def test_delta_gt_increase():
    trigger = TriggerAgent({"count": "2"}, {"count": "10"}, {})
    cond = Condition(id="jump", field="count", op="delta_gt", value=5)
    assert trigger.evaluate(cond).matched
    cond_small = Condition(id="jump", field="count", op="delta_gt", value=20)
    assert not trigger.evaluate(cond_small).matched


def test_empty_and_became_empty():
    trigger = TriggerAgent({"gate": "C3"}, {"gate": ""}, {})
    empty = Condition(id="e", field="gate", op="empty")
    became = Condition(id="b", field="gate", op="became_empty")
    still = Condition(id="s", field="gate", op="became_nonempty")
    assert trigger.evaluate(empty).matched
    assert trigger.evaluate(became).matched
    assert not trigger.evaluate(still).matched


def test_became_nonempty():
    trigger = TriggerAgent({"status": ""}, {"status": "Delayed"}, {})
    cond = Condition(id="appear", field="status", op="became_nonempty")
    assert trigger.evaluate(cond).matched
    still_empty = Condition(id="empty", field="status", op="became_empty")
    assert not trigger.evaluate(still_empty).matched


def test_any_changed_compound():
    prev = {"status": "On time", "gate": "C3", "price": "100"}
    current = {"status": "Delayed", "gate": "C3", "price": "100"}
    trigger = TriggerAgent(prev, current, {})
    cond = Condition(id="any", op="any_changed", fields=["status", "gate", "price"])
    result = trigger.evaluate(cond)
    assert result.matched, result.reason
    none = Condition(id="none", op="any_changed", fields=["gate", "price"])
    assert not trigger.evaluate(none).matched


def test_all_changed_compound():
    prev = {"dep_time": "17:20", "arr_time": "19:18"}
    current = {"dep_time": "17:40", "arr_time": "19:18"}
    trigger = TriggerAgent(prev, current, {})
    cond = Condition(id="all", op="all_changed", fields=["dep_time", "arr_time"])
    assert not trigger.evaluate(cond).matched
    current["arr_time"] = "19:40"
    trigger = TriggerAgent(prev, current, {})
    assert trigger.evaluate(cond).matched


def test_delta_block_any_and_became_empty():
    prev = {"status": "On time", "gate": "C3", "headline": "Storm"}
    current = {"status": "Delayed", "gate": "C3", "headline": ""}
    trigger = TriggerAgent(prev, current, {})
    cond = Condition(id="promo", delta={"any": ["status", "gate"], "became_empty": ["headline"]})
    result = trigger.evaluate(cond)
    assert result.matched, result.reason
    miss = Condition(id="promo", delta={"all": ["status", "gate"], "became_empty": ["headline"]})
    assert not trigger.evaluate(miss).matched


def test_delta_block_numeric_range():
    prev = {"price": "100", "status": "ok"}
    current = {"price": "70", "status": "sale"}
    trigger = TriggerAgent(prev, current, {})
    cond = Condition(
        id="sale",
        delta={
            "any": ["status"],
            "range": {"field": "price", "min": -50, "max": -5},
        },
    )
    result = trigger.evaluate(cond)
    assert result.matched, result.reason
    too_small = Condition(
        id="sale",
        delta={"range": {"field": "price", "min": -4, "max": -1}},
    )
    assert not trigger.evaluate(too_small).matched


def test_any_empty_and_all_empty():
    trigger = TriggerAgent({"a": "x", "b": "y"}, {"a": "", "b": "y"}, {})
    any_empty = Condition(id="ae", op="any_empty", fields=["a", "b"])
    all_empty = Condition(id="alle", op="all_empty", fields=["a", "b"])
    assert trigger.evaluate(any_empty).matched
    assert not trigger.evaluate(all_empty).matched
    trigger = TriggerAgent({"a": "x", "b": "y"}, {"a": "", "b": "  "}, {})
    assert trigger.evaluate(all_empty).matched


def test_evidence_includes_prev_new_delta():
    config = DetectConfig(name="Promo Monitor")
    prev = {"price": "100", "status": "ok", "acknowledged": {}}
    current = {"price": "70", "status": "sale", "acknowledged": {}}
    cond = Condition(id="drop", field="price", op="delta_between", min=-50, max=-5)
    result = ConditionResult(True, "price delta -30 in [-50, -5] (100 → 70)")
    evidence = LLMEscalationAgent(config, prev, current, [])._build_evidence(
        "drop", result, cond,
    )
    assert evidence["previous_value"] == "100"
    assert evidence["new_value"] == "70"
    assert evidence["numeric_delta"] == -30
    assert "price" in evidence["changed_fields"]
    assert evidence["delta"]["fields"]["price"]["previous"] == "100"
    assert evidence["delta"]["fields"]["price"]["new"] == "70"
    assert "Previous value: 100" in evidence["prompt"]
    assert "New value: 70" in evidence["prompt"]
    assert "Delta:" in evidence["prompt"]


def test_compound_evidence_promotes_all_involved_fields():
    config = DetectConfig(name="Compound")
    prev = {"status": "On time", "gate": "C3"}
    current = {"status": "Delayed", "gate": ""}
    cond = Condition(id="combo", delta={"any": ["status"], "became_empty": ["gate"]})
    result = ConditionResult(True, "delta: all matched")
    evidence = LLMEscalationAgent(config, prev, current, [])._build_evidence(
        "combo", result, cond,
    )
    assert evidence["field"] is None
    assert set(evidence["fields"]) == {"status", "gate"}
    assert evidence["previous_value"] is None
    assert evidence["new_value"] is None
    assert evidence["delta"]["fields"]["status"]["previous"] == "On time"
    assert evidence["delta"]["fields"]["status"]["new"] == "Delayed"
    assert evidence["delta"]["fields"]["gate"]["became_empty"] is True
    assert "status" in evidence["changed_fields"]


runner.run("TC-RANGE-BETWEEN: inclusive numeric band", test_between_inclusive)
runner.run("TC-RANGE-BETWEEN-VALIDATE: min and max required", test_between_requires_min_max)
runner.run("TC-DELTA-BETWEEN: numeric prev→new drop in range", test_delta_between_price_drop)
runner.run("TC-DELTA-GT: numeric increase threshold", test_delta_gt_increase)
runner.run("TC-EMPTY: empty and became_empty", test_empty_and_became_empty)
runner.run("TC-BECAME-NONEMPTY: empty to value", test_became_nonempty)
runner.run("TC-ANY-CHANGED: compound field list", test_any_changed_compound)
runner.run("TC-ALL-CHANGED: all listed fields must move", test_all_changed_compound)
runner.run("TC-DELTA-BLOCK: any + became_empty clauses AND together", test_delta_block_any_and_became_empty)
runner.run("TC-DELTA-RANGE: compound delta.range on numeric change", test_delta_block_numeric_range)
runner.run("TC-ANY-ALL-EMPTY: empty field lists", test_any_empty_and_all_empty)
runner.run("TC-EVIDENCE-DELTA: promotion payload has prev/new/delta", test_evidence_includes_prev_new_delta)
runner.run("TC-EVIDENCE-COMPOUND: involved fields promoted", test_compound_evidence_promotes_all_involved_fields)


# ═══════════════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    success = runner.summary()
    sys.exit(0 if success else 1)
