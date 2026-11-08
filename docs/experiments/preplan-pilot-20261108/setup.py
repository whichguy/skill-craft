"""Build deterministic local planning fixtures; never starts a model."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "93dd53b73e1931c5847ad75d9bc19205c40fb441"

ADAPTER = '''"""Installed local adapter 2.3. Public interface: apply(db_path, rows).

The existing single-row client is covered; the batch failure contract has not
been characterized by this application. This module is available for inspection.
"""
import sqlite3

VERSION = "2.3"

def apply(db_path, rows):
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS inventory (sku TEXT PRIMARY KEY, quantity INTEGER)")
        for row in rows:
            if not isinstance(row["quantity"], int) or row["quantity"] < 0:
                raise ValueError("invalid quantity")
            db.execute("INSERT OR REPLACE INTO inventory VALUES (?, ?)", (row["sku"], row["quantity"]))
            db.commit()
    return {"accepted": len(rows)}
'''
BASELINE = '''import unittest, tempfile, sqlite3
from pathlib import Path
from src import adapter

class Baseline(unittest.TestCase):
    def test_single_row_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = str(Path(tmp) / "db.sqlite")
            self.assertEqual(adapter.apply(p, [{"sku":"old","quantity":2}]), {"accepted":1})
            with sqlite3.connect(p) as db:
                self.assertEqual(db.execute("SELECT * FROM inventory").fetchall(), [("old",2)])

if __name__ == "__main__": unittest.main()
'''
SEARCH = '''"""Application SQLite binding. Search implementation is not written yet."""
import sqlite3

def connect(path=":memory:"):
    return sqlite3.connect(path)
'''
SEARCH_BASELINE = '''import unittest
from src import database

class Baseline(unittest.TestCase):
    def test_application_connection(self):
        with database.connect() as db:
            self.assertEqual(db.execute("select 1").fetchone(), (1,))

if __name__ == "__main__": unittest.main()
'''
UNAVAILABLE = '''"""Offline surrogate for the external inventory service transport.

