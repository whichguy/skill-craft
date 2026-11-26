---
name: shiploop-e2e-audit
argument-hint: "[improve [CASE] | preflight | review RUN_DIR] [checkout=PATH] [output=PATH]"
description: >-
  Run the continuous ShipLoop end-to-end improvement loop from a skill-craft
  source checkout: iterate ShipLoop on a real local case, evaluate behavior and
  workflow quality, decide whether ShipLoop needs to change, plan one bounded
  hypothesis, apply and verify the change, and rerun a qualified comparison.
version: 2.2.0
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
4. **Plan** one bounded, generic hypothesis with a falsifiable prediction; pre-screen single-stage hypotheses rapidly via `test/shiploop_e2e/stage_suite/stages.py` before spending full deliveries (`promotion/5` remains required for end-to-end qualification).
5. **Change** `skills/shiploop/` at owner-selected `max` effort and verify with the `quick` test tier.
6. **Rerun & promote** via a qualified `promotion/5` comparison (each attempt in its own fresh isolated product Git repo folder), release on `PROMOTE`, and repeat.

## Host and runtime matrix

| Surface | Requirement |
| --- | --- |
| Operator host | Any host with shell access to a clean `skill-craft` checkout (Codex, Claude Code, Grok, Cursor, OpenCode, Antigravity `agy`). |
| Subject host | Defaults to Antigravity Orchestrator (Neon) (`--host antigravity`, `gemini-pro-orchestrator-neon`, pairing Neon planning with Carbon execution internally); explicit overrides include `--host codex` (`gpt-6.2-sol`, `xhigh`, `--codex-auto-review`), `--host claude` (`--backend anthropic` or `ollama`), and `--host grok`. Reviewer, judge and improver roles also default to Antigravity Orchestrator (Neon) (`gemini-pro-orchestrator-neon`) with explicit per-role overrides. |
| Python | `python3` — 3.13+ on macOS (`os.waitid` in `listeners.py`), 3.9+ on Linux (ShipLoop itself requires 3.9+). |
| Git | Configured committer identity (`git -c user.useConfigOnly=true var GIT_COMMITTER_IDENT`) before spending model runs. |

ShipLoop's builder runs independently as a test-case run inside its own new,
isolated Git repository folder — never inside `$SOURCE` (`skill-craft`) and
never reusing a prior run's product directory. Never coach the builder, complete
its callbacks, or modify its product or selected packages during a trial. Keep
raw run outputs outside the source checkout and retain compact evidence in the
repo for every terminal attempt.
