---
name: shiploop-e2e-audit
argument-hint: "[improve [CASE] | preflight | review RUN_DIR] [checkout=PATH] [output=PATH]"
description: >-
  Run the continuous ShipLoop end-to-end improvement loop from a skill-craft
  source checkout: iterate ShipLoop on a real local case, evaluate behavior and
  workflow quality, decide whether ShipLoop needs to change, plan one bounded
  hypothesis, apply and verify the change, and rerun a qualified comparison.
version: 1.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

# ShipLoop E2E improvement loop

Use [the improvement procedure](IMPROVE.md) for every request to test, review,
iterate on, or self-improve ShipLoop end to end. This skill requires a clean
`skill-craft` source checkout (`test/shiploop_e2e/`); it ships no bundled
second harness.

The six-step loop is:

1. **Iterate** ShipLoop headlessly on a test case in a brand-new, independent, isolated product Git repository folder (`$RUN/work`, created fresh per run outside `skill-craft`).
2. **Evaluate** product checks, held-out quality, and an independent read-only review + judge.
3. **Decide** whether ShipLoop itself needs to improve, and record learnings in the repo.
4. **Plan** one bounded, generic hypothesis with a falsifiable prediction.
5. **Change** `skills/shiploop/` at owner-selected `max` effort and verify with the `quick` test tier.
6. **Rerun & promote** via a qualified `promotion/5` comparison (each attempt in its own fresh isolated product Git repo folder), release on `PROMOTE`, and repeat.

## Host and runtime matrix

| Surface | Requirement |
| --- | --- |
| Operator host | Any host with shell access to a clean `skill-craft` checkout (Codex, Claude Code, Grok, Cursor, OpenCode). |
| Subject host | `--host codex` (`--codex-auto-review`), `--host claude` (`--backend anthropic` or `ollama`), or `--host grok`. Operator and subject may differ. |
| Python | `python3` — 3.13+ on macOS (`os.waitid` in `listeners.py`), 3.9+ on Linux (ShipLoop itself requires 3.9+). |
| Git | Configured committer identity (`git -c user.useConfigOnly=true var GIT_COMMITTER_IDENT`) before spending model runs. |

ShipLoop's builder runs independently as a test-case run inside its own new,
isolated Git repository folder — never inside `$SOURCE` (`skill-craft`) and
never reusing a prior run's product directory. Never coach the builder, complete
its callbacks, or modify its product or selected packages during a trial. Keep
raw run outputs outside the source checkout and retain compact evidence in the
repo for every terminal attempt.
