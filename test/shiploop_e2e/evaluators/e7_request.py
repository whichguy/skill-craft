#!/usr/bin/env python3
"""E7-F by the request: do a sample's tests fail on versions of the fixed implementation that break the request?

    python3 test/shiploop_e2e/evaluators/e7_request.py score <sample>...
    python3 test/shiploop_e2e/evaluators/e7_request.py verify

e7_tests.py scores tests by mutants of the code, which take the code as the truth: a test that agrees with a wrong
implementation kills them all, and a check the code added that the request never asked for counts as a gap. This
evaluator takes the request as the truth instead. Each of ``VARIANTS`` changes one line of E7-F's recorded
implementation (E7-K2 A/6, tree ``RECORDED_TREE``) so that it breaks one sentence of tickets-assign's prompt, and
carries a witness: a script over the HTTP API that passes on the recorded implementation and fails on the variant, the
proof that the variant breaks the request and is not an equivalent change. ``verify`` checks every witness both ways,
that each ``find`` occurs once, and records which variants the case's own hidden check catches.

``score`` copies a sample's worktree (the test stage's tests over the recorded implementation, as the seed laid it),
lays each variant over the copy alone and runs the whole suite (``node --test``, the case's ``npm test``). A variant is
``killed`` when the suite fails twice in a row, so one flaky run (test/service.test.js's ECONNRESET, E7-F D/1) cannot
count as a kill. The same runs with test/ restored to the seed commit say which variants the tests that were there
before the test stage already catch. ``value`` is the killed fraction of all variants; ``added_value`` the killed
fraction of those the earlier tests miss, which is what the test stage contributed. The unmutated suite must pass first,
or nothing is scored. Writes ``<sample>/request-score.json``, never score.json.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

CASE = "tickets-assign"
RECORDED_SOURCE = Path.home() / "e2e-runs/e7-20261030/E7-K2/A/6/slice/.shiploop-runs/seed/worktree"
RECORDED_TREE = "a45625d34ae0554853ca7ba3991a1f774e5e5a8e"
SUITE = ("node", "--test")
SUITE_SECONDS = 60

# The witnesses' shared frame: a fresh ticket ``t`` on a test service, its assignee URL ``u`` and ticket URL ``tid``.
_FRAME = ("const {withService,ticketBody}=require('./test/helpers');const a=require('assert');"
          "withService({},async(api)=>{const t=(await api.post('/tickets',ticketBody())).body;"
          "const tid='/tickets/'+t.id;const u=tid+'/assignee';"
          "const move=async(to)=>a.strictEqual((await api.post(tid+'/transition',{to})).status,200);"
          "const sent=async()=>Object.values((await api.get('/admin/outbox')).body).flat()"
          ".filter((e)=>e.type==='ticket.assigned');"
          "%s}).then(()=>process.exit(0),(e)=>{console.error(e);process.exit(1)})")

# (id, the request's words it breaks, file, find, replace, witness body)
VARIANTS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("limit-65", "an agent is a non-empty name of at most 64 characters", "src/tickets/validate.js",
     "assignee: 64 })", "assignee: 65 })",
     "a.strictEqual((await api.put(u,{assignee:'x'.repeat(65)})).status,400);"),
    ("limit-63", "an agent is a non-empty name of at most 64 characters", "src/tickets/validate.js",
     "assignee: 64 })", "assignee: 63 })",
     ("a.strictEqual((await api.put(u,{assignee:'x'.repeat(64)})).status,200);"
     "a.strictEqual((await api.get(tid)).body.assignee,'x'.repeat(64));")),
    ("empty-name", "an agent is a non-empty name", "src/tickets/validate.js",
     "body.assignee === null ? null", "!body.assignee ? null",
     "a.strictEqual((await api.put(u,{assignee:''})).status,400);"),
    ("no-unassign", "`{\"assignee\": null}` unassigns it", "src/tickets/validate.js",
     "body.assignee === null ? null : text(", "false ? null : text(",
     ("a.strictEqual((await api.put(u,{assignee:'A'})).status,200);"
     "a.strictEqual((await api.put(u,{assignee:null})).status,200);"
     "a.strictEqual((await api.get(tid)).body.assignee,null);")),
    ("resolved-assignable", "Only open and in-progress tickets can be assigned or unassigned", "src/store.js",
     "if (!isActive(ticket.status)) throw", "if (ticket.status === 'closed') throw",
     ("await move('in_progress');await move('resolved');"
     "a.strictEqual((await api.put(u,{assignee:'A'})).status,409);"
     "a.strictEqual((await api.get(tid)).body.assignee,null);")),
    ("in-progress-refused", "Only open and in-progress tickets can be assigned or unassigned", "src/store.js",
     "if (!isActive(ticket.status)) throw", "if (ticket.status !== 'open') throw",
     "await move('in_progress');a.strictEqual((await api.put(u,{assignee:'A'})).status,200);"),
    ("same-agent-changes", "Assigning a ticket to the agent it already has changes nothing", "src/store.js",
     "ticket.assignee === assignee ? {} :", "false ? {} :",
     ("a.strictEqual((await api.put(u,{assignee:'A'})).status,200);"
     "const audit=(await api.get(tid+'/audit')).body.items.length;const notes=(await sent()).length;"
     "a.strictEqual((await api.put(u,{assignee:'A'})).status,200);"
     "a.strictEqual((await api.get(tid+'/audit')).body.items.length,audit);"
     "a.strictEqual((await sent()).length,notes);")),
    ("not-notified", "The agent a ticket is assigned to is notified", "src/store.js",
     "if (assignee !== null) this.notify(", "if (false) this.notify(",
     ("a.strictEqual((await api.put(u,{assignee:'A'})).status,200);"
     "a.ok((await sent()).some((e)=>e.to==='A'&&e.ticket===t.id));")),
    ("requester-notified", "The agent a ticket is assigned to is notified that it was assigned to them",
     "src/store.js", "'ticket.assigned', assignee, at,", "'ticket.assigned', ticket.requester, at,",
     ("a.strictEqual((await api.put(u,{assignee:'A'})).status,200);"
     "a.ok((await sent()).some((e)=>e.to==='A'&&e.ticket===t.id));")),
    ("no-null-assignee", "Every ticket shows its `assignee` (null when unassigned)", "src/store.js",
     "status: 'open', assignee: null, created", "status: 'open', created",
     ("a.ok('assignee' in t);a.strictEqual(t.assignee,null);"
     "a.strictEqual((await api.get(tid)).body.assignee,null);")),
)


def _run(argv: list[str], cwd: Path) -> tuple[int | None, str]:
    try:
        done = subprocess.run(argv, check=False, cwd=cwd, capture_output=True, text=True, timeout=SUITE_SECONDS)
    except subprocess.TimeoutExpired:
        return None, "timed out"
    return done.returncode, done.stdout + done.stderr


def _failed(output: str) -> list[str]:
    """The failing tests' names the spec reporter prints (each a line starting with ✖), first five."""
    names = [line.strip()[2:].split(" (")[0] for line in output.splitlines() if line.strip().startswith("✖ ")]
    return list(dict.fromkeys(names))[:5]


