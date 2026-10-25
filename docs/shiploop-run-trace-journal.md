# ShipLoop run trace: journal

Living record of the run-trace work: the question, the design decisions, the evidence and what is still open. Newest
entries last; superseded claims stay, marked with the date and the reason.

## 2026-10-25: the question

Owner request: the in-progress status should be "a dynamic update to data, so a viewer could see or inspect what's going
on", a data file or JSONL plus a reader, inspectable "both by the LLM and by me visually in a nice HTML artifact". It
must show what steps have been run, what has not been run and is still scheduled, and what prompt messages were
injected. Feedback written during the run is wanted later, not in the first pass.

## 2026-10-25: what already existed, and the gaps (firm)

Read from the canonical checkout at `ef5af728` and the chess E2E run of 2026-10-24
(`~/e2e-runs/20261024/chess-sf-full-12a23d`, ShipLoop 1.9.0, 61 accepted steps, 84 packet files):

| Source | What it gives | Gap for this request |
|---|---|---|
| `state.md` `history` | accepted steps in order (action, stage, work item, outcome) | no refusals, no packets, no hooks; Improve stages are not history entries |
| `timeline.json` | when each step was accepted | nothing else |
| `packets/<action>.md` | the packet in full | rewritten in place by every `next`; a reprint or a paused packet overwrites the earlier text, so "what was injected" is lost |
| `status.md`, `progress.html` | where the run is now, plan outline, recent activity | position, not history; no packet text, no refusals |
| `skill-calls.jsonl` | Skill-tool calls (Claude Code only) | only Skill calls |
| keepalive `decisions.log` | stop decisions | in the keepalive home, not the run; no injected text |
| E2E `flow.py` | packets and host events per action | after the fact, E2E only; packet text is the last copy |

The 2026-10-04 ledger design (memory `jsonl-ledger-consolidation-design-2026-10-04`) proposed one `run/ledger.jsonl`
for engine verb calls and left the writer as an owner decision. This request is that decision.

## 2026-10-25: design (firm, built)

- **One append-only file per run, `RUN/trace.jsonl`; "Markdown decides, JSONL remembers."** `state.md` stays the only
  authority; nothing resumes from the trace.
- **Three writers, one module** (`shiploop_trace.py`): `protocol.main` records every command that names the run, with
  the saved state before the verb and the state read after the lock is released (revision, stage and action before and
  after, the history entries it accepted, the refusal text); `navigator.emit` records every printed packet and keeps its
  text in `packets/sent/<sha16>.md` (content-addressed, so a reprint costs one line, not a file); the keepalive stop hook
  records each decision for a bound run with the text it put into the turn.
- **No lock for appends.** One `os.write` on an `O_APPEND`, `O_NOFOLLOW` descriptor; a hook process and a command can
  append at once. Mode 0600 like `state.md`. A failed append never fails a command. Cap 32 MB.
- **Reads and displays are not activity:** `view`, `hook-status`, `trace` and `graph-dry-run` are not recorded.
- **`--check-only` failures are checks, not refusals** (counted separately), since the verb reports and never completes.
- **Reader = `shiploop trace`**: the digest (the shape a model reads: Now, the plan of every stage as done / current /
  reopened / pending with ×runs, +I and !refusals, steps run, recent events, totals), `--action` for one action,
  `--json` for the whole model, `--html` for the page. Events without their own `--action` are attributed to the action
  current at the time (the last packet's).
- **Page = `RUN/trace.html`**, one template (`shiploop_trace_page.html`) with the model inlined; the packet texts are
  screened line by line with the progress view's credential screen. The progress observer rewrites it when the trace,
  `state.md` or `skill-calls.jsonl` change; an active run's page reloads every 10 s, held while a packet is open or a
  search is typed, and a checkbox turns it off.
- **Old runs still read** from `state.md` and `timeline.json`, and say so.

Rejected: extending `progress.html` (bounded, privacy-checked document previews and 967 lines of Python HTML; the
trace is a different consumer); a separate ledger per writer; storing packet text inline in the JSONL (a chess run's
packets are about 2 MB, the trace stays small and greppable).

## 2026-10-25: evidence

- `test/shiploop-trace.test.py`: 15 tests, 18.6 s locally, all pass. They drive real CLI runs (init, a reprint, a
  refused and an accepted intake, pause, resume, status, a failed `--check-only`), the keepalive stop hook with the
  recorded Claude payload, and navigator-saved states past planning (work-item rows, the current slot, Improve marks), plus
  an untraced run, the symlink refusal, the size cap, redaction in the page and the observer writing the page.
- The reader on the 2026-10-24 chess run (no trace; it predates it) shows the whole plan with reruns (W1 implement ×11,
  step-plan ×2 after the send-backs), 61 steps with durations and headlines, and the note that packets are last copies.
- A demo run with every event kind (refusal, hook continuation with its injected text, a head-printed packet, a failed
  check) rendered in the page at desktop and at 375 px in dark mode with no horizontal scroll.

## Open (exploratory)

- **Owner feedback during a run** (the "nice to have"): a `shiploop note --run-dir RUN --text …` verb that appends a
  `note` event, and the next packet quoting unread notes. Needs a packet change, so it waits for the owner.
- **E2E consumers**: `flow.py` and the Run Review exporter rebuild the sequence from host streams; they can read
  `trace.jsonl` instead for refusals, reprints and hook text once a released run has one.
- **Hosts other than Claude Code** record Skill calls nowhere; the trace does not change that.
