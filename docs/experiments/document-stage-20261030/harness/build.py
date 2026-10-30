"""Build the document-stage side experiment's scenarios from the node-base fixture.

Each scenario is a post-implement, post-test state: a Git worktree whose base commit holds the product and the
knowledge home (docs/shiploop), with the step's code and test changes left uncommitted, plus a RUN folder holding the
earlier stages' results.  Planted documentation defects are listed in scenarios.json for the grader.

    python3 -I build.py <out dir>
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]  # the repository root, from docs/experiments/<round>/harness/
FIXTURE = ROOT / "test/shiploop_e2e/fixtures/node-base"

KNOWLEDGE_ARCH = """\
# Architecture

## Structure
- `src/<concept>.js`: one CommonJS module per concept, exporting named functions or classes.
- `test/<concept>.test.js`: node:test tests for that module.

## Conventions
- Argument errors: TypeError for a wrong type or shape, RangeError for an out-of-range value; the message names the argument.
- One-line JSDoc on each exported function.

## Decisions
- AD-1: No runtime dependencies; Node >= 20 built-ins only (node:test, node:assert). Owner: maintainer. Revalidate when a dependency is proposed.

## Superseded
"""

KNOWLEDGE_ENV = """\
# Environment

## Commands
- `npm test`: runs `node --test`, every test/*.test.js; exit 0 is a pass.

## Harnesses and suites
- node:test through `node --test`; no other harness.
"""


def state(obj):
    return "# ShipLoop navigator result\n\n```shiploop-state\n" + json.dumps(obj, indent=2) + "\n```\n"


SCENARIOS = {
    "s1-basket": {
        "title": "Add Basket in src/basket.js",
        "context": "limit is a positive integer (TypeError otherwise); add returns the count; RangeError when full.",
        "request": ("In this Node.js project, add a class Basket in a new module src/basket.js and export it. new "
                    "Basket({limit}) holds at most limit items; limit must be a positive integer, otherwise the "
                    "constructor throws a TypeError. add(item) appends the item and returns the new count, and throws "
                    "a RangeError when the basket is full. Cover it with node:test tests; npm test must pass."),
        "spec": """\
# Living spec

## R-1 Basket capacity
`new Basket({limit})` creates a basket holding at most `limit` items; `limit` must be a positive integer, otherwise the constructor throws a TypeError.

## R-2 Adding items
`add(item)` appends the item and returns the new count; it throws a RangeError when the basket is full.

## R-3 Tests
`npm test` passes.
""",
        "base_edits": {},
        "work": {
            "src/basket.js": """\
'use strict';

/** A basket of items. */
class Basket {
  /** Create a basket. */
  constructor({ limit } = {}) {
    // check the limit
    if (!Number.isInteger(limit) || limit < 1) {
      throw new TypeError('limit must be a positive integer');
    }
    this.limit = limit;
    this.items = [];
  }

  /** Add an item. */
  add(item) {
    // if the basket is full throw
    if (this.items.length >= this.limit) {
      throw new RangeError(`basket is full (limit ${this.limit})`);
    }
    this.items.push(item);
    return this.items.length;
  }
}

module.exports = { Basket };
""",
            "test/basket.test.js": """\
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { Basket } = require('../src/basket');

test('TC-1 a basket with a positive integer limit starts empty', () => {
  const basket = new Basket({ limit: 2 });
  assert.equal(basket.items.length, 0);
});

test('TC-2 a limit that is not a positive integer throws a TypeError', () => {
  for (const limit of [0, -1, 1.5, '2', undefined, NaN]) {
    assert.throws(() => new Basket({ limit }), TypeError);
  }
  assert.throws(() => new Basket(), TypeError);
});

test('TC-3 add appends the item and returns the new count', () => {
  const basket = new Basket({ limit: 2 });
  assert.equal(basket.add('a'), 1);
  assert.equal(basket.add(undefined), 2);
});