def _lay(tree: Path, variant: tuple) -> bytes:
    """Lay one variant over ``tree``; returns the file's original bytes."""
    _, _, path, find, replace, _ = variant
    target = tree / path
    original = target.read_bytes()
    text = original.decode("utf-8")
    if text.count(find) != 1:
        raise ValueError(f"{variant[0]}: {path} has {text.count(find)} matches of {find!r}, not 1")
    target.write_bytes(text.replace(find, replace).encode("utf-8"))
    return original


def _copy(worktree: Path, into: Path) -> Path:
    tree = into / "tree"
    shutil.copytree(worktree, tree, symlinks=True, ignore=shutil.ignore_patterns("node_modules", ".shiploop-runs"))
    return tree


def _judge(tree: Path) -> dict:
    """Each variant alone over ``tree``, the whole suite twice when the first run fails."""
    code, output = _run(list(SUITE), tree)
    if code != 0:
        return {"unmutated": "failed", "failed": _failed(output) or [output[-400:]]}
    rows = {}
    for variant in VARIANTS:
        original = _lay(tree, variant)
        try:
            first, output = _run(list(SUITE), tree)
            second = _run(list(SUITE), tree)[0] if first != 0 else 0
        finally:
            (tree / variant[2]).write_bytes(original)
        killed = first != 0 and second != 0
        rows[variant[0]] = {"status": "killed" if killed else "survived",
                            **({"failed": _failed(output)} if killed else {}),
                            **({"flaky": True} if first != 0 and second == 0 else {})}
    return {"unmutated": "passed", "variants": rows}