No external endpoint or credential is configured in this fixture. Its failure
deliberately conveys no information about the service's batch contract.
"""
def apply(target, rows):
    raise ConnectionError("approved sandbox not provisioned; no request sent")
'''
OFFLINE_TEST = '''import unittest
from src import client

class Baseline(unittest.TestCase):
    def test_unconfigured_transport_is_explicit(self):
        with self.assertRaises(ConnectionError): client.apply("sandbox", [])

if __name__ == "__main__": unittest.main()
'''

REQUESTS = {
    "atomic": "Extend this local Python inventory tool with a JSON batch-import command. Import must be all-or-nothing: any invalid record, adapter error or interrupted import leaves the previously visible inventory unchanged; successful publication exposes the complete new batch and preserves unrelated existing SKUs. Repeating a successful import is idempotent. Keep the installed adapter for applying rows unless evidence shows an alternative is needed. The adapter's batch behavior has not been characterized. No concurrent writers are in scope; readers can reopen the database between commands. Use only Python's standard library. Temporary local experiments on disposable databases are authorized. Do not mutate the retained seed inventory. Add automated CLI, invalid-middle-record, interrupted-publication and recovery checks as implementation work. Existing tests must remain passing.",
    "evidence": "Extend this local Python inventory tool with a JSON batch-import command. Import must be all-or-nothing: any invalid record, adapter error or interrupted import leaves the previously visible inventory unchanged; successful publication exposes the complete new batch and preserves unrelated existing SKUs. Repeating a successful import is idempotent. Keep the installed adapter for applying rows unless evidence shows an alternative is needed. Discovery already characterized this exact adapter and configuration; its commands, source hash and observations are in docs/evidence/adapter.json. No concurrent writers are in scope; readers can reopen the database between commands. Use only Python's standard library. Temporary local experiments on disposable databases are authorized. Do not mutate the retained seed inventory. Add automated CLI, invalid-middle-record, interrupted-publication and recovery checks as implementation work. Existing tests must remain passing.",
    "unicode": "Add offline substring search to this Python catalog using the application's src/database.py connection. Search must be accent insensitive and Unicode casefold insensitive, without changing displayed titles: cafe finds Café Racer, STRASSE finds Die Straße, and interior query afe finds Café Racer. Query xyz finds no records. An empty query returns no matches. Search order is stable by ID and duplicate titles preserve distinct IDs. The fixed initial catalog fits in memory (at most 5000 titles), search needs no external service, no fuzzy ranking and no new dependency. A previous design note suggests SQLite FTS5 trigram or LIKE if they meet these semantics on this binding; that is a proposal, not an accepted requirement. Verify the chosen mechanism at its real boundary when needed, and retain implementation and consumer checks as future work. Temporary local experiments on disposable data are authorized. Existing tests must remain passing.",
    "unavailable": "Add a JSON batch-import command for an external inventory service. Publication must be all-or-nothing, preserve unrelated existing SKUs and be idempotent on retry; invalid rows are reported clearly. Its sandbox has not been provisioned. The repository's offline transport deliberately fails before sending any request and cannot reveal the service's atomicity contract. No remote endpoint, credential, deployment or provisioning is authorized for this task. Build independent local input validation and preview work while keeping service-dependent integration conditional on a named readiness prerequisite. The future service owner must supply an approved sandbox and verify success, partial failure, interrupted publication and recovery. Do not substitute a local simulation for live service evidence. Existing tests must remain passing. Temporary local experiments are authorized only if they can settle a relevant local question.",
}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main():
    cases = {}
    calibration = {}
    for name, request in REQUESTS.items():
        p = HERE / "fixtures" / name
        p.mkdir(parents=True, exist_ok=True)
        write(p / "src/__init__.py", "")
        write(p / "tests/__init__.py", "")
        if name in ("atomic", "evidence"):
            write(p / "src/adapter.py", ADAPTER)
            write(p / "tests/test_baseline.py", BASELINE)
            write(p / "data/seed.json", '[{"sku":"old","quantity":2}]\n')
        elif name == "unicode":
            write(p / "src/database.py", SEARCH)
            write(p / "tests/test_baseline.py", SEARCH_BASELINE)
            write(p / "data/catalog.json", '[{"id":1,"title":"Café Racer"},{"id":2,"title":"Die Straße"},{"id":3,"title":"Café Racer"}]\n')
        else:
            write(p / "src/client.py", UNAVAILABLE)
            write(p / "tests/test_baseline.py", OFFLINE_TEST)
        baseline = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=p, text=True, capture_output=True, check=True)
        calibration[name] = {"baseline": baseline.stderr, "command": "python3 -B -m unittest discover -s tests -v"}
        write(p / "README.md", "# Inventory tool\n\n" + request + "\n\nRun the existing suite with `python3 -B -m unittest discover -s tests -v`. All new product behavior is unimplemented.\n")
        write(p / "docs/shiploop/spec.md", "# Product specification\n\n## Requirements\n\nR-1: " + request + "\n\n## Non-functional requirements\n\nR-2: Keep data loss and false success visible; preserve the existing baseline and require repeatable behavioral tests for the new command. Use only the stated local standard-library runtime.\n\n## Retired\n\nNone.\n")
        write(p / "docs/shiploop/environment.md", "# Environment\n\n## Runtime and access\n\nLocal Python 3 standard library; no network, account, dependency download or deployment is needed or authorized. The supplied source and fixtures are the inspected application.\n\n## Harnesses and suites\n\nPython unittest is available and the unchanged baseline passed before this seed was frozen. It covers only the existing behavior, not the requested feature.\n\n## Commands\n\nExisting suite, all tests under tests/:\n```sh\npython3 -B -m unittest discover -s tests -v\n```\n\n## ID convention\n\nThe strategy must choose legal unittest method names and preserve traceability in titles or output.\n")
        write(p / "docs/shiploop/architecture.md", "# Architecture\n\n## Stack\n\nPython standard library; sqlite3 for local persistence where applicable.\n\n## Structure\n\nsrc/ holds current application adapters; tests/ holds baseline tests; data/ holds read-only seed inputs. New command and publication/search responsibility placement is undecided.\n\n## Conventions\n\nSmall explicit functions, unittest, disposable fixtures.\n\n## Interfaces and boundaries\n\n" + ("The external service transport is unavailable and reveals no contract.\n" if name == "unavailable" else "Public adapter/binding interfaces are in src/. Inspect source or use an authorized disposable local probe when a planning decision requires it.\n") + "\n## Real-boundary checks\n\nThe requested command does not exist; its behavioral and recovery acceptance remains due after implementation.\n\n## Decisions\n\nAD-1: Preserve the supplied standard-library stack and existing baseline; accepted. New feature architecture remains provisional.\n\n## Superseded\n\nNone.\n")
        write(p / "docs/discovery.md", "# Supplied discovery\n\nThis is a constructed planning fixture. Source, tests and data are present; the baseline suite passed. Only existing behavior was tested. No new feature, atomicity or search acceptance is implied. " + ("Current representative adapter observations are supplied in docs/evidence/adapter.json; reuse them where sufficient.\n" if name == "evidence" else "No earlier decision experiment is supplied.\n"))
        records = {s: {"summary": "Synthetic accepted seed: see docs/discovery.md, docs/shiploop/spec.md and docs/shiploop/architecture.md. " + ("Current exact-adapter observations in docs/evidence/adapter.json." if name == "evidence" else "No feature acceptance has run."), "evidence_refs": ["docs/discovery.md", "docs/shiploop/spec.md", "docs/shiploop/environment.md", "docs/shiploop/architecture.md"]} for s in ("discovery", "research", "spec")}
        records["spec"]["primary"] = ["R-1", "R-2"]
        cases[name] = {"fixture": name, "prompt": request, "work_item": {"id":"placeholder", "title":"Unused placeholder: live plan defines work items"}, "expect_paths": [], "checks": ["python3 -B -m unittest discover -s tests -v"], "seed_records": records}
    # Calibrate the supplied evidence through the same adapter, using a clean temporary database.
    probe = '''import json, sqlite3, tempfile\nfrom pathlib import Path\nfrom src import adapter\nwith tempfile.TemporaryDirectory() as tmp:\n p=str(Path(tmp)/"probe.sqlite")\n adapter.apply(p,[{"sku":"old","quantity":2}])\n success=adapter.apply(p,[{"sku":"a","quantity":3},{"sku":"b","quantity":4}])\n with sqlite3.connect(p) as db: before=db.execute("SELECT * FROM inventory ORDER BY sku").fetchall()\n try: adapter.apply(p,[{"sku":"c","quantity":5},{"sku":"bad","quantity":-1}])\n except ValueError as e: error=str(e)\n with sqlite3.connect(p) as db: after=db.execute("SELECT * FROM inventory ORDER BY sku").fetchall()\n print(json.dumps({"success":success,"before":before,"failure":error,"after":after,"partial_write_visible":before!=after}))\n'''
    observed = subprocess.run([sys.executable, "-B", "-c", probe], cwd=HERE / "fixtures/evidence", capture_output=True, text=True, check=True)
    evidence = {"source": "src/adapter.py", "sha256": hashlib.sha256(ADAPTER.encode()).hexdigest(), "adapter_version": "2.3", "configuration": "default connection, no concurrent writers, new local disposable database", "command_argv": ["python3", "-B", "-c", probe], "stdout": json.loads(observed.stdout), "conclusion": "This adapter commits each applied row; a later invalid record leaves prior writes visible to a fresh connection. Applying directly to the visible destination cannot satisfy all-or-nothing failure. This says nothing about an unimplemented staging/publication/recovery design."}
    assert evidence["stdout"]["partial_write_visible"] is True
    write(HERE / "fixtures/evidence/docs/evidence/adapter.json", json.dumps(evidence, indent=2) + "\n")
    calibration["atomicity"] = evidence
    search_probe = '''import json\nfrom src import database\nwith database.connect() as db:\n db.execute("CREATE VIRTUAL TABLE docs USING fts5(title, tokenize='trigram')")\n db.executemany("INSERT INTO docs(title) VALUES (?)",[("Café Racer",),("Die Straße",)])\n print(json.dumps({q:db.execute("SELECT rowid FROM docs WHERE title LIKE ?",("%"+q+"%",)).fetchall() for q in ["cafe","STRASSE","afe","xyz"]}))\n'''
    result = subprocess.run([sys.executable, "-B", "-c", search_probe], cwd=HERE / "fixtures/unicode", capture_output=True, text=True)
    calibration["native_search"] = {"argv": ["python3", "-B", "-c", search_probe], "exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    write(HERE / "cases.json", json.dumps(cases, indent=2) + "\n")
    write(HERE / "fixture-calibration.json", json.dumps(calibration, indent=2) + "\n")
    anchor = "2. Plan backward from desired outcomes to their producers (Dependency-planning guidance); return `work_items`"
    addition = """Before defining work items, assess the accepted spec and reopened sources for consequential uncertainty:
   which unknown could change the approach, dependencies, scope or readiness of this plan? Use sufficient current
   evidence first; zero experiments is valid. When a small authorized representative experiment can settle such
   a decision more usefully than further reading or conditional planning, identify and run it now, before committing
   dependent work to the breakdown. State the decision, alternatives, representative target and observation that
   would distinguish them before running. Keep temporary code/data in RUN/scratch; retain exact commands, outputs,
   source/setup identity and their decision consequences in RUN/notes/planning-experiments.md. Clean up owned
   resources; a probe grants no new authority, product integration, baseline mutation or production access.
   A failed apparatus or inconclusive result leaves the question open; gate its dependent work and keep independent
   planning eligible. Carry findings and unresolved decisions into `assumptions` and `evidence_refs`. Reuse research's
   shared investigation allowance and record consumption/remaining allowance in that note for Plan Improve; a new
   stage or review grants no fresh allowance. Plan Improve still reassesses the resulting plan, including assumptions
   introduced by its breakdown, using prior evidence where sufficient. Use the current stage; add no Until Loop.
2. Plan backward from desired outcomes to their producers (Dependency-planning guidance); return `work_items`"""
    overlay = {"about":"Early consequential experiments after spec/test strategy and source reopening, before work_items; Plan Improve is byte-identical to baseline.", "baseline": BASE, "edits":[{"module":"shiploop_prompts.py", "constant":"DUTIES", "key":"plan", "old":anchor,"new":addition}]}
    write(HERE / "candidate-overlay.json", json.dumps(overlay, indent=2) + "\n")
    print(json.dumps({"cases":list(cases),"partial_write_visible":True,"native_search":calibration["native_search"]},indent=2))

if __name__ == "__main__":
    main()