test('TC-4 add throws a RangeError when the basket is full and keeps the count', () => {
  const basket = new Basket({ limit: 1 });
  basket.add('a');
  assert.throws(() => basket.add('b'), RangeError);
  assert.equal(basket.items.length, 1);
});
""",
        },
        "criteria": [
            {"id": "C1", "text": "new Basket({limit}) throws a TypeError for a limit that is not a positive integer (R-1). Confirm by: node --test test/basket.test.js runs TC-2; pass when it passes", "confirm": "executed"},
            {"id": "C2", "text": "add returns the new count and throws a RangeError when full (R-2). Confirm by: node --test test/basket.test.js runs TC-3 and TC-4; pass when both pass", "confirm": "executed"},
            {"id": "C3", "text": "src/basket.js carries a contract docstring on Basket, its constructor and add (Code craft 2-3). Confirm by: grep -c '/\\*\\*' src/basket.js; pass when at least 3", "confirm": "searched"},
        ],
        "paths": ["src/basket.js", "test/basket.test.js", "README.md"],
        "implement_summary": ("Added src/basket.js with class Basket. S1 first kept a separate `this.count` beside "
                              "`this.items`; a probe (RUN/scratch/probe-count.js) that pushed into basket.items "
                              "directly showed the count drifting from the real contents, so the count was removed "
                              "and items.length is the one source. The constructor validates before any assignment. "
                              "R-1 asks for a TypeError even for 0 and -1, which the architecture convention would "
                              "make RangeErrors; the request's wording was followed."),
        "not_covered": ["basket.items is a public array: a caller can push into it directly and exceed limit"],
        "test_cases": ["TC-1", "TC-2", "TC-3", "TC-4"],
        "commands": [{"kind": "focused", "command": "node --test test/basket.test.js", "ids": ["TC-1", "TC-2", "TC-3", "TC-4"]},
                     {"kind": "full", "command": "npm test", "ids": []}],
        "test_summary": ("All four cases pass. `node --test test/basket.test.js` runs one file; "
                         "`node --test --test-name-pattern=TC-2` selects a case by name (both worked)."),
        "planted": {
            "file_purpose_line": "src/basket.js has no purpose line",
            "vacuous_docstrings": ["/** A basket of items. */", "/** Create a basket. */", "/** Add an item. */"],
            "restating_comments": ["// check the limit", "// if the basket is full throw"],
            "tombstone": "a separate count drifted from items; items.length is the one source",
            "caveat": "items is public and mutable: pushing into it bypasses limit",
            "readme_stale": "README's module list lacks src/basket.js",
            "architecture": "R-1 departs from the RangeError convention (TypeError for 0 and -1): an AD-n",
            "environment_durable": ["node --test test/basket.test.js", "--test-name-pattern"],
            "environment_transient": ["probe-count.js", "RUN/scratch"],
        },
    },
    "s2-rename": {
        "title": "Rename getUser to findUser across the project",
        "context": "Definition, export, server use and tests; no behaviour change; no getUser left anywhere.",
        "request": ("In this Node.js project, rename getUser to findUser everywhere: its definition and export in "
                    "src/users.js, its use in src/server.js, and the tests. Behaviour must not change and no getUser "
                    "alias may remain. npm test must pass."),
        "spec": """\
# Living spec

## R-1 Rename
The user lookup is exported as `findUser(id)` from src/users.js and used by src/server.js and the tests.

## R-2 No alias
No `getUser` name or alias remains.

## R-3 Behaviour unchanged
`findUser(id)` returns the user with `id`, or null; GET /users/:id answers 200 with the user or 404; `npm test` passes.
""",
        "base_edits": {
            "README.md": """\
# node-base

A small Node.js project with no dependencies.

- `src/strings.js`: text helpers
- `src/paginate.js`: split a list into pages
- `src/users.js`: an in-memory user store; `getUser(id)` returns the user or null, `listUsers()` every user
- `src/server.js`: an HTTP server (`node:http`) that serves the users (see [docs/api.md](docs/api.md))