def score(sample: Path) -> dict:
    sample = Path(sample)
    worktree = sample / "slice/.shiploop-runs/seed/worktree"
    if not worktree.is_dir():
        worktree = sample / ".shiploop-runs/seed/worktree"
    out: dict = {"sample": str(sample), "variants_total": len(VARIANTS)}
    with tempfile.TemporaryDirectory(prefix="e7-request-") as scratch:
        tree = _copy(worktree, Path(scratch))
        full = _judge(tree)
        subprocess.run(["git", "-C", str(tree), "checkout", "HEAD", "--", "test"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tree), "clean", "-fdq", "--", "test"], check=True, capture_output=True)
        earlier = _judge(tree)
    out["unmutated"] = full["unmutated"]
    if full["unmutated"] != "passed":
        return {**out, "value": None, "failed": full["failed"]}
    killed = [name for name, row in full["variants"].items() if row["status"] == "killed"]
    before = [name for name, row in (earlier.get("variants") or {}).items() if row["status"] == "killed"]
    rest = [name for name in full["variants"] if name not in before]
    out.update(value=round(len(killed) / len(VARIANTS), 4),
               added_value=round(sum(name in killed for name in rest) / len(rest), 4) if rest else None,
               killed=killed, survived=[name for name in full["variants"] if name not in killed],
               earlier_tests_kill=before, earlier_unmutated=earlier["unmutated"], variants=full["variants"])
    return out


def verify() -> list[dict]:
    """Each variant's find occurs once in the recorded implementation, its witness passes there and fails on the
    variant; and which variants the case's hidden check (step_cases.json ``checks``) catches."""
    hidden = [command for command in common.case(CASE)["checks"] if command.startswith("node -e")]
    rows = []
    with tempfile.TemporaryDirectory(prefix="e7-request-verify-") as scratch:
        tree = _copy(RECORDED_SOURCE, Path(scratch))
        subprocess.run(["git", "-C", str(tree), "checkout", RECORDED_TREE, "--", "src"], check=True,
                       capture_output=True)
        for variant in VARIANTS:
            witness = _FRAME % variant[5]
            real = _run(["node", "-e", witness], tree)
            original = _lay(tree, variant)
            try:
                broken = _run(["node", "-e", witness], tree)
                caught = [_run(["sh", "-c", command], tree)[0] != 0 for command in hidden]
            finally:
                (tree / variant[2]).write_bytes(original)
            rows.append({"variant": variant[0], "clause": variant[1], "ok": real[0] == 0 and broken[0] != 0,
                         "witness_on_recorded": real[0], "witness_on_variant": broken[0],
                         "hidden_check_catches": any(caught),
                         **({"detail": (real[1] if real[0] else broken[1])[-300:]} if not (real[0] == 0 and broken[0]) else {})})
    return rows


def main(argv: list[str]) -> int:
    if argv[:1] == ["verify"]:
        rows = verify()
        print(json.dumps(rows, indent=1))
        return 0 if all(row["ok"] for row in rows) else 1
    if argv[:1] == ["score"] and argv[1:]:
        for sample in argv[1:]:
            result = score(Path(sample))
            (Path(sample) / "request-score.json").write_text(json.dumps(result, indent=1) + "\n")
            print(sample, result.get("value"), result.get("added_value"), "survived:", result.get("survived"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
