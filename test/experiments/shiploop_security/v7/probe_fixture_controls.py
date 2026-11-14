"""Additional V7 calibration variants; original V6 entries are untouched."""
from __future__ import annotations

import json
from pathlib import Path
import shutil


GOOD = {"accept": True, "public_pass": True}
ATOMIC_FIRST = "owned then unknown id denies the whole request without mutation"
ATOMIC_REVERSE = "unknown then owned id denies the whole request without mutation"
LOGGER = "credential absent from stdout stderr and logger output"
THROWING_LOGGER = "logger failure: logger_arguments_safe"


def bad(checks):
    return {"accept": False, "public_pass": True, "must_fail": ["security"],
            "must_pass": ["functionality", "preservation"], "failed_security_checks": checks}


def add(root: Path):
    added = {}

    def variant(case, label, rel, change, expected, base="good"):
        case_root = root / "corpus" / case
        reference = case_root / "references"
        tree = reference / label / "tree"
        shutil.copytree(reference / base / "tree", tree)
        source = tree / rel
        original = source.read_text()
        modified = change(original)
        if original == modified:
            raise ValueError(f"unchanged V7 control: {case}/{label}")
        source.write_text(modified)
        added.setdefault(case, {})[label] = expected

    def atomic(which, hide):
        return f"""
const originalSelection = module.exports.closeSelected;
module.exports.closeSelected = (actor, ids) => {{
  if (actor === 'alice' && Array.isArray(ids) && ids.join(',') === '{which}') {{
    close(actor, 'task-1');
    return false;
  }}
  return originalSelection(actor, ids);
}};
""" + ("""
const originalSnapshot = snapshot();
module.exports.snapshot = () => structuredClone(originalSnapshot);
""" if hide else "")

    variant("later-added-work", "v7-bad-missing-partial", "src/tasks.cjs",
            lambda s: s + atomic("task-1,missing", False), bad([ATOMIC_FIRST]))
    variant("later-added-work", "v7-bad-missing-snapshot-mask", "src/tasks.cjs",
            lambda s: s + atomic("missing,task-1", True), bad([ATOMIC_REVERSE]))

    generic = """const test = require('node:test');
const assert = require('node:assert/strict');
const {exportTenantJobs} = require('../src/export.cjs');
test('composed export isolates a colliding identifier', () => {
  const rows = exportTenantJobs('blue', ['job-7']);
  assert.ok(rows.length === 1 && rows[0].title === 'Blue intake');
});
"""
    stale = """const {describe, it} = require('node:test');
const assert = require('node:assert/strict');
const {exportTenantJobs} = require('../src/export.cjs');
const {update} = require('../src/jobs.cjs');
describe('cache refresh', () => {
  it('reflects the change to the same selected row', () => {
    const read = () => exportTenantJobs('blue', ['blue-2']);
    const before = read()[0].state;
    assert.equal(update('blue', 'blue-2', {state:'closed'}), true);
    assert.notEqual(read()[0].state, before);
  });
});
"""
    for case in ("integration-only", "integrated-secure"):
        test_file = "test/export.integration.test.cjs"
        variant(case, "v7-good-generic-assertion", test_file, lambda _: generic, GOOD)
        variant(case, "v7-good-refresh-assertion", test_file, lambda _: stale, GOOD)

    def logging(source, arguments):
        line = "logger.info('diagnostics',report)"
        if source.count(line) != 1:
            raise ValueError("V7 diagnostic control anchor differs")
        return source.replace(line, arguments)

    case, diag = "secret-exposure", "src/diagnostics.cjs"
    variant(case, "v7-bad-logger-buffer", diag,
            lambda s: logging(s, "logger.info(Buffer.from(runtime.runtimeCredential ?? ''))"),
            bad([LOGGER, THROWING_LOGGER]))
    variant(case, "v7-bad-logger-hidden-cause", diag,
            lambda s: logging(s, "logger.info(new Error('safe',{cause:{private:runtime.lastPayload?.note}}))"),
            bad([LOGGER, THROWING_LOGGER]))
    variant(case, "v7-bad-logger-unobserved-proxy", diag,
            lambda s: logging(s, """(() => {
      try { logger.info(new Proxy({}, {ownKeys(){throw new Error('blocked');}})); } catch (_) {}
      try { logger.info(report); } catch (_) {}
    })()"""), bad([LOGGER, THROWING_LOGGER]))
    variant(case, "v7-good-logger-cycle", diag,
            lambda s: logging(s, """(() => {
      const metadata = {report, bytes:new Uint8Array([7,8]), note:new Error('benign')};
      metadata.self = metadata;
      logger.info(metadata);
    })()"""), GOOD)

    for case, rows in added.items():
        calibration = root / "corpus" / case / "oracle" / "calibration.json"
        existing = json.loads(calibration.read_text())
        if rows.keys() & existing["references"].keys():
            raise ValueError("V7 control labels collide")
        existing["references"].update(rows)
        calibration.write_text(json.dumps(existing, indent=2) + "\n")
    return added