Run the tests with `npm test`, which runs `node --test`.
""",
            "docs/api.md": """\
# HTTP API

| Route | Answer |
|---|---|
| `GET /users` | 200, every user as a JSON array (`listUsers()`) |
| `GET /users/:id` | 200 with the user found by `getUser(id)`, or 404 `{"error":"not found"}` |

Any other route answers 404 `{"error":"not found"}`.
""",
        },
        "work": "rename",
        "criteria": [
            {"id": "C1", "text": "findUser is defined and exported by src/users.js and used by src/server.js (R-1). Confirm by: npm test; pass when exit 0", "confirm": "executed"},
            {"id": "C2", "text": "no getUser remains in src or test (R-2). Confirm by: ! grep -rn getUser src test; pass when exit 0", "confirm": "searched"},
        ],
        "paths": ["src/users.js", "src/server.js", "test/users.test.js"],
        "implement_summary": ("Renamed getUser to findUser in src/users.js (definition and export) and src/server.js; "
                              "no alias kept. `! grep -rn getUser src test` exits 0."),
        "not_covered": [],
        "test_cases": ["TC-1"],
        "commands": [{"kind": "focused", "command": "node --test test/users.test.js", "ids": ["TC-1"]},
                     {"kind": "full", "command": "npm test", "ids": []}],
        "test_summary": "TC-1 renamed the users test to findUser; all suites pass.",
        "planted": {
            "stale_mentions": ["README.md: getUser(id)", "docs/api.md: getUser(id)"],
            "no_bloat": "a rename needs no new prose: the two stale mentions are the whole doc change",
            "architecture": "no AD warranted",
        },
    },
    "s3-health": {
        "title": "Add GET /health to src/server.js",
        "context": "GET /health answers 200 with {\"ok\":true} as application/json; existing routes unchanged.",
        "request": ("In this Node.js project, add a health route to the HTTP server in src/server.js: GET /health "
                    "answers 200 with the JSON body {\"ok\":true} and a content-type of application/json. The existing "
                    "routes must not change. npm test must pass."),
        "spec": """\
# Living spec

## R-1 Health route
GET /health answers 200 with the JSON body {"ok":true} and content-type application/json.

## R-2 Existing routes unchanged
GET /users and GET /users/:id answer as before; `npm test` passes.
""",
        "base_edits": {},
        "work": "health",
        "criteria": [
            {"id": "C1", "text": "GET /health answers 200, application/json, {\"ok\":true} (R-1). Confirm by: node --test test/server.test.js runs TC-1; pass when it passes", "confirm": "executed"},
            {"id": "C2", "text": "existing routes unchanged (R-2). Confirm by: npm test; pass when exit 0", "confirm": "executed"},
        ],
        "paths": ["src/server.js", "test/server.test.js"],
        "implement_summary": ("Added the GET /health branch before the users routes in createServer. Observed with "
                              "`PORT=4123 npm start` and `curl -si http://127.0.0.1:4123/health`: 200, content-type "
                              "application/json, body {\"ok\":true}. A HEAD /health request answers 404 because only "
                              "GET is routed; POST /health also answers 404, not 405."),
        "not_covered": ["HEAD /health answers 404 (only GET is routed)"],
        "test_cases": ["TC-1"],
        "commands": [{"kind": "focused", "command": "node --test test/server.test.js", "ids": ["TC-1"]},
                     {"kind": "full", "command": "npm test", "ids": []}],
        "test_summary": "TC-1 passes; the existing server test still passes.",
        "planted": {
            "readme_missing": "README does not say how to start the server, its PORT, or its routes (health included)",
            "caveat": "HEAD /health answers 404 (load balancers often probe with HEAD)",
            "stale_docstring": "createServer's docstring says 'for the user store' only",
            "environment_durable": ["npm start", "PORT", "/health"],
        },
    },
}


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def apply_work(kind, tree: Path):
    if kind == "rename":
        for rel in ("src/users.js", "src/server.js", "test/users.test.js"):
            path = tree / rel
            path.write_text(path.read_text().replace("getUser", "findUser"))
        return
    if kind == "health":
        server = tree / "src/server.js"
        text = server.read_text()
        text = text.replace(
            "    if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());\n",
            "    if (req.method === 'GET' && url.pathname === '/health') return send(res, 200, { ok: true });\n"
            "    if (req.method === 'GET' && url.pathname === '/users') return send(res, 200, listUsers());\n")
        server.write_text(text)
        tests = tree / "test/server.test.js"
        tests.write_text(tests.read_text() + """
