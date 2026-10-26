# Review ShipLoop's scripts and prompts: ranked advice with specific plans

You are an outside reviewer. Your current directory is a disposable Git worktree of the `skill-craft`
repository at `origin/main` 31933a73 (ShipLoop 1.9.0). You have every tool. Read the code, run the CLI,
run tests, write scratch files. Do not commit, and do not push. The deliverable is advice, not edits.

## What ShipLoop is for

ShipLoop (`skills/shiploop/`) is a script-backed SDLC delivery harness. It is a portable skill for
several coding-agent hosts: Claude Code, Codex, Grok, Cursor and OpenCode. A user says "ship this".
The host model starts a run, and Python scripts persist the SDLC graph:

1. planning stages: intake, discovery, requirements, plan;
2. per work item: implement, then checks and tests, then an Improve review stage;
3. release and carry-forward.

The scripts print one **action packet** at a time. The model does that one step, writes a result file and
runs the exact **callback** the packet printed. The script then accepts the result or refuses it, and
chooses the next stage. The model is used like a library call: it never picks the next stage or advances
state itself.

The owner's goal is for ShipLoop to produce good code faster on **any** project. The E2E runs (Salesforce
chess and Battleship apps, node bug fixes) are probes that expose ShipLoop defects. They are not the
product. Recent live runs hit a 4-hour cap, and one Grok run spent about 4 hours on what the journal calls
"mostly avoidable ceremony". Speed and code quality on an ordinary run are what matter.

## Design tenets you must respect (judge every proposal against them)

1. **Context can be cleared or compacted between any two stages, so every packet stands alone.** A packet
   restates its stage's purpose, how it operates, how it is checked and how to recover. Repetition *across*
   packets is deliberate grounding. Only repetition *inside* one packet is waste. Do not propose moving
   grounding out of packets into a file the packet merely names. (README top; `test/shiploop_e2e/SPEC.md` S-6.)
2. **Scripts own decisions.** Prefer moving a decision into the script (derived from state, Git diff or the
   submitted result) over prompt text that asks the model to decide. Prompt guidance is for how to do the
   step itself.
3. **Generic.** Name no language, framework or platform in core scripts, prompts or catalogs. Platform
   specifics live only in `skills/shiploop/references/platforms/`.
4. **KISS/YAGNI.** Fix what breaks or misleads a *normal* run. Do not propose guards against adversarial
   models, such as forged packets or racing callbacks.
5. **One supported version.** No shims, fallbacks, aliases or migrations for old runs.
6. **Evidence is a script-run test that passed**, never a model's judgement that the work is good.
7. **Prompts are concise but keep every obligation.** Cut ineffective detail, never a duty.
8. **One term per concept.** `skills/shiploop/references/glossary.md` defines the terms.

## Where to look

- `skills/shiploop/README.md`: the tenet and the navigator sections at the top. "Maintainer map and
  verification" maps the code.
- `skills/shiploop/SKILL.md`: the entry card the host model reads.
- `skills/shiploop/references/`: `navigator.md`, `inner-loop.md`, `test-loop.md`, `glossary.md` and the
  others that packets point at.
- Scripts (`skills/shiploop/scripts/`): `shiploop_navigator.py` (8.7k lines; graph, acceptance, refusals),
  `shiploop_prompts.py` (packet text), `shiploop_stage_spec.py`, `shiploop_protocol.py`,
  `shiploop_loops.py`, `shiploop_test_loop.py`, `shiploop_workspace.py`, and the `shiploop` CLI entry.
- **See the real packets:** `python3 skills/shiploop/scripts/shiploop graph-dry-run --scenario two-work-items
  --format markdown` prints every packet of a simulated two-item run (about 550 KB, so redirect it to a file
  and read it in parts). `--list` shows the other scenarios. Judge the prompts by what a model actually
  receives.
- Real-run evidence: `test/shiploop_e2e/LEARNINGS.md`. Its last ~350 lines cover chess runs 3 and 4 and the
  Grok Battleship run. Also read `docs/shiploop-run5-batch-journal-2026-10-24.md` and the last 25 commits
  (`git log --oneline -25`), so you don't re-propose what just landed.
- The E2E contract: `test/shiploop_e2e/SPEC.md`.
- Repository rules: `AGENTS.md` and `docs/ARCHITECTURE.md`.

## What to deliver

Rank up to 10 recommendations, the most valuable first. Value means the gain in speed or code quality on an
ordinary run of any project, weighed against cost and risk. For each one, give:

1. **Title**, in one line.
2. **Problem:** what goes wrong today, with evidence. Give a `path:symbol`, a short quoted line, a dry-run
   packet excerpt, or a LEARNINGS entry. Mark each claim **observed** (you read it or ran it) or **inferred**.
3. **Plan:** the specific change. Name the files and functions or prompt sections to add, change or remove,
   and the new behaviour, concretely enough that an engineer could implement it.
4. **Expected effect:** on run time, tokens, code quality or failure rate, with a rough size if you can.
5. **Cost and risk:** what could break.
6. **Verify by:** which existing or new test, dry-run comparison or E2E measure would show it worked.
7. **Tenets:** which tenets it touches, and why it does not violate them.

Then list **considered and rejected** ideas, one line each with the reason. This should include anything you
would have proposed but that a tenet forbids.

Write the full report to `REVIEW-deepseek.md` in this worktree's root, and also give it as your final message.
Before you finish, re-open each `path:symbol` you cite and confirm it exists. Drop any recommendation whose
evidence you could not confirm.
