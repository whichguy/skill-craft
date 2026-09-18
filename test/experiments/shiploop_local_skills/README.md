# Repository-local skill reuse pilot

This opt-in fixture asks fresh-context agents to triage a small release-evidence
bundle, then makes cold clones for reuse, compatible evolution, an incident
branch, and a no-op editing task. It prepares inputs and grades deterministic
JSON only; it does not launch a model or simulate one.

See [the trial protocol](protocol.md) for its fixed fixture criteria and the
method-change boundary for already launched agents.

Create a study child, give an agent only its `launch*.md` file and fixture path,
then grade it after the bounded local action:

```sh
SKILL_TRIAL_ROOT="$(mktemp -d)"
python3 test/experiments/shiploop_local_skills/prepare.py init \
  --output "$SKILL_TRIAL_ROOT/candidate"
# Give candidate/launch-initial.md to the fresh-context agent.
python3 test/experiments/shiploop_local_skills/oracle.py --case initial \
  --fixture "$SKILL_TRIAL_ROOT/candidate/fixture" \
  --before-manifest "$SKILL_TRIAL_ROOT/candidate/control/before-manifest.json"

python3 test/experiments/shiploop_local_skills/prepare.py next \
  --source "$SKILL_TRIAL_ROOT/candidate/fixture" \
  --output "$SKILL_TRIAL_ROOT/reuse" --case reuse
# Give reuse/launch.md to a new fresh-context agent, then grade with
# reuse/control/before-manifest.json. Repeat next for evolve, fork, and noop.
```

Each study child contains `fixture/`, the frozen ShipLoop package, and actual
v3-rendered `skill-assess` and `skill-validate` packets. Their predecessor states
are explicitly synthetic packet setup: no callback or Improve execution occurred.
The before manifest stays outside `fixture/`; fixed expected JSON lives only in
the oracle. The oracle compares exact task output and inventories every byte of
each local skill package. It does not judge prompt wording. Review created or
changed skills separately for contract references, durable scope, and retained
v1 behavior.

This is a pilot of one fixture family. It is not a causal reliability study, a
global-skill discovery test, or a context-token comparison. The launch wrapper
itself supplies explicit local scope and default-contract links, so baseline and
candidate observations are not cleanly attributable to the rendered packet alone.

`--case relocate` moves the unchanged v1 authority while leaving the skill's
locator stale; a later `--case reuse` can consume that repaired repository.
This checks an actual reason to evolve a skill when a new business rule alone
may already be covered by its contract-driven procedure.

Run the mechanical cold-packet routing regression with:

```sh
python3 -B test/experiments/shiploop_local_skills/test_packet_routes.py
```

The ordinary ShipLoop CI inventory also runs:

```sh
python3 -B test/shiploop-local-skills.test.py
```

That suite replays archived outputs from temporary copies, checks negative
controls (including JSON boolean/number type confusion) against the grader, and verifies that fresh trial preparation removes
prior outputs while preserving local skills. It uses no model or network and
does not certify semantic skill selection or evolution. Before claiming those
behaviors for changed guidance or a different model, rerun the relevant fresh
reader cases above and inspect the resulting skill artifacts separately.

[Recorded live study](evidence/2026-09-18/README.md) preserves outputs, skills,
package hashes, grades, limitations and the ambiguous initial incident fixture.