test('TC-1 GET /health answers 200 with {"ok":true} as application/json', async () => {
  await withServer(async (base) => {
    const res = await fetch(`${base}/health`);
    assert.equal(res.status, 200);
    assert.match(res.headers.get('content-type'), /^application\\/json/);
    assert.deepEqual(await res.json(), { ok: true });
  });
});
""")
        return
    for rel, text in kind.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)


def build(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, sc in SCENARIOS.items():
        root = out / name
        if root.exists():
            shutil.rmtree(root)
        tree, rundir = root / "worktree", root / "run"
        shutil.copytree(FIXTURE, tree)
        for rel, text in sc["base_edits"].items():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_text(text)
        home = tree / "docs/shiploop"
        home.mkdir(parents=True, exist_ok=True)
        (home / "spec.md").write_text(sc["spec"])
        (home / "architecture.md").write_text(KNOWLEDGE_ARCH)
        (home / "environment.md").write_text(KNOWLEDGE_ENV)
        run(["git", "init", "-q", "-b", "main"], tree)
        run(["git", "-c", "user.name=fixture", "-c", "user.email=f@x", "add", "-A"], tree)
        run(["git", "-c", "user.name=fixture", "-c", "user.email=f@x", "commit", "-qm", "base"], tree)
        apply_work(sc["work"], tree)
        for sub in ("results", "notes", "scratch", "inbox"):
            (rundir / sub).mkdir(parents=True, exist_ok=True)
        (rundir / "request.md").write_text("S1 " + sc["request"] + "\n")
        (rundir / "results/step-plan.md").write_text(state({
            "outcome": "done", "summary": "One step.", "criteria": sc["criteria"],
            "steps": [{"id": "S1", "task": sc["title"], "criteria": [c["id"] for c in sc["criteria"]],
                       "proof": sc["commands"][0]["command"]}],
            "paths": sc["paths"], "test_commands": sc["commands"]}))
        (rundir / "results/test-spec.md").write_text(state({
            "outcome": "done", "summary": "Cases " + ", ".join(sc["test_cases"]) + ".",
            "test_cases": sc["test_cases"]}))
        (rundir / "results/implement-S1.md").write_text(state({
            "outcome": "done", "summary": sc["implement_summary"], "not_covered": sc["not_covered"]}))
        (rundir / "results/test-S1.md").write_text(state({
            "outcome": "done", "summary": sc["test_summary"], "commands": sc["commands"]}))
        if name == "s1-basket":
            (rundir / "scratch/probe-count.js").write_text("// implement's probe: push into basket.items directly\n")
        subprocess.run(["npm", "test"], cwd=tree, check=True, capture_output=True)
        changed = subprocess.run(["git", "status", "--porcelain"], cwd=tree, capture_output=True, text=True).stdout
        manifest[name] = {"title": sc["title"], "context": sc["context"], "planted": sc["planted"],
                          "changed": changed.splitlines(), "commands": sc["commands"]}
    (out / "scenarios.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: v["changed"] for k, v in manifest.items()}, indent=1))


if __name__ == "__main__":
    build(Path(sys.argv[1]))
